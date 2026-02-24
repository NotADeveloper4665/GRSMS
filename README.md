How GRPI Works

GRPI (Graphical RPM Package Installer) is a graphical front-end for installing
local .rpm files, similar to how GDebi works on Debian-based systems.

1. Launch grpi
2. Click Browse to select a .rpm file from your system.
3. GRPI will display the package information including name, version,
   architecture, size, license, and a short description.
4. Click Install Package and confirm the prompt.
5. You will be asked for your password via pkexec, kdesu, or sudo.
6. GRPI will use dnf, zypper, or yum to install the package, automatically
   downloading and installing any missing dependencies.
7. The installation log is shown in real time. A success or failure message
   will appear when finished.

Settings (gear icon next to the title):
- Auto-close: Automatically closes GRPI after a successful installation.
- Package Manager: Choose which package manager to use, or leave it on
  Automatic to let GRPI pick the best available one. Any package manager
  not installed on your system will be greyed out.


How GRPU Works

GRPU (Graphical RPM Package Updater) is a graphical front-end for keeping
your entire system up to date in one click.

1. Launch grpu
2. Tick the update sources you want to run. Available options are:
   - DNF    — updates system packages on Fedora, RHEL, and Ultramarine
   - Zypper — updates system packages on openSUSE
   - YUM    — updates system packages on older RHEL and CentOS
   - Flatpak — updates all installed Flatpak applications
   - Snap   — updates all installed Snap packages
   Any source not installed on your system will be greyed out automatically.
3. Click Run Updates. You will be prompted for your password.
4. Each update task runs one at a time. The live log shows exactly what is
   happening, with colour coded output — blue for the active task, green
   for success, and red for any errors.
5. When all tasks are done a summary popup tells you whether everything
   succeeded or if any tasks failed.
6. Click Save Log at any time to save the log output to a file named
   log_date_time.txt in a folder of your choice.
7. Click Clear Log to wipe the log output.
