Name:           grtools
Version:        1.0.0
Release:        1%{?dist}
Summary:        GRPI and GRPU - Graphical RPM Package Tools
License:        GPL-3.0
BuildArch:      noarch
Requires:       python3, python3-qt5

%description
A suite of graphical RPM package management tools for KDE.
Includes GRPI (RPM installer) and GRPU (package updater).

%install
mkdir -p %{buildroot}/usr/local/bin
mkdir -p %{buildroot}/usr/share/applications

install -m 755 %{_sourcedir}/grpi %{buildroot}/usr/local/bin/grpi
install -m 755 %{_sourcedir}/grpu %{buildroot}/usr/local/bin/grpu

cat > %{buildroot}/usr/share/applications/grpi.desktop << EOF
[Desktop Entry]
Name=GRPI RPM Installer
Comment=Install local RPM packages
Exec=grpi %f
MimeType=application/x-rpm;
Icon=system-software-install
Type=Application
Categories=System;PackageManager;
StartupNotify=true
EOF

cat > %{buildroot}/usr/share/applications/grpu.desktop << EOF
[Desktop Entry]
Name=GRPU Package Updater
Comment=Update system and application packages
Exec=grpu
Icon=system-software-update
Type=Application
Categories=System;PackageManager;
StartupNotify=true
EOF

%files
%attr(0755, root, root) /usr/local/bin/grpi
%attr(0755, root, root) /usr/local/bin/grpu
/usr/share/applications/grpi.desktop
/usr/share/applications/grpu.desktop

%changelog
* Mon Feb 23 2026 You <you@example.com> - 1.0.0-1
- Initial release combining GRPI and GRPU
