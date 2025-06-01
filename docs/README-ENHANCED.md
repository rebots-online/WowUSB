
# WowUSB-DS9

<div align="center">
<img src=".github/woeusb-logo.png" alt="brand" width="28%" />
</div>

_A Linux program to create advanced Windows USB installation media with extended filesystem support, multi-boot capabilities, and Windows-To-Go functionality._

## Features

WowUSB-DS9 enables you to create bootable Windows USB drives with advanced capabilities:

### Core Functionality
* Create bootable Windows installation USB from ISO images or DVDs
* Support for Windows Vista through Windows 11
* Compatible with both Legacy BIOS and UEFI boot modes
* Automatic filesystem selection based on ISO content

### Extended Filesystem Support
* **FAT32**: Default for maximum compatibility (with 4GB file size limit)
* **NTFS**: Support for larger files with integrated UEFI:NTFS bootloader
* **exFAT**: Combined large file support and cross-platform compatibility
* **F2FS**: Flash-friendly filesystem option for better performance
* **BTRFS**: Advanced Linux filesystem with additional features

### Advanced Capabilities
* **Windows-To-Go**: Run Windows directly from USB without installation
  * TPM bypass for Windows 11 compatibility
  * Portable driver configuration
  * Hardware adaptation for different systems
* **Optimized Formatting**: Device-specific optimizations for different storage types
  * SSD/Flash optimizations (alignment, cluster size)
  * HDD optimizations
* **Bundled Bootloaders**: Integrated UEFI:NTFS bootloader with fallback download

### User Interface
* Simple command-line interface for scripting and automation
* Graphical interface for ease of use
* Detailed progress reporting
* Comprehensive error handling and validation

## Installation

### Dependencies

#### Required Packages
```shell
sudo apt install git p7zip-full python3-pip python3-wxgtk4.0 grub2-common grub-pc-bin parted dosfstools ntfs-3g
```

#### Extended Filesystem Support
```shell
sudo apt install exfatprogs exfat-fuse f2fs-tools btrfs-progs
```

### Installation from Package Manager

#### Debian/Ubuntu
```shell
# Download the latest .deb package from the releases page
wget https://github.com/rebots-online/WowUSB/releases/latest/download/wowusb-ds9_0.3.0-1_all.deb

# Install the package
sudo apt install ./wowusb-ds9_0.3.0-1_all.deb
```

#### Arch Linux
```shell
yay -S wowusb-ds9
```

#### Fedora
```shell
sudo dnf install wowusb-ds9
```

### Installation from PyPI
```shell
sudo pip3 install WowUSB-DS9
```

### Installation from Source Code
```shell
git clone https://github.com/rebots-online/WowUSB.git
cd WowUSB
sudo pip3 install .
```

### Generic Linux Installation (tar.gz)
```shell
# Download the latest tar.gz package from the releases page
wget https://github.com/rebots-online/WowUSB/releases/latest/download/wowusb-ds9-0.3.0.tar.gz

# Extract the package
tar -xzf wowusb-ds9-0.3.0.tar.gz

# Run the installation script
cd wowusb-ds9-0.3.0
sudo ./install.sh
```

## Usage

### Command Line Interface

Basic usage:
```shell
wowusb --device source.iso /dev/sdX
```

Extended options:
```shell
# Specify filesystem type
wowusb --device source.iso /dev/sdX --target-filesystem NTFS

# Create Windows-To-Go installation
wowusb --device source.iso /dev/sdX --wintogo

# Format only a specific partition
wowusb --partition source.iso /dev/sdX1

# Automatic filesystem selection based on ISO content
wowusb --device source.iso /dev/sdX --target-filesystem AUTO
```

### Graphical Interface
```shell
wowusbgui
```

## Advanced Features

### Filesystem Selection

WowUSB-DS9 can automatically select the optimal filesystem based on the content of your Windows ISO:

1. If the ISO contains files larger than 4GB, it will select from available filesystems in this order:
   - exFAT (preferred for flash drives)
   - NTFS (good Windows compatibility)
   - F2FS (Linux-optimized flash filesystem)
   - BTRFS (advanced features)

2. If no files larger than 4GB are detected, it will use FAT32 for maximum compatibility.

You can also manually specify the filesystem with the `--target-filesystem` option.

### Windows-To-Go

Windows-To-Go allows you to create a portable Windows installation that runs directly from the USB drive:

```shell
wowusb --device windows10.iso /dev/sdX --wintogo
```

This creates a specialized partition layout:
1. EFI System Partition (ESP) - FAT32, 260MB
2. Microsoft Reserved Partition (MSR) - 128MB
3. Windows OS Partition - Selected filesystem, remaining space

