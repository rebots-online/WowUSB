#!/bin/bash
# WowUSB-DS9 Tarball Creation Script
# This script creates a tar.gz package with all required files and dependencies

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Dynamically get version from setup.py
VERSION=$(cd "$PROJECT_DIR"; python3 setup.py --version)
if [ -z "$VERSION" ]; then
    echo "Error: Could not determine version from setup.py"
    exit 1
fi

PACKAGE_NAME="wowusb-ds9" # Should match setup.py name if possible
TARBALL_NAME="${PACKAGE_NAME}-${VERSION}"
TEMP_DIR=$(mktemp -d)


# Print banner
echo "====================================================="
echo "  Creating ${TARBALL_NAME}.tar.gz package"
echo "====================================================="

# Create directory structure
echo "Creating directory structure..."
mkdir -p "${TEMP_DIR}/${TARBALL_NAME}"
mkdir -p "${TEMP_DIR}/${TARBALL_NAME}/bin"
mkdir -p "${TEMP_DIR}/${TARBALL_NAME}/share/applications"
mkdir -p "${TEMP_DIR}/${TARBALL_NAME}/share/icons/WowUSB-DS9"
mkdir -p "${TEMP_DIR}/${TARBALL_NAME}/share/polkit-1/actions"

# Copy Python package
echo "Copying Python package..."
cp -r "${PROJECT_DIR}/WowUSB" "${TEMP_DIR}/${TARBALL_NAME}/"
cp -r "${PROJECT_DIR}/WoeUSB" "${TEMP_DIR}/${TARBALL_NAME}/"

# Copy scripts
echo "Copying scripts..."
cp "${PROJECT_DIR}/WowUSB/wowusb" "${TEMP_DIR}/${TARBALL_NAME}/bin/"
cp "${PROJECT_DIR}/WowUSB/wowusbgui" "${TEMP_DIR}/${TARBALL_NAME}/bin/"
cp "${SCRIPT_DIR}/install.sh" "${TEMP_DIR}/${TARBALL_NAME}/"
chmod +x "${TEMP_DIR}/${TARBALL_NAME}/install.sh"
cp "${SCRIPT_DIR}/uninstall.sh" "${TEMP_DIR}/${TARBALL_NAME}/"
chmod +x "${TEMP_DIR}/${TARBALL_NAME}/uninstall.sh"

# Copy desktop integration files
echo "Copying desktop integration files..."
cp "${PROJECT_DIR}/miscellaneous/WowUSB-DS9.desktop" "${TEMP_DIR}/${TARBALL_NAME}/share/applications/"
cp "${PROJECT_DIR}/WowUSB/data/icon.ico" "${TEMP_DIR}/${TARBALL_NAME}/share/icons/WowUSB-DS9/"
cp "${PROJECT_DIR}/miscellaneous/com.rebots.wowusb.ds9.policy" "${TEMP_DIR}/${TARBALL_NAME}/share/polkit-1/actions/"

# Copy documentation
echo "Copying documentation..."
cp "${PROJECT_DIR}/README.md" "${TEMP_DIR}/${TARBALL_NAME}/"
cp "${PROJECT_DIR}/COPYING" "${TEMP_DIR}/${TARBALL_NAME}/"
cp "${PROJECT_DIR}/CHANGELOG.md" "${TEMP_DIR}/${TARBALL_NAME}/" 2>/dev/null || echo "No CHANGELOG.md found, skipping..."
cp "${PROJECT_DIR}/TECHNICAL_DESIGN.md" "${TEMP_DIR}/${TARBALL_NAME}/" 2>/dev/null || echo "No TECHNICAL_DESIGN.md found, skipping..."

# Create distribution-specific dependency lists
echo "Creating distribution-specific dependency lists..."
mkdir -p "${TEMP_DIR}/${TARBALL_NAME}/dependencies"

# Debian/Ubuntu dependencies
cat > "${TEMP_DIR}/${TARBALL_NAME}/dependencies/debian.txt" << EOF
python3
python3-pip
python3-wxgtk4.0
python3-termcolor
grub2-common
grub-pc-bin
parted
dosfstools
ntfs-3g
exfat-utils | exfatprogs
f2fs-tools
btrfs-progs
p7zip-full
EOF

# Fedora dependencies
cat > "${TEMP_DIR}/${TARBALL_NAME}/dependencies/fedora.txt" << EOF
python3
python3-pip
python3-wxpython4
python3-termcolor
grub2-common
grub2-tools
parted
dosfstools
ntfs-3g
exfatprogs
f2fs-tools
btrfs-progs
p7zip
p7zip-plugins
EOF

# Arch Linux dependencies
cat > "${TEMP_DIR}/${TARBALL_NAME}/dependencies/arch.txt" << EOF
python
python-pip
python-wxpython
python-termcolor
grub
parted
dosfstools
ntfs-3g
exfatprogs
f2fs-tools
btrfs-progs
p7zip
EOF

# openSUSE dependencies
cat > "${TEMP_DIR}/${TARBALL_NAME}/dependencies/opensuse.txt" << EOF
python3
python3-pip
python3-wxPython
python3-termcolor
grub2
parted
dosfstools
ntfs-3g
exfatprogs
f2fs-tools
btrfs-progs
p7zip
EOF

# Create the tarball
echo "Creating tarball..."
cd "${TEMP_DIR}"
tar -czf "${TARBALL_NAME}.tar.gz" "${TARBALL_NAME}"

# Move the tarball to the project directory
echo "Moving tarball to project directory..."
mkdir -p "${PROJECT_DIR}/dist"
mv "${TARBALL_NAME}.tar.gz" "${PROJECT_DIR}/dist/"

# Clean up
echo "Cleaning up..."
rm -rf "${TEMP_DIR}"

echo "====================================================="
echo "  Package created: dist/${TARBALL_NAME}.tar.gz"
echo "====================================================="
