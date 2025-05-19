#!/bin/bash
# WowUSB-DS9 Uninstallation Script
# This script removes WowUSB-DS9 from the system

set -e

# Configuration
INSTALL_PREFIX="/usr/local"

# Print banner
echo "====================================================="
echo "  WowUSB-DS9 Uninstallation Script"
echo "====================================================="

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root"
    echo "Please run: sudo $0"
    exit 1
fi

# Confirm uninstallation
echo "This will remove WowUSB-DS9 from your system."
read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

# Remove files
echo "Removing files..."

# Remove executables
rm -f "$INSTALL_PREFIX/bin/wowusb"
rm -f "$INSTALL_PREFIX/bin/wowusbgui"

# Remove Python package
rm -rf "$INSTALL_PREFIX/lib/wowusb-ds9"
rm -f "$INSTALL_PREFIX/lib/python3/dist-packages/wowusb.pth"

# Remove desktop integration files
rm -f "$INSTALL_PREFIX/share/applications/WowUSB-DS9.desktop"
rm -rf "$INSTALL_PREFIX/share/icons/WowUSB-DS9"
rm -f "$INSTALL_PREFIX/share/polkit-1/actions/com.rebots.wowusb.ds9.policy"

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q
fi

# Update icon cache
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor 2>/dev/null || true
fi

# Clean up temporary files
echo "Cleaning up temporary files..."
rm -rf /tmp/WowUSB.*

echo "====================================================="
echo "  WowUSB-DS9 has been successfully uninstalled!"
echo "====================================================="
