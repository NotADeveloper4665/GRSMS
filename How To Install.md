(Option 1) "Pre-Built"

1)Head over to the releases page and download the newest version
2)Open terminal and type the command below replace XXX with the version number ie for v0.01 "extraordinary-eggs" is 0.01

    sudo dnf install ~/Downloads/GRSMS-XXX.*.noarch.rpm


(Option 2) 

1) How to Build and Install GRSMS from Source

2) Download the .py files and the .spec files, then open the terminal in the directory you downloaded the files too

2.5) Before building, make sure you have the following installed:

    sudo dnf install rpm-build python3-qt5


3. Type the commands below to copy the source files in the correct locations:

        cp grpi.py ~/rpmbuild/SOURCES/grpi
        cp grpu.py ~/rpmbuild/SOURCES/grpu
        cp grsms.spec ~/rpmbuild/SPECS/grsms.spec

4.   If the rpmbuild folders don't exist yet, create them first:

         mkdir -p ~/rpmbuild/{SPECS,SOURCES,BUILD,RPMS,SRPMS}

5. Build the RPM:

        rpmbuild -bb ~/rpmbuild/SPECS/grsms.spec

6. Install the built RPM:

        sudo dnf install ~/rpmbuild/RPMS/noarch/GRSMS-1.0.0-1.*.noarch.rpm


Uninstalling
To remove GRSMS from your system:

    sudo dnf remove grpi && sudo dnf remove grpu
