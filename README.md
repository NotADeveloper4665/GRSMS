How to Build and Install GRSMS from Source

Requirements
Before building, make sure you have the following installed:

    sudo dnf install rpm-build python3-qt5

Setup
1. Place the source files in the correct locations:

    cp grpi.py ~/rpmbuild/SOURCES/grpi
    cp grpu.py ~/rpmbuild/SOURCES/grpu
    cp grsms.spec ~/rpmbuild/SPECS/grsms.spec

   If the rpmbuild folders don't exist yet, create them first:

    mkdir -p ~/rpmbuild/{SPECS,SOURCES,BUILD,RPMS,SRPMS}

Build
2. Build the RPM:

    rpmbuild -bb ~/rpmbuild/SPECS/grsms.spec

Install
3. Install the built RPM:

    sudo dnf install ~/rpmbuild/RPMS/noarch/GRSMS-1.0.0-1.*.noarch.rpm

To open an RPM file directly with GRPI From CLI:

    grpi /path/to/package.rpm

Uninstalling
To remove GRSMS from your system:

    sudo dnf remove GRSMS
