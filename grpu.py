#!/usr/bin/env python3
import sys
import os
import subprocess
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QProgressBar, QGroupBox,
    QMessageBox, QFrame, QCheckBox, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont


# ── Helpers ────────────────────────────────────────────────────────────────────
def which(cmd):
    return subprocess.run(["which", cmd], capture_output=True).returncode == 0

def find_escalation():
    for tool in ["pkexec", "kdesu", "sudo"]:
        if which(tool):
            return tool
    return None

AVAILABLE = {
    "dnf":     which("dnf"),
    "zypper":  which("zypper"),
    "yum":     which("yum"),
    "flatpak": which("flatpak"),
    "snap":    which("snap"),
}


# ── Worker thread ──────────────────────────────────────────────────────────────
class UpdateThread(QThread):
    output_signal  = pyqtSignal(str)
    section_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int, str)

    def __init__(self, task_name, cmd, needs_root=True):
        super().__init__()
        self.task_name  = task_name
        self.cmd        = cmd
        self.needs_root = needs_root

    def run(self):
        self.section_signal.emit(self.task_name)
        try:
            if self.needs_root:
                esc = find_escalation()
                if not esc:
                    self.output_signal.emit("ERROR: No privilege escalation tool found.")
                    self.finished_signal.emit(1, self.task_name)
                    return
                cmd = (["kdesu", "--"] if esc == "kdesu" else [esc]) + self.cmd
            else:
                cmd = self.cmd

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True
            )
            for line in process.stdout:
                self.output_signal.emit(line.rstrip())
            process.wait()
            self.finished_signal.emit(process.returncode, self.task_name)
        except Exception as e:
            self.output_signal.emit(f"ERROR: {e}")
            self.finished_signal.emit(1, self.task_name)


# ── Status label ───────────────────────────────────────────────────────────────
class StatusLabel(QLabel):
    def __init__(self):
        super().__init__("● Idle")
        self.setAlignment(Qt.AlignCenter)
        self.set_idle()

    def set_idle(self):
        self.setText("● Idle")
        self.setStyleSheet("color: gray; font-weight: bold;")

    def set_running(self, name):
        self.setText(f"⟳ {name}")
        self.setStyleSheet("color: #3daee9; font-weight: bold;")

    def set_done(self, ok):
        if ok:
            self.setText("✔ All updates complete")
            self.setStyleSheet("color: #27ae60; font-weight: bold;")
        else:
            self.setText("✘ Completed with errors")
            self.setStyleSheet("color: #e74c3c; font-weight: bold;")


