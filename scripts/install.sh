#!/bin/bash
# WowUSB-DS9 Installation Script
# This script installs WowUSB-DS9 on various Linux distributions

set -e

# Configuration
INSTALL_PREFIX="/usr/local"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Print banner
echo "====================================================="
echo "  WowUSB-DS9 Installation Script"
echo "====================================================="

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root"
    echo "Please run: sudo $0"
    exit 1
fi

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_VERSION=$VERSION_ID
        DISTRO_NAME=$NAME
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        DISTRO=$DISTRIB_ID
        DISTRO_VERSION=$DISTRIB_RELEASE
        DISTRO_NAME=$DISTRIB_DESCRIPTION
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
        DISTRO_VERSION=$(cat /etc/debian_version)
        DISTRO_NAME="Debian"
    elif [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
        DISTRO_NAME="Red Hat Enterprise Linux"
    elif [ -f /etc/fedora-release ]; then
        DISTRO="fedora"
        DISTRO_NAME="Fedora"
    elif [ -f /etc/arch-release ]; then
        DISTRO="arch"
        DISTRO_NAME="Arch Linux"
    elif [ -f /etc/SuSE-release ] || [ -f /etc/suse-release ]; then
        DISTRO="opensuse"
        DISTRO_NAME="openSUSE"
    else
        DISTRO="unknown"
        DISTRO_NAME="Unknown Distribution"
    fi
}

# Install dependencies based on distribution
install_dependencies() {
    echo "Detected distribution: $DISTRO_NAME"
    
    case "$DISTRO" in
        ubuntu|debian|linuxmint|pop|elementary|zorin)
            echo "Installing dependencies for Debian-based distribution..."
            apt-get update
            xargs apt-get install -y < "$SCRIPT_DIR/dependencies/debian.txt"
            ;;
        fedora|rhel|centos|rocky|alma)
            echo "Installing dependencies for Fedora/RHEL-based distribution..."
            dnf install -y $(cat "$SCRIPT_DIR/dependencies/fedora.txt")
            ;;
        arch|manjaro|endeavouros)
            echo "Installing dependencies for Arch-based distribution..."
            pacman -Sy --needed --noconfirm $(cat "$SCRIPT_DIR/dependencies/arch.txt")
            ;;
        opensuse|suse)
            echo "Installing dependencies for openSUSE..."
            zypper install -y $(cat "$SCRIPT_DIR/dependencies/opensuse.txt")
            ;;
        *)
            echo "Warning: Unsupported distribution. You may need to install dependencies manually."
            echo "Required packages:"
            echo "- Python 3"
            echo "- wxPython 4"
            echo "- termcolor"
            echo "- GRUB2"
            echo "- parted"
            echo "- dosfstools"
            echo "- ntfs-3g"
            echo "- exfat-utils or exfatprogs"
            echo "- f2fs-tools"
            echo "- btrfs-progs"
            echo "- p7zip"
            echo ""
            read -p "Continue with installation? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
            ;;
    esac
}

# Install Python package
install_python_package() {
    echo "Installing Python package..."
    
    # Create directories
    mkdir -p "$INSTALL_PREFIX/lib/wowusb-ds9"
    mkdir -p "$INSTALL_PREFIX/bin"
    mkdir -p "$INSTALL_PREFIX/share/applications"
    mkdir -p "$INSTALL_PREFIX/share/icons/WowUSB-DS9"
    mkdir -p "$INSTALL_PREFIX/share/polkit-1/actions"
    
    # Copy Python package
    cp -r "$SCRIPT_DIR/WowUSB" "$INSTALL_PREFIX/lib/wowusb-ds9/"
    cp -r "$SCRIPT_DIR/WoeUSB" "$INSTALL_PREFIX/lib/wowusb-ds9/"
    
    # Create Python path file
    mkdir -p "$INSTALL_PREFIX/lib/python3/dist-packages"
    cat > "$INSTALL_PREFIX/lib/python3/dist-packages/wowusb.pth" << EOF
$INSTALL_PREFIX/lib/wowusb-ds9
EOF
    
    # Install executables
    install -m 755 "$SCRIPT_DIR/bin/wowusb" "$INSTALL_PREFIX/bin/"
    install -m 755 "$SCRIPT_DIR/bin/wowusbgui" "$INSTALL_PREFIX/bin/"
    
    # Install desktop integration files
    install -m 644 "$SCRIPT_DIR/share/applications/WowUSB-DS9.desktop" "$INSTALL_PREFIX/share/applications/"
    install -m 644 "$SCRIPT_DIR/share/icons/WowUSB-DS9/icon.ico" "$INSTALL_PREFIX/share/icons/WowUSB-DS9/"
    install -m 644 "$SCRIPT_DIR/share/polkit-1/actions/com.rebots.wowusb.ds9.policy" "$INSTALL_PREFIX/share/polkit-1/actions/"
    
    # Update desktop database
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q
    fi
    
    # Update icon cache
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor 2>/dev/null || true
    fi
}

# Main installation process
main() {
    detect_distro
    install_dependencies
    install_python_package
    
    echo "====================================================="
    echo "  WowUSB-DS9 has been successfully installed!"
    echo "====================================================="
    echo ""
    echo "You can now run WowUSB-DS9 using:"
    echo "  Command line: wowusb"
    echo "  Graphical interface: wowusbgui"
    echo ""
    echo "Or find it in your application menu as 'WowUSB-DS9'"
    echo ""
}

# Run the main function
main
