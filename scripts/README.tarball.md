# WowUSB-DS9 Tarball Installation

This tarball contains WowUSB-DS9, a Linux utility that enables you to create your own bootable Windows installation USB storage device from an existing Windows Installation disc or disk image.

## Installation

### Automatic Installation

To install WowUSB-DS9 automatically, run the included installation script as root:

```bash
sudo ./install.sh
```

This script will:
1. Detect your Linux distribution
2. Install required dependencies
3. Install WowUSB-DS9 to /usr/local
4. Set up desktop integration

### Manual Installation

If you prefer to install manually or the automatic installation fails, follow these steps:

1. Install the required dependencies for your distribution:

   **Debian/Ubuntu/Mint:**
   ```bash
   sudo apt-get update
   sudo apt-get install python3 python3-pip python3-wxgtk4.0 python3-termcolor grub2-common grub-pc-bin parted dosfstools ntfs-3g exfat-utils f2fs-tools btrfs-progs p7zip-full
   ```

   **Fedora/RHEL:**
   ```bash
   sudo dnf install python3 python3-pip python3-wxpython4 python3-termcolor grub2-common grub2-tools parted dosfstools ntfs-3g exfatprogs f2fs-tools btrfs-progs p7zip p7zip-plugins
   ```

   **Arch Linux:**
   ```bash
   sudo pacman -Sy python python-pip python-wxpython python-termcolor grub parted dosfstools ntfs-3g exfatprogs f2fs-tools btrfs-progs p7zip
   ```

   **openSUSE:**
   ```bash
   sudo zypper install python3 python3-pip python3-wxPython python3-termcolor grub2 parted dosfstools ntfs-3g exfatprogs f2fs-tools btrfs-progs p7zip
   ```

2. Create the necessary directories:
   ```bash
   sudo mkdir -p /usr/local/lib/wowusb-ds9
   sudo mkdir -p /usr/local/bin
   sudo mkdir -p /usr/local/share/applications
   sudo mkdir -p /usr/local/share/icons/WowUSB-DS9
   sudo mkdir -p /usr/local/share/polkit-1/actions
   ```

3. Copy the Python package:
   ```bash
   sudo cp -r WowUSB WoeUSB /usr/local/lib/wowusb-ds9/
   ```

4. Create a Python path file:
   ```bash
   sudo mkdir -p /usr/local/lib/python3/dist-packages
   echo "/usr/local/lib/wowusb-ds9" | sudo tee /usr/local/lib/python3/dist-packages/wowusb.pth
   ```

5. Install the executables:
   ```bash
   sudo install -m 755 bin/wowusb /usr/local/bin/
   sudo install -m 755 bin/wowusbgui /usr/local/bin/
   ```

6. Install desktop integration files:
   ```bash
   sudo install -m 644 share/applications/WowUSB-DS9.desktop /usr/local/share/applications/
   sudo install -m 644 share/icons/WowUSB-DS9/icon.ico /usr/local/share/icons/WowUSB-DS9/
   sudo install -m 644 share/polkit-1/actions/com.rebots.wowusb.ds9.policy /usr/local/share/polkit-1/actions/
   ```

7. Update desktop database and icon cache:
   ```bash
   sudo update-desktop-database -q
   sudo gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor
   ```

## Uninstallation

To uninstall WowUSB-DS9, run the included uninstallation script:

```bash
sudo ./uninstall.sh
```

Or manually remove the installed files:

```bash
sudo rm -f /usr/local/bin/wowusb
sudo rm -f /usr/local/bin/wowusbgui
sudo rm -rf /usr/local/lib/wowusb-ds9
sudo rm -f /usr/local/lib/python3/dist-packages/wowusb.pth
sudo rm -f /usr/local/share/applications/WowUSB-DS9.desktop
sudo rm -rf /usr/local/share/icons/WowUSB-DS9
sudo rm -f /usr/local/share/polkit-1/actions/com.rebots.wowusb.ds9.policy
```

## Usage

After installation, you can run WowUSB-DS9 using:

- Command line: `wowusb`
- Graphical interface: `wowusbgui`

Or find it in your application menu as "WowUSB-DS9".

## Features

- Support for Windows Vista, 7, 8.x, 10, and 11
- Support for multiple filesystems (FAT32, NTFS, exFAT, F2FS, BTRFS)
- Automatic filesystem selection based on ISO content
- Support for files larger than 4GB
- Windows-To-Go support for portable Windows installations
- Both command-line and graphical interfaces

## License

WowUSB-DS9 is distributed under the GPL license.
