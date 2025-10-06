#!/bin/bash
set -e

PLATFORM=$1
VERSION=$2
ARCH=${PLATFORM#*-}

# Convert architecture for deb packages
if [ "$ARCH" = "x64" ]; then
    DEB_ARCH="amd64"
    TARGET="x86_64-unknown-linux-gnu"
else
    DEB_ARCH="arm64"
    TARGET="aarch64-unknown-linux-gnu"
fi

PACKAGE_NAME="wowusb-ds9"
PACKAGE_VERSION="${VERSION#v}"  # Remove 'v' prefix if present

echo "Building deb package for ${PLATFORM} version ${VERSION}"

# Create package directory structure
DEB_DIR="deb-package"
rm -rf "$DEB_DIR"
mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/usr/bin"
mkdir -p "$DEB_DIR/usr/share/applications"
mkdir -p "$DEB_DIR/usr/share/icons/WowUSB-DS9"
mkdir -p "$DEB_DIR/usr/share/doc/wowusb-ds9"

# Copy the built binary
if [ "$ARCH" = "x64" ]; then
    BINARY="src-tauri/target/x86_64-unknown-linux-gnu/release/wowusb-ds9"
else
    BINARY="src-tauri/target/aarch64-unknown-linux-gnu/release/wowusb-ds9"
fi

cp "$BINARY" "$DEB_DIR/usr/bin/wowusb-ds9"

# Copy desktop file
cp "miscellaneous/WowUSB-DS9.desktop" "$DEB_DIR/usr/share/applications/"

# Copy icon
if [ -f "WowUSB/data/icon.ico" ]; then
    cp "WowUSB/data/icon.ico" "$DEB_DIR/usr/share/icons/WowUSB-DS9/icon.ico"
fi

# Copy documentation
if [ -f "README.md" ]; then
    cp README.md "$DEB_DIR/usr/share/doc/wowusb-ds9/"
fi
if [ -f "COPYING" ]; then
    cp COPYING "$DEB_DIR/usr/share/doc/wowusb-ds9/"
fi
if [ -f "CHANGELOG.md" ]; then
    cp CHANGELOG.md "$DEB_DIR/usr/share/doc/wowusb-ds9/" 2>/dev/null || true
fi

# Create control file
cat > "$DEB_DIR/DEBIAN/control" << EOF
Package: ${PACKAGE_NAME}
Version: ${PACKAGE_VERSION}
Section: utils
Priority: optional
Architecture: ${DEB_ARCH}
Depends: libc6, libgtk-3-0, libwebkit2gtk-4.0-37, libappindicator3-1, libnotify4, xdg-user-dirs, libnss3
Maintainer: Robin L. M. Cheung <robin@robincheung.com>
Description: Create bootable Windows USB drives with advanced features
 WowUSB-DS9 is a Linux program to create a Windows USB stick installer from a real Windows DVD or image with advanced filesystem support and Windows-To-Go capability.
Homepage: https://github.com/rebots-online/WowUSB
Bugs: https://github.com/rebots-online/WowUSB/issues
EOF

# Create md5sums
cd "$DEB_DIR"
find usr -type f -exec md5sum {} \; > DEBIAN/md5sums
cd ..

# Create conffiles
cat > "$DEB_DIR/DEBIAN/conffiles" << EOF
etc/xdg/wowusb-ds9.desktop usr/share/applications/WowUSB-DS9.desktop
usr/share/icons/WowUSB-DS9/icon.ico usr/share/icons/WowUSB-DS9/icon.ico
EOF

# Build the package
dpkg-deb --build "$DEB_DIR" "${PACKAGE_NAME}_${PACKAGE_VERSION}_${DEB_ARCH}.deb"

echo "Deb package created: ${PACKAGE_NAME}_${PACKAGE_VERSION}_${DEB_ARCH}.deb"

# Clean up
rm -rf "$DEB_DIR"