For Windows 11, it automatically applies TPM and Secure Boot bypasses to ensure compatibility with a wide range of hardware.

### UEFI:NTFS Bootloader

When using NTFS or exFAT filesystems, WowUSB-DS9 automatically integrates the UEFI:NTFS bootloader to enable UEFI booting:

1. The bootloader is bundled with the package for offline use
2. If the bundled bootloader is missing or corrupted, it will download from GitHub
3. The bootloader is installed to a small FAT16 partition at the end of the drive

This enables UEFI firmware to boot from NTFS and exFAT filesystems, which aren't natively supported by most UEFI implementations.

### Device-Specific Optimizations

WowUSB-DS9 applies filesystem optimizations based on the detected device type:

- **SSD/Flash Drives**:
  - exFAT: 128KB cluster size, 1MB alignment
  - NTFS: 4KB cluster size, 4KB alignment

- **Hard Disk Drives**:
  - exFAT: 32KB cluster size
  - NTFS: 16KB cluster size

These optimizations improve performance and longevity of the storage device.

## Compatibility

### Supported Windows Versions
* Windows Vista, 7, 8.1, 10, 11
* All languages and editions (Home, Pro, Enterprise)
* Windows PE

### Supported Boot Modes
* Legacy BIOS boot
* UEFI boot
* Secure Boot (with limitations)

### Minimum Requirements
* USB drive: 8GB for basic installation, 32GB+ recommended for Windows-To-Go
* USB 3.0+ port recommended for best performance with Windows-To-Go

## Documentation
* [User Guide](USER_GUIDE.md) - Detailed usage instructions
* [Troubleshooting Guide](TROUBLESHOOTING.md) - Solutions to common issues
* [Technical Design](TECHNICAL_DESIGN.md) - Implementation details
* [Architecture](ARCHITECTURE.md) - System architecture and components
* [Changelog](CHANGELOG.md) - Version history and changes

## License
WowUSB-DS9 is distributed under the [GPL license](COPYING).

## Testing

WowUSB-DS9 includes a comprehensive test suite to ensure reliability:

### Automated Tests
* Unit tests for core functionality
* Filesystem handler tests
* Bootloader integration tests
* Windows-To-Go functionality tests

### Manual Testing
* Bootability tests across different hardware configurations
* Performance benchmarks for different filesystems
* Large file handling tests
* Windows-To-Go boot tests

To run the automated tests:
```shell
# Run all tests
python3 tests/run_tests.py

# Run specific test modules
python3 tests/test_filesystems.py
python3 tests/test_wintogo.py
```

## Development

### Setting Up Development Environment
```shell
# Clone the repository
git clone https://github.com/rebots-online/WowUSB.git
cd WowUSB

# Install development dependencies
pip3 install -e ".[dev]"
```

### Project Structure
```
WowUSB/
├── WowUSB/                  # Main package
│   ├── __init__.py          # Version information
│   ├── core.py              # Core functionality
│   ├── filesystem_handlers.py # Filesystem handlers
│   ├── bootloader.py        # Bootloader management
│   ├── utils.py             # Utility functions
│   ├── workaround.py        # Workarounds for specific issues
│   └── data/                # Bundled data files
│       └── bootloaders/     # Bundled bootloader images
├── tests/                   # Test suite
├── scripts/                 # Build and packaging scripts
├── debian/                  # Debian package configuration
├── miscellaneous/           # Desktop integration files
└── docs/                    # Documentation
```

### Building Packages

#### PyPI Package
```shell
python3 scripts/build_package.py
```

#### Debian Package
```shell
./scripts/build_deb.sh
```

#### Generic Linux Package (tar.gz)
```shell
./scripts/create_tarball.sh
```

### Contributing
Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Roadmap

Future development plans include:

### Phase 1: Core Enhancements
* Performance optimizations for large file copying
* Additional filesystem validation and recovery options
* Enhanced progress reporting and logging

### Phase 2: Multi-Boot Support
* Support for multiple Windows versions on a single USB
* GRUB2-based boot menu configuration
* Chainloading for different operating systems

### Phase 3: Linux Support
* Linux Live USB with persistence
* F2FS and BTRFS optimizations for Linux distributions
* Hybrid Windows/Linux multi-boot support

### Phase 4: Advanced UI
* Redesigned graphical interface with simple/advanced modes
* Visual disk layout representation
* Configuration profiles for repeated operations

## Acknowledgments

WowUSB-DS9 builds upon the work of:
* [WoeUSB](https://github.com/slacka/WoeUSB)
* [WoeUSB-ng](https://github.com/WoeUSB/WoeUSB-ng)
* [UEFI:NTFS](https://github.com/pbatard/uefi-ntfs) by Pete Batard

Special thanks to all contributors and testers who have helped improve this project.