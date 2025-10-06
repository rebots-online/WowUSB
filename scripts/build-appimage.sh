#!/bin/bash
set -e

PLATFORM=$1
VERSION=$2
ARCH=${PLATFORM#*-}

echo "Building AppImage for ${PLATFORM} version ${VERSION}"

# Create AppDir structure
APPDIR="WowUSB-DS9.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# Copy the built binary
if [ "$ARCH" = "x64" ]; then
    BINARY="src-tauri/target/x86_64-unknown-linux-gnu/release/wowusb-ds9"
else
    BINARY="src-tauri/target/aarch64-unknown-linux-gnu/release/wowusb-ds9"
fi

cp "$BINARY" "$APPDIR/usr/bin/wowusb-ds9"

# Copy desktop file
cat > "$APPDIR/usr/share/applications/WowUSB-DS9.desktop" << 'EOF'
[Desktop Entry]
Name=WowUSB-DS9
Comment=Create Bootable Windows USB Drives
Exec=wowusb-ds9
Icon=WowUSB-DS9
Type=Application
Categories=System;Utility;
Keywords=usb;boot;windows;installer;
StartupNotify=true
EOF

# Copy icon
if [ -f "src-tauri/icons/icon.ico" ]; then
    cp "src-tauri/icons/icon.ico" "$APPDIR/usr/share/icons/hicolor/256x256/apps/wowusb-ds9.ico"
else
    # Create a simple icon using ImageMagick if available
    if command -v convert &> /dev/null; then
        convert -size 256x256 xc:blue -pointsize 72 -fill white -gravity center -annotate 0 "W3" \
                "$APPDIR/usr/share/icons/hicolor/256x256/apps/wowusb-ds9.ico"
    else
        echo "Warning: No icon found and ImageMagick not available"
    fi
fi

# Create AppRun
cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
exec "${HERE}/usr/bin/wowusb-ds9" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# Download and extract appimagetool
wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage

# Create AppImage
if [ "$ARCH" = "x64" ]; then
    ARCHIVE_NAME="WowUSB-DS9-${VERSION}-${PLATFORM}.AppImage"
    ./appimagetool-x86_64.AppImage --no-appstream "$APPDIR" "$ARCHIVE_NAME"
    echo "AppImage created: $ARCHIVE_NAME"
else
    # For ARM64, we need a different appimagetool or cross-compilation setup
    echo "Building ARM64 AppImage requires additional setup"
    # For now, create a simple tarball
    tar -czf "WowUSB-DS9-${VERSION}-${PLATFORM}.tar.gz" -C "$APPDIR" usr
    echo "Tarball created: WowUSB-DS9-${VERSION}-${PLATFORM}.tar.gz"
fi

# Clean up
rm -rf "$APPDIR"
rm -f appimagetool-x86_64.AppImage

echo "AppImage build completed for ${PLATFORM}"