# ── Main window ────────────────────────────────────────────────────────────────
class GrpuWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.threads   = []   # keep all thread refs alive
        self.task_queue = []
        self.results   = []
        self.running   = False

        self.setWindowTitle("GRPU - Graphical RedHat Package Updater")
        self.setMinimumSize(700, 600)
        self.setWindowIcon(QIcon.fromTheme("system-software-update"))
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header
        header = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(QIcon.fromTheme("system-software-update").pixmap(48, 48))
        header.addWidget(icon_lbl)
        title_col = QVBoxLayout()
        title_lbl = QLabel("GRPU")
        f = QFont(); f.setPointSize(18); f.setBold(True)
        title_lbl.setFont(f)
        sub_lbl = QLabel("Graphical RedHat Package Updater")
        sub_lbl.setStyleSheet("color: gray;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)
        header.addLayout(title_col)
        header.addStretch()
        self.status_lbl = StatusLabel()
        header.addWidget(self.status_lbl)
        layout.addLayout(header)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine); sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # Update sources
        sources_group = QGroupBox("Update Sources")
        sources_layout = QVBoxLayout(sources_group)
        self.checks = {}
        sources = [
            ("dnf",     "DNF — system packages (Fedora / RHEL / Ultramarine)", AVAILABLE["dnf"]),
            ("zypper",  "Zypper — system packages (openSUSE)",                  AVAILABLE["zypper"]),
            ("yum",     "YUM — system packages (older RHEL / CentOS)",          AVAILABLE["yum"]),
            ("flatpak", "Flatpak — sandboxed applications",                     AVAILABLE["flatpak"]),
            ("snap",    "Snap — snap packages",                                  AVAILABLE["snap"]),
        ]
        for key, label, available in sources:
            cb = QCheckBox(label if available else label + "  [not installed]")
            cb.setChecked(available)
            cb.setEnabled(available)
            if not available:
                cb.setToolTip("Not installed on this system")
            self.checks[key] = cb
            sources_layout.addWidget(cb)
        layout.addWidget(sources_group)

        # Log
        log_group = QGroupBox("Update Log")
        log_layout = QVBoxLayout(log_group)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Monospace", 9))
        self.log.setStyleSheet("background-color: #1a1a2e; color: #e0e0e0;")
        self.log.setMinimumHeight(200)
        log_layout.addWidget(self.log)
        layout.addWidget(log_group)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Buttons
        btn_row = QHBoxLayout()
        clear_btn = QPushButton("Clear Log")
        clear_btn.setIcon(QIcon.fromTheme("edit-clear"))
        clear_btn.clicked.connect(self.log.clear)
        btn_row.addWidget(clear_btn)

        save_log_btn = QPushButton("Save Log")
        save_log_btn.setIcon(QIcon.fromTheme("document-save"))
        save_log_btn.setToolTip("Save log to a folder of your choice")
        save_log_btn.clicked.connect(self._save_log)
        btn_row.addWidget(save_log_btn)
        btn_row.addStretch()

        self.update_btn = QPushButton("Run Updates")
        self.update_btn.setIcon(QIcon.fromTheme("system-software-update"))
        self.update_btn.setMinimumWidth(150)
        self.update_btn.setDefault(True)
        f2 = QFont(); f2.setBold(True)
        self.update_btn.setFont(f2)
        self.update_btn.clicked.connect(self._start_updates)
        btn_row.addWidget(self.update_btn)

        close_btn = QPushButton("Close")
        close_btn.setIcon(QIcon.fromTheme("window-close"))
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    # ── Build task list ────────────────────────────────────────────────────────
    def _build_task_list(self):
        tasks = []
        if self.checks["dnf"].isChecked():
            tasks.append(UpdateThread("DNF — Upgrade packages", ["dnf", "upgrade", "-y"], needs_root=True))
        if self.checks["zypper"].isChecked():
            tasks.append(UpdateThread("Zypper — Refresh repos",   ["zypper", "refresh"], needs_root=True))
            tasks.append(UpdateThread("Zypper — Update packages", ["zypper", "--non-interactive", "update"], needs_root=True))
        if self.checks["yum"].isChecked():
            tasks.append(UpdateThread("YUM — Update packages", ["yum", "update", "-y"], needs_root=True))
        if self.checks["flatpak"].isChecked():
            tasks.append(UpdateThread("Flatpak — Update all", ["flatpak", "update", "-y"], needs_root=False))
        if self.checks["snap"].isChecked():
            tasks.append(UpdateThread("Snap — Refresh all", ["snap", "refresh"], needs_root=True))
        return tasks

    # ── Run next task in queue ─────────────────────────────────────────────────
    def _start_updates(self):
        tasks = self._build_task_list()
        if not tasks:
            QMessageBox.warning(self, "Nothing selected", "Please tick at least one update source.")
            return

        self.update_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.log.clear()
        self.results = []
        self.threads = []
        self.task_queue = tasks
        self._log("━━━ GRPU Update Session Started ━━━\n")
        self._run_next()

    def _run_next(self):
        if not self.task_queue:
            self._all_done()
            return

        task = self.task_queue.pop(0)
        self.threads.append(task)   # keep reference alive
        task.output_signal.connect(self._log)
        task.section_signal.connect(self._log_section)
        task.finished_signal.connect(self._task_finished)
        task.start()

    def _log(self, text):
        self.log.append(text)

    def _log_section(self, name):
        self.status_lbl.set_running(name)
        self.log.append(f"\n<span style='color:#3daee9; font-weight:bold;'>▶ {name}</span>")

    def _task_finished(self, code, name):
        # dnf upgrade exits 0 always; dnf check-update exits 100 if updates exist
        success = code in (0, 100)
        if success:
            self.log.append(f"<span style='color:#27ae60;'>✔ {name} — done</span>")
        else:
            self.log.append(f"<span style='color:#e74c3c;'>✘ {name} — exit code {code}</span>")
        self.results.append((name, code))
        self._run_next()

    def _all_done(self):
        self.progress.setVisible(False)
        self.update_btn.setEnabled(True)

        failures = [(n, c) for n, c in self.results if c not in (0, 100)]
        ok = len(failures) == 0
        self.log.append(
            f"\n<span style='font-weight:bold;'>━━━ Session complete — "
            f"{'all tasks succeeded' if ok else f'{len(failures)} task(s) failed'} ━━━</span>"
        )
        self.status_lbl.set_done(ok)

        if ok:
            QMessageBox.information(self, "Updates Complete", "All selected updates finished successfully!")
        else:
            failed_names = "\n".join(f"  • {n}" for n, _ in failures)
            QMessageBox.warning(self, "Some Updates Failed",
                                f"The following tasks reported errors:\n{failed_names}\n\nCheck the log for details.")

    def _save_log(self):
        text = self.log.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Empty Log", "There is nothing in the log to save.")
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Choose folder to save log",
            os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly
        )
        if not folder:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join(folder, f"log_{timestamp}.txt")
        try:
            with open(filepath, "w") as f:
                f.write(text)
            QMessageBox.information(self, "Log Saved", f"Log saved to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Could not save log:\n{e}")

    def closeEvent(self, event):
        # Wait for any running threads before closing
        for t in self.threads:
            if t.isRunning():
                t.wait(3000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("grpu")
    app.setApplicationDisplayName("GRPU - Graphical RedHat Package Updater")
    window = GrpuWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
