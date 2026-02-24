#!/usr/bin/env python3
import sys
import os
import subprocess
import re
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QProgressBar,
    QGroupBox, QMessageBox, QFrame, QDialog, QCheckBox, QRadioButton,
    QButtonGroup
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

# Config
CONFIG_PATH = os.path.expanduser("~/.config/grpi/settings.json")
DEFAULT_SETTINGS = {
    "auto_close": False,
    "preferred_pm": "auto",
}

def load_settings():
    try:
        with open(CONFIG_PATH) as f:
            s = DEFAULT_SETTINGS.copy()
            s.update(json.load(f))
            return s
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(settings, f, indent=2)

def which(cmd):
    return subprocess.run(["which", cmd], capture_output=True).returncode == 0


class InstallThread(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)

    def __init__(self, rpm_path, settings):
        super().__init__()
        self.rpm_path = rpm_path
        self.settings = settings

    def _pick_pm(self):
        pref = self.settings.get("preferred_pm", "auto")
        if pref != "auto" and which(pref):
            return pref
        for pm in ["dnf", "zypper", "yum", "rpm"]:
            if which(pm):
                return pm
        return None

    def _pick_escalation(self):
        for tool in ["pkexec", "kdesu", "sudo"]:
            if which(tool):
                return tool
        return None

    def run(self):
        try:
            pm = self._pick_pm()
            esc = self._pick_escalation()

            if not esc:
                self.output_signal.emit("ERROR: No privilege escalation tool found.")
                self.finished_signal.emit(1)
                return

            if pm == "dnf":
                install_cmd = ["dnf", "install", "-y", self.rpm_path]
                self.output_signal.emit("Using dnf (dependency resolution enabled)...")
            elif pm == "zypper":
                install_cmd = ["zypper", "--non-interactive", "install", self.rpm_path]
                self.output_signal.emit("Using zypper (dependency resolution enabled)...")
            elif pm == "yum":
                install_cmd = ["yum", "install", "-y", self.rpm_path]
                self.output_signal.emit("Using yum (dependency resolution enabled)...")
            elif pm == "rpm":
                install_cmd = ["rpm", "-ivh", "--replacepkgs", self.rpm_path]
                self.output_signal.emit("WARNING: Using rpm directly - no automatic dependency resolution.")
            else:
                self.output_signal.emit("ERROR: No package manager found.")
                self.finished_signal.emit(1)
                return

            cmd = (["kdesu", "--"] if esc == "kdesu" else [esc]) + install_cmd

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                self.output_signal.emit(line.rstrip())
            process.wait()
            self.finished_signal.emit(process.returncode)

        except Exception as e:
            self.output_signal.emit(f"ERROR: {e}")
            self.finished_signal.emit(1)


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.setWindowTitle("grpi Settings")
        self.setMinimumWidth(420)
        self.setWindowIcon(QIcon.fromTheme("configure"))
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # General
        general_group = QGroupBox("General")
        general_layout = QVBoxLayout(general_group)
        self.auto_close_cb = QCheckBox("Auto-close window after successful installation")
        self.auto_close_cb.setChecked(self.settings.get("auto_close", False))
        general_layout.addWidget(self.auto_close_cb)
        layout.addWidget(general_group)

        # Package manager
        pm_group = QGroupBox("Package Manager")
        pm_layout = QVBoxLayout(pm_group)
        note = QLabel("Managers not installed on this system are greyed out.")
        note.setStyleSheet("color: gray; font-size: 10px;")
        pm_layout.addWidget(note)

        self.pm_button_group = QButtonGroup(self)
        managers = [
            ("auto",   "Automatic — use best available (recommended)", True),
            ("dnf",    "dnf  — Fedora / RHEL / Ultramarine",           which("dnf")),
            ("zypper", "zypper — openSUSE",                            which("zypper")),
            ("yum",    "yum  — older RHEL / CentOS",                   which("yum")),
            ("rpm",    "rpm  — direct install (no dependency resolution)", which("rpm")),
        ]

        pref = self.settings.get("preferred_pm", "auto")
        for key, label, available in managers:
            rb = QRadioButton(label)
            rb.setProperty("pm_key", key)
            rb.setEnabled(available)
            if not available:
                rb.setToolTip("Not installed on this system")
            if key == pref:
                rb.setChecked(True)
            self.pm_button_group.addButton(rb)
            pm_layout.addWidget(rb)

        layout.addWidget(pm_group)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Save")
        save_btn.setIcon(QIcon.fromTheme("document-save"))
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setIcon(QIcon.fromTheme("dialog-cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _save(self):
        self.settings["auto_close"] = self.auto_close_cb.isChecked()
        for btn in self.pm_button_group.buttons():
            if btn.isChecked():
                self.settings["preferred_pm"] = btn.property("pm_key")
                break
        save_settings(self.settings)
        self.accept()

    def get_settings(self):
        return self.settings


class GrpiWindow(QMainWindow):
    def __init__(self, rpm_file=None):
        super().__init__()
        self.rpm_path = None
        self.install_thread = None
        self.settings = load_settings()
        self.setWindowTitle("grpi - RPM Package Installer")
        self.setMinimumSize(620, 540)
        self.setWindowIcon(QIcon.fromTheme("system-software-install"))
        self._build_ui()
        if rpm_file and os.path.isfile(rpm_file):
            self._load_rpm(rpm_file)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header
        header = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(QIcon.fromTheme("application-x-rpm").pixmap(48, 48))
        header.addWidget(icon_lbl)
        title_lbl = QLabel("grpi RPM Installer")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        title_lbl.setFont(f)
        header.addWidget(title_lbl)
        header.addStretch()
        settings_btn = QPushButton("Settings")
        settings_btn.setIcon(QIcon.fromTheme("configure"))
        settings_btn.clicked.connect(self._open_settings)
        header.addWidget(settings_btn)
        layout.addLayout(header)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # File picker
        file_group = QGroupBox("RPM Package")
        file_row = QHBoxLayout(file_group)
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: gray;")
        file_row.addWidget(self.file_label, stretch=1)
        browse_btn = QPushButton("Browse...")
        browse_btn.setIcon(QIcon.fromTheme("document-open"))
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(browse_btn)
        layout.addWidget(file_group)

        # Package info
        info_group = QGroupBox("Package Information")
        info_layout = QVBoxLayout(info_group)
        self.info_label = QLabel("Select an RPM file to view package details.")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignTop)
        self.info_label.setStyleSheet("font-family: monospace;")
        self.info_label.setMinimumHeight(80)
        info_layout.addWidget(self.info_label)
        layout.addWidget(info_group)

        # Log
        log_group = QGroupBox("Installation Log")
        log_layout = QVBoxLayout(log_group)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Monospace", 9))
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        self.log_output.setMinimumHeight(130)
        log_layout.addWidget(self.log_output)
        layout.addWidget(log_group)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.install_btn = QPushButton("Install Package")
        self.install_btn.setIcon(QIcon.fromTheme("system-software-install"))
        self.install_btn.setEnabled(False)
        self.install_btn.setMinimumWidth(140)
        self.install_btn.setDefault(True)
        self.install_btn.clicked.connect(self._install)
        btn_row.addWidget(self.install_btn)
        close_btn = QPushButton("Close")
        close_btn.setIcon(QIcon.fromTheme("window-close"))
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec_() == QDialog.Accepted:
            self.settings = dlg.get_settings()

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open RPM Package", os.path.expanduser("~"),
            "RPM Packages (*.rpm);;All Files (*)"
        )
        if path:
            self._load_rpm(path)

    def _load_rpm(self, path):
        self.rpm_path = path
        self.file_label.setText(os.path.basename(path))
        self.file_label.setStyleSheet("color: black; font-weight: bold;")
        self.log_output.clear()
        self._query_rpm_info(path)
        self.install_btn.setEnabled(True)

    def _query_rpm_info(self, path):
        try:
            result = subprocess.run(["rpm", "-qip", path], capture_output=True, text=True)
            if result.returncode == 0:
                fields = {}
                for line in result.stdout.splitlines():
                    for key in ["Name", "Version", "Release", "Architecture", "Summary", "Size", "License"]:
                        if line.startswith(key + " "):
                            fields[key] = re.sub(rf"^{key}\s*:\s*", "", line).strip()
                text = ""
                if "Name" in fields:         text += f"<b>Name:</b> {fields['Name']}<br>"
                if "Version" in fields:      text += f"<b>Version:</b> {fields['Version']}-{fields.get('Release','')}<br>"
                if "Architecture" in fields: text += f"<b>Architecture:</b> {fields['Architecture']}<br>"
                if "Size" in fields:
                    kb = int(fields['Size']) // 1024 if fields['Size'].isdigit() else "?"
                    text += f"<b>Installed Size:</b> {kb} KB<br>"
                if "License" in fields:      text += f"<b>License:</b> {fields['License']}<br>"
                if "Summary" in fields:      text += f"<b>Summary:</b> {fields['Summary']}<br>"
                self.info_label.setText(text or result.stdout[:500])
            else:
                self.info_label.setText(f"<span style='color:red'>Could not read RPM info:<br>{result.stderr}</span>")
        except FileNotFoundError:
            self.info_label.setText("<span style='color:red'>ERROR: rpm not found.</span>")

    def _install(self):
        if not self.rpm_path:
            return
        reply = QMessageBox.question(
            self, "Confirm Installation",
            f"Install <b>{os.path.basename(self.rpm_path)}</b>?<br><br>"
            "You will be prompted for your password.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return

        self.install_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.log_output.clear()
        self._log("Starting installation...")

        self.install_thread = InstallThread(self.rpm_path, self.settings)
        self.install_thread.output_signal.connect(self._log)
        self.install_thread.finished_signal.connect(self._install_finished)
        self.install_thread.start()

    def _log(self, text):
        self.log_output.append(text)

    def _install_finished(self, exit_code):
        self.progress.setVisible(False)
        self.install_btn.setEnabled(True)

        if exit_code == 0:
            self._log("\n✔ Installation completed successfully.")
            if self.settings.get("auto_close"):
                QApplication.quit()
            else:
                QMessageBox.information(self, "Success", "Package installed successfully!")
        else:
            self._log(f"\n✘ Installation failed (exit code {exit_code}).")
            QMessageBox.critical(self, "Installation Failed",
                                 f"Installation failed with exit code {exit_code}.\n"
                                 "Check the log for details.")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("grpi")
    app.setApplicationDisplayName("grpi RPM Installer")
    rpm_file = sys.argv[1] if len(sys.argv) > 1 else None
    window = GrpiWindow(rpm_file)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
