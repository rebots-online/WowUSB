
<div align="center">
<h1>WowUSB-DS9</h1>
<img src=".github/woeusb-logo.png" alt="brand" width="28%" />
</div>

_A Linux program to create a Windows USB stick installer from a real Windows DVD or image with advanced filesystem support and Windows-To-Go capability._

**NEW: WowUSB-DS9 now supports large ISO files (>4GB) through NTFS, exFAT, F2FS and BTRFS filesystem support, plus Windows-To-Go functionality!**

This package contains two programs:

* **wowusb**: A command-line utility that enables you to create your own bootable Windows installation USB storage device from an existing Windows Installation disc or disk image
* **woeusbgui**: Graphic version of wowusb

## Features

* Support for Windows Vista, Windows 7, Window 8.x, Windows 10, and Windows 11
* Support for multiple filesystems with automatic selection based on ISO content:
  * **FAT32**: Default for maximum compatibility (with 4GB file size limit)
  * **NTFS**: Support for larger files with integrated UEFI:NTFS bootloader
  * **exFAT**: Combined large file support and cross-platform compatibility
  * **F2FS**: Flash-friendly filesystem option for better performance
  * **BTRFS**: Advanced Linux filesystem with additional features
* Windows-To-Go support for creating portable Windows installations that run directly from USB
* Both Legacy/MBR-style and UEFI boot modes
* Automatic detection of large files (>4GB) and filesystem selection

This project is a significant enhancement of the original [WoeUSB](https://github.com/slacka/WoeUSB) and [WoeUSB-ng](https://github.com/WoeUSB/WoeUSB-ng) projects.

## Installation

### Option 1: PyPI Package (All Linux Distributions)

```shell
# Install dependencies (example for Debian/Ubuntu)
sudo apt install git p7zip-full python3-pip python3-wxgtk4.0 grub2-common grub-pc-bin parted dosfstools ntfs-3g exfat-utils f2fs-tools btrfs-progs

# Install WowUSB-DS9
sudo pip3 install WowUSB-DS9
```

### Option 2: Debian Package (.deb)

```shell
# Download the latest .deb package from the releases page
wget https://github.com/rebots-online/WowUSB/releases/latest/download/wowusb-ds9_0.3.0-1_all.deb

# Install the package
sudo apt install ./wowusb-ds9_0.3.0-1_all.deb
```

### Option 3: Arch Linux

```shell
yay -S wowusb-ds9
```

### Option 4: Generic Linux Package (tar.gz)

```shell
# Download the latest tar.gz package from the releases page
wget https://github.com/rebots-online/WowUSB/releases/latest/download/wowusb-ds9-0.3.0.tar.gz

# Extract the package
tar -xzf wowusb-ds9-0.3.0.tar.gz

# Run the installation script
cd wowusb-ds9-0.3.0
sudo ./install.sh
```

### Option 5: Installation from Source Code

```shell
# Install dependencies (example for Debian/Ubuntu)
sudo apt install git p7zip-full python3-pip python3-wxgtk4.0 grub2-common grub-pc-bin parted dosfstools ntfs-3g exfat-utils f2fs-tools btrfs-progs

# Clone the repository
git clone https://github.com/rebots-online/WowUSB.git
cd WowUSB

# Install from source
sudo pip3 install .
```

## Dependency Requirements

| Distribution   | Required Packages                                                                                |
|----------------|--------------------------------------------------------------------------------------------------|
| Debian/Ubuntu  | `python3-pip python3-wxgtk4.0 grub2-common grub-pc-bin parted dosfstools ntfs-3g exfat-utils f2fs-tools btrfs-progs p7zip-full` |
| Fedora         | `python3-pip python3-wxpython4 grub2-common grub2-tools parted dosfstools ntfs-3g exfatprogs f2fs-tools btrfs-progs p7zip p7zip-plugins` |
| Arch Linux     | `python-pip python-wxpython grub parted dosfstools ntfs-3g exfatprogs f2fs-tools btrfs-progs p7zip` |
| openSUSE       | `python3-pip python3-wxPython grub2 parted dosfstools ntfs-3g exfatprogs f2fs-tools btrfs-progs p7zip` |

## Usage

### Command Line Interface

Basic usage:

```shell
wowusb --device source.iso /dev/sdX
```

Advanced options:

```shell
# Specify filesystem type
wowusb --device source.iso /dev/sdX --target-filesystem NTFS

# Create Windows-To-Go installation
wowusb --device source.iso /dev/sdX --wintogo

# Format only a specific partition
wowusb --partition source.iso /dev/sdX1
```

### Graphical Interface

```shell
woeusbgui
```

## Uninstallation

### PyPI Package

```shell
sudo pip3 uninstall WowUSB-DS9
sudo rm /usr/share/icons/WowUSB-DS9/icon.ico \
    /usr/share/applications/WowUSB-DS9.desktop \
    /usr/local/bin/woeusbgui
sudo rmdir /usr/share/icons/WowUSB-DS9/
```

### Debian Package

```shell
sudo apt remove wowusb-ds9
```

### Generic Linux Package

```shell
sudo ./uninstall.sh
```

## Advanced Filesystem Features

WowUSB-DS9 automatically detects if your Windows ISO contains files larger than 4GB and selects the appropriate filesystem:

| Filesystem | Used When                    | Requirements                | Features                                                             |
|------------|------------------------------|-----------------------------|----------------------------------------------------------------------|
| FAT32      | Default for maximum compatibility | dosfstools package           | Most compatible, 4GB file size limit                                |
| NTFS       | ISO contains files >4GB      | ntfs-3g package             | Windows-native, large file support, slower on flash drives          |
| exFAT      | ISO contains files >4GB      | exfat-utils/exfatprogs package | Optimized for flash drives, large file support, good cross-platform compatibility |
| F2FS       | ISO contains files >4GB      | f2fs-tools package          | Flash-friendly, optimized for flash storage performance             |
| BTRFS      | ISO contains files >4GB      | btrfs-progs package         | Advanced features like compression and snapshots                    |

The filesystem is automatically selected based on the detected content and available tools, with a preference order of exFAT > NTFS > F2FS > BTRFS > FAT32.

For detailed information on implementation, see the [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) file.

## Documentation

- [User Guide](USER_GUIDE.md) - Detailed usage instructions
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Solutions to common issues
- [Technical Design](TECHNICAL_DESIGN.md) - Implementation details
- [Changelog](CHANGELOG.md) - Version history and changes
- [Release Notes](RELEASE_NOTES.md) - Detailed information about the latest release

## License

WowUSB-DS9 is distributed under the [GPL license](COPYING).

