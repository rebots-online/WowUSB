# WowUSB-DS9 User Guide

This guide provides detailed instructions for using WowUSB-DS9 to create bootable Windows USB drives with advanced features.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Command Line Interface](#command-line-interface)
3. [Graphical Interface](#graphical-interface)
4. [Filesystem Options](#filesystem-options)
5. [Windows-To-Go](#windows-to-go)
6. [Advanced Usage](#advanced-usage)
7. [Tips and Best Practices](#tips-and-best-practices)

## Getting Started

### Requirements

- A Linux system with required dependencies installed
- A Windows ISO file or DVD
- A USB drive (8GB minimum, 16GB+ recommended for Windows 10/11, 32GB+ for Windows-To-Go)
- Administrator privileges (sudo access)

### Preparing Your USB Drive

Before using WowUSB-DS9, it's recommended to:

1. Backup any important data on the USB drive
2. Ensure the USB drive is properly connected
3. Identify the correct device path (e.g., `/dev/sdX`)

> ⚠️ **WARNING**: Be extremely careful when identifying your USB drive. Using the wrong device path can result in data loss on your system drives.

You can identify your USB drive using:

```bash
lsblk -o NAME,SIZE,MODEL,VENDOR,TYPE,MOUNTPOINT
```

## Command Line Interface

The command line interface provides full access to all features of WowUSB-DS9.

### Basic Usage

```bash
wowusb --device source.iso /dev/sdX
```

This will:
1. Format the USB drive
2. Create the appropriate partition structure
3. Install Windows bootloader
4. Copy all files from the ISO to the USB drive

### Common Options

| Option | Description |
|--------|-------------|
| `--device` | Create a bootable Windows USB drive from an ISO or DVD |
| `--partition` | Install Windows to an existing partition |
| `--target-filesystem` | Specify filesystem type (FAT, NTFS, EXFAT, F2FS, BTRFS, AUTO) |
| `--wintogo` | Create a Windows-To-Go installation |
| `--verbose` | Enable verbose output |
| `--help` | Show help message |

### Examples

**Create a bootable USB with automatic filesystem selection:**
```bash
wowusb --device windows10.iso /dev/sdX
```

**Create a bootable USB with NTFS filesystem:**
```bash
wowusb --device windows10.iso /dev/sdX --target-filesystem NTFS
```

**Create a Windows-To-Go installation:**
```bash
wowusb --device windows10.iso /dev/sdX --wintogo
```

**Install to a specific partition:**
```bash
wowusb --partition windows10.iso /dev/sdX1
```

## Graphical Interface

The graphical interface provides an easy-to-use alternative to the command line.

### Starting the GUI

```bash
woeusbgui
```

### Using the GUI

1. **Select Source**: Choose your Windows ISO file or DVD
2. **Select Target**: Choose your USB device
3. **Select Filesystem**: (Optional) Choose a specific filesystem or use automatic selection
4. **Advanced Options**: (Optional) Enable Windows-To-Go mode
5. **Install**: Click the Install button to begin the process

The GUI will show a progress bar and status messages during the installation process.

## Filesystem Options

WowUSB-DS9 supports multiple filesystems, each with different characteristics:

### FAT32
- **Best for**: Maximum compatibility with older systems
- **Limitations**: Cannot store files larger than 4GB
- **When to use**: For older Windows versions (Vista, 7) or when compatibility is critical

### NTFS
- **Best for**: Windows-native operations, large file support
- **Limitations**: May require additional drivers for UEFI boot on some systems
- **When to use**: For Windows 8/10/11 with large files when exFAT is not available

### exFAT
- **Best for**: Flash drives, cross-platform compatibility, large file support
- **Limitations**: Requires exFAT support in the system
- **When to use**: This is the recommended option for most modern Windows installations

### F2FS
- **Best for**: Flash drive performance
- **Limitations**: Less widely supported
- **When to use**: When optimizing for flash drive performance

### BTRFS
- **Best for**: Advanced features like compression
- **Limitations**: Less widely supported
- **When to use**: When advanced filesystem features are needed

## Windows-To-Go

Windows-To-Go allows you to create a portable Windows installation that runs directly from the USB drive without installing to the computer's internal drive.

### Requirements

- Windows 10 or 11 ISO
- USB drive (32GB+ recommended, USB 3.0+ for best performance)
- WowUSB-DS9 with Windows-To-Go option

### Creating a Windows-To-Go Drive

**Command Line:**
```bash
wowusb --device windows10.iso /dev/sdX --wintogo
```

**GUI:**
1. Select your Windows ISO
2. Select your USB device
3. Check the "Windows-To-Go" option
4. Click Install

### Windows-To-Go Features

- **Portable Windows**: Run Windows from any compatible computer
- **Persistent Storage**: Changes are saved between sessions
- **Hardware Adaptation**: Automatically adapts to different hardware
- **TPM Bypass**: Works on systems without TPM (for Windows 11)

### Limitations

- Performance depends on USB drive speed
- Some hardware-specific features may not work
- Not all applications are compatible with portable operation

## Advanced Usage

### Custom Partition Layout

For advanced users who need more control over the partition layout:

```bash
# Create a GPT partition table manually
sudo parted /dev/sdX mklabel gpt

# Create an EFI System Partition
sudo parted /dev/sdX mkpart ESP fat32 1MiB 261MiB
sudo parted /dev/sdX set 1 boot on
sudo parted /dev/sdX set 1 esp on

# Create a Microsoft Reserved Partition
sudo parted /dev/sdX mkpart MSR 261MiB 389MiB
sudo parted /dev/sdX set 2 msftres on

# Create a Windows partition
sudo parted /dev/sdX mkpart Windows 389MiB 100%

# Format the partitions
sudo mkfs.fat -F 32 -n ESP /dev/sdX1
sudo mkfs.ntfs -f -L Windows /dev/sdX3

# Install Windows to the third partition
wowusb --partition windows10.iso /dev/sdX3
```

### Using with Different Windows Versions

WowUSB-DS9 supports all modern Windows versions, but there are some version-specific considerations:

- **Windows Vista/7**: Use FAT32 for best compatibility
- **Windows 8/8.1**: Works with all filesystem options
- **Windows 10**: Works with all filesystem options, recommended for Windows-To-Go
- **Windows 11**: Requires TPM bypass for Windows-To-Go (automatically applied)

## Tips and Best Practices

### Performance Optimization

- Use a USB 3.0 or higher port and drive for best performance
- exFAT generally provides the best balance of performance and compatibility
- For Windows-To-Go, use a high-quality USB drive with good random I/O performance

### Troubleshooting

- If the USB drive isn't bootable, check the boot order in your BIOS/UEFI settings
- For UEFI boot issues, ensure Secure Boot is disabled or properly configured
- If Windows installation fails, try a different filesystem option

### Security Considerations

- Windows-To-Go drives contain a full Windows installation and should be secured
- Consider encrypting the drive if it contains sensitive information
- Always safely eject the drive before physically removing it

### Backup and Recovery

- Always back up important data before creating a bootable USB
- Keep a copy of your Windows ISO file for future use
- Consider creating a recovery partition on the USB drive

For more detailed troubleshooting information, see the [Troubleshooting Guide](TROUBLESHOOTING.md).
