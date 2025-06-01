# F2FS and BTRFS Testing Plan with Linux Distributions

**(C)2025 Robin L. M. Cheung, MBA**

## Overview

This document outlines a comprehensive testing plan for WowUSB-DS9's F2FS and BTRFS filesystem implementations with various Linux distributions. The tests focus on verifying bootability, performance, and persistence options across different hardware configurations.

## Prerequisites

### Required Hardware
- At least 2 different USB drives:
  - USB 3.0+ drive (16GB or larger)
  - USB 2.0 drive (8GB or larger)
- At least 2 different test computers:
  - Modern system with UEFI firmware
  - Older system with Legacy BIOS

### Required Software
- Linux distribution ISOs:
  - Ubuntu 22.04 LTS or newer
  - Fedora 38 or newer
  - Arch Linux (latest)
  - Debian 12 or newer
  - Linux Mint 21 or newer
- WowUSB-DS9 installed on a Linux system
- Required tools:
  - `f2fs-tools` package
  - `btrfs-progs` package
  - `squashfs-tools` package (for persistence setup)

## Test Matrix

| Test ID | Filesystem | Distribution | Boot Mode | Persistence | Computer Type | Expected Result |
|---------|------------|--------------|-----------|-------------|---------------|-----------------|
| F2FS-UBU-UEFI | F2FS | Ubuntu | UEFI | No | Modern | Pass |
| F2FS-UBU-LEGACY | F2FS | Ubuntu | Legacy | No | Older | Pass |
| F2FS-UBU-UEFI-PERS | F2FS | Ubuntu | UEFI | Yes | Modern | Pass |
| F2FS-FED-UEFI | F2FS | Fedora | UEFI | No | Modern | Pass |
| F2FS-FED-LEGACY | F2FS | Fedora | Legacy | No | Older | Pass |
| F2FS-FED-UEFI-PERS | F2FS | Fedora | UEFI | Yes | Modern | Pass |
| F2FS-ARCH-UEFI | F2FS | Arch | UEFI | No | Modern | Pass |
| F2FS-ARCH-LEGACY | F2FS | Arch | Legacy | No | Older | Pass |
| F2FS-DEB-UEFI | F2FS | Debian | UEFI | No | Modern | Pass |
| F2FS-DEB-LEGACY | F2FS | Debian | Legacy | No | Older | Pass |
| F2FS-MINT-UEFI | F2FS | Mint | UEFI | No | Modern | Pass |
| F2FS-MINT-LEGACY | F2FS | Mint | Legacy | No | Older | Pass |
| BTRFS-UBU-UEFI | BTRFS | Ubuntu | UEFI | No | Modern | Pass |
| BTRFS-UBU-LEGACY | BTRFS | Ubuntu | Legacy | No | Older | Pass |
| BTRFS-UBU-UEFI-PERS | BTRFS | Ubuntu | UEFI | Yes | Modern | Pass |
| BTRFS-FED-UEFI | BTRFS | Fedora | UEFI | No | Modern | Pass |
| BTRFS-FED-LEGACY | BTRFS | Fedora | Legacy | No | Older | Pass |
| BTRFS-FED-UEFI-PERS | BTRFS | Fedora | UEFI | Yes | Modern | Pass |
| BTRFS-ARCH-UEFI | BTRFS | Arch | UEFI | No | Modern | Pass |
| BTRFS-ARCH-LEGACY | BTRFS | Arch | Legacy | No | Older | Pass |
| BTRFS-DEB-UEFI | BTRFS | Debian | UEFI | No | Modern | Pass |
| BTRFS-DEB-LEGACY | BTRFS | Debian | Legacy | No | Older | Pass |
| BTRFS-MINT-UEFI | BTRFS | Mint | UEFI | No | Modern | Pass |
| BTRFS-MINT-LEGACY | BTRFS | Mint | Legacy | No | Older | Pass |

## Detailed Test Procedures

### 1. F2FS Filesystem Tests

#### 1.1 Preparation
- [ ] Insert the USB drive into the Linux machine
- [ ] Ensure that the USB drive is not mounted
  ```bash
  # Replace sdX with your device
  sudo umount /dev/sdX*
  ```
- [ ] Verify F2FS tools are installed
  ```bash
  # Check for f2fs-tools
  which mkfs.f2fs
  ```

#### 1.2 Create F2FS USB Drive with Ubuntu (No Persistence)
- [ ] Run WowUSB-DS9 with F2FS filesystem
  ```bash
  # For GUI
  sudo wowusbgui
  # For CLI
  sudo wowusb --device /path/to/ubuntu.iso /dev/sdX --target-filesystem F2FS
  ```
- [ ] Monitor progress indicators
- [ ] Note any warnings or errors
- [ ] Record the total time taken for the operation

#### 1.3 Verify F2FS Filesystem
- [ ] Check for completion message
- [ ] Verify filesystem was created as F2FS
  ```bash
  lsblk -f /dev/sdX1  # Should show f2fs filesystem
  ```
- [ ] Mount the USB drive
  ```bash
  sudo mkdir -p /mnt/usb
  sudo mount /dev/sdX1 /mnt/usb
  ```
- [ ] Verify files were copied correctly
  ```bash
  # Check for essential boot files
  ls -la /mnt/usb/boot
  ls -la /mnt/usb/EFI  # For UEFI boot
  ```
- [ ] Unmount the USB drive
  ```bash
  sudo umount /mnt/usb
  ```

#### 1.4 Test Bootability (UEFI Mode)
- [ ] Insert USB drive into test computer with UEFI firmware
- [ ] Enter UEFI boot menu (typically F12, F10, or ESC)
- [ ] Select USB drive from UEFI boot options
- [ ] Verify Linux boot menu appears
- [ ] Select "Try Ubuntu without installing" or equivalent
- [ ] Verify Linux desktop loads correctly
- [ ] Record boot time and any issues encountered

#### 1.5 Test Bootability (Legacy BIOS Mode)
- [ ] Insert USB drive into test computer with Legacy BIOS
- [ ] Enter boot menu
- [ ] Select USB drive from boot options
- [ ] Verify Linux boot menu appears
- [ ] Select "Try Ubuntu without installing" or equivalent
- [ ] Verify Linux desktop loads correctly
- [ ] Record boot time and any issues encountered

#### 1.6 Create F2FS USB Drive with Ubuntu (With Persistence)
- [ ] Run WowUSB-DS9 with F2FS filesystem and persistence option
  ```bash
  # For CLI
  sudo wowusb --device /path/to/ubuntu.iso /dev/sdX --target-filesystem F2FS --persistence 4096
  ```
- [ ] Monitor progress indicators
- [ ] Note any warnings or errors
- [ ] Record the total time taken for the operation

#### 1.7 Test Persistence
- [ ] Boot the USB drive on test computer
- [ ] Create a test file on the desktop
- [ ] Install a small application
- [ ] Change system settings (wallpaper, etc.)
- [ ] Reboot the computer
- [ ] Verify that all changes persist after reboot
- [ ] Record any issues encountered

#### 1.8 Repeat for Other Linux Distributions
- [ ] Repeat steps 1.2-1.5 for each Linux distribution in the test matrix
- [ ] Note any distribution-specific issues or behaviors

### 2. BTRFS Filesystem Tests

#### 2.1 Preparation
- [ ] Insert the USB drive into the Linux machine
- [ ] Ensure that the USB drive is not mounted
  ```bash
  # Replace sdX with your device
  sudo umount /dev/sdX*
  ```
- [ ] Verify BTRFS tools are installed
  ```bash
  # Check for btrfs-progs
  which mkfs.btrfs
  ```

#### 2.2 Create BTRFS USB Drive with Ubuntu (No Persistence)
- [ ] Run WowUSB-DS9 with BTRFS filesystem
  ```bash
  # For GUI
  sudo wowusbgui
  # For CLI
  sudo wowusb --device /path/to/ubuntu.iso /dev/sdX --target-filesystem BTRFS
  ```
- [ ] Monitor progress indicators
- [ ] Note any warnings or errors
- [ ] Record the total time taken for the operation

#### 2.3 Verify BTRFS Filesystem
- [ ] Check for completion message
- [ ] Verify filesystem was created as BTRFS
  ```bash
  lsblk -f /dev/sdX1  # Should show btrfs filesystem
  ```
- [ ] Mount the USB drive
  ```bash
  sudo mkdir -p /mnt/usb
  sudo mount /dev/sdX1 /mnt/usb
  ```
- [ ] Verify files were copied correctly
  ```bash
  # Check for essential boot files
  ls -la /mnt/usb/boot
  ls -la /mnt/usb/EFI  # For UEFI boot
  ```
- [ ] Check BTRFS-specific features
  ```bash
  # Check subvolumes
  sudo btrfs subvolume list /mnt/usb
  
  # Check compression
  sudo btrfs filesystem df /mnt/usb
  ```
- [ ] Unmount the USB drive
  ```bash
  sudo umount /mnt/usb
  ```

#### 2.4 Test Bootability (UEFI Mode)
- [ ] Follow the same procedure as in step 1.4

#### 2.5 Test Bootability (Legacy BIOS Mode)
- [ ] Follow the same procedure as in step 1.5

#### 2.6 Create BTRFS USB Drive with Ubuntu (With Persistence)
- [ ] Run WowUSB-DS9 with BTRFS filesystem and persistence option
  ```bash
  # For CLI
  sudo wowusb --device /path/to/ubuntu.iso /dev/sdX --target-filesystem BTRFS --persistence 4096
  ```
- [ ] Monitor progress indicators
- [ ] Note any warnings or errors
- [ ] Record the total time taken for the operation

#### 2.7 Test Persistence
- [ ] Follow the same procedure as in step 1.7

#### 2.8 Test BTRFS-Specific Features
- [ ] Boot the USB drive on test computer
- [ ] Open terminal
- [ ] Test compression effectiveness
  ```bash
  # Create a compressible file
  dd if=/dev/zero of=test_file bs=1M count=100
  
  # Check actual space used
  du -h test_file
  ```
- [ ] Test snapshot functionality (if implemented)
  ```bash
  # Create a snapshot
  sudo btrfs subvolume snapshot / /snapshot_1
  
  # Verify snapshot
  sudo btrfs subvolume list /
  ```
- [ ] Record any issues encountered

#### 2.9 Repeat for Other Linux Distributions
- [ ] Repeat steps 2.2-2.5 for each Linux distribution in the test matrix
- [ ] Note any distribution-specific issues or behaviors

### 3. Performance Comparison

#### 3.1 Creation Time Comparison
- [ ] Compare the time taken to create F2FS vs BTRFS USB drives
- [ ] Record the results in the table below:

| Filesystem | Distribution | USB Type | Creation Time |
|------------|--------------|----------|---------------|
| F2FS       | Ubuntu       | USB 3.0  |               |
| F2FS       | Ubuntu       | USB 2.0  |               |
| F2FS       | Fedora       | USB 3.0  |               |
| F2FS       | Fedora       | USB 2.0  |               |
| BTRFS      | Ubuntu       | USB 3.0  |               |
| BTRFS      | Ubuntu       | USB 2.0  |               |
| BTRFS      | Fedora       | USB 3.0  |               |
| BTRFS      | Fedora       | USB 2.0  |               |

#### 3.2 Boot Time Comparison
- [ ] Compare the boot time for F2FS vs BTRFS USB drives
- [ ] Record the results in the table below:

| Filesystem | Distribution | Boot Mode | Boot Time |
|------------|--------------|-----------|-----------|
| F2FS       | Ubuntu       | UEFI      |           |
| F2FS       | Ubuntu       | Legacy    |           |
| F2FS       | Fedora       | UEFI      |           |
| F2FS       | Fedora       | Legacy    |           |
| BTRFS      | Ubuntu       | UEFI      |           |
| BTRFS      | Ubuntu       | Legacy    |           |
| BTRFS      | Fedora       | UEFI      |           |
| BTRFS      | Fedora       | Legacy    |           |

#### 3.3 File Operation Performance
- [ ] Test file operations on both filesystems
- [ ] Record the results in the table below:

| Filesystem | Operation | Time (seconds) |
|------------|-----------|----------------|
| F2FS       | Copy 1GB file |            |
| F2FS       | Create 1000 small files |  |
| F2FS       | Delete 1000 small files |  |
| BTRFS      | Copy 1GB file |            |
| BTRFS      | Create 1000 small files |  |
| BTRFS      | Delete 1000 small files |  |

## Persistence Implementation

### F2FS Persistence

F2FS persistence can be implemented using an overlay filesystem approach. This section outlines the technical details for implementing persistence with F2FS.

#### Partition Layout
For a USB drive with F2FS and persistence:
1. EFI System Partition (FAT32) - For UEFI boot support
2. Main F2FS Partition - For the Linux distribution files
3. Persistence Partition (F2FS) - For storing persistent changes

#### Persistence Setup
The persistence setup involves creating an overlay filesystem that combines the read-only Linux distribution with a writable layer:

1. Create a persistence.conf file in the persistence partition:
   ```
   / union
   ```

2. Modify the boot parameters to include:
   ```
   persistent persistence-label=persistence
   ```

3. For Ubuntu-based distributions, the casper-rw file or partition is used.
4. For Fedora, the overlay filesystem is configured in the boot options.
5. For Arch Linux, custom hooks may be required.

### BTRFS Persistence

BTRFS offers native features that can be leveraged for persistence, such as subvolumes and snapshots.

#### Partition Layout
For a USB drive with BTRFS and persistence:
1. EFI System Partition (FAT32) - For UEFI boot support
2. Main BTRFS Partition - For both the Linux distribution files and persistence

#### Persistence Setup
The persistence setup with BTRFS can leverage subvolumes:

1. Create a "rootfs" subvolume for the Linux distribution files
2. Create a "persistence" subvolume for persistent changes
3. Configure the boot parameters to use both subvolumes in an overlay setup

#### Snapshot Management
BTRFS allows for snapshot management, which can be useful for:
1. Creating recovery points
2. Rolling back to previous states
3. Managing multiple configurations

## Distribution-Specific Considerations

### Ubuntu/Linux Mint
- Uses casper for live boot
- Persistence typically implemented with a casper-rw file or partition
- Well-documented persistence options

### Fedora
- Uses dracut for live boot
- Persistence implemented with overlay filesystem
- May require specific boot parameters

### Arch Linux
- Uses archiso for live boot
- Persistence less standardized
- May require custom initramfs hooks

### Debian
- Uses live-boot for live boot
- Persistence similar to Ubuntu
- May have different boot parameters

## Test Results

### Installation Phase
* Errors encountered (if any): _____________________
* Installation duration: _____________________
* Final filesystem type: _____________________

### Boot Testing
* Successfully booted? (Yes/No): _____________________
* Linux desktop loaded? (Yes/No): _____________________
* Boot time: _____________________

### Persistence Testing
* Changes persisted after reboot? (Yes/No): _____________________
* Applications remained installed? (Yes/No): _____________________
* System settings preserved? (Yes/No): _____________________

### Hardware Details
* USB Drive: 
  - Make/Model: _____________________
  - Capacity: _____________________
  - Interface: _____________________
* Test Computer:
  - Make/Model: _____________________
  - CPU: _____________________
  - RAM: _____________________
  - BIOS/UEFI Mode: _____________________
  - Boot type (Legacy/UEFI): _____________________

### Additional Observations
_____________________
_____________________
_____________________

## Troubleshooting Common Issues

### F2FS-Specific Issues
- **"F2FS filesystem not supported"**: Ensure f2fs-tools is installed
- **Slow performance**: Try using a different USB drive, preferably USB 3.0+
- **Corruption after heavy use**: F2FS is optimized for flash drives but may still experience issues with frequent writes

### BTRFS-Specific Issues
- **"BTRFS filesystem not supported"**: Ensure btrfs-progs is installed
- **Subvolume errors**: Check if the distribution supports BTRFS subvolumes properly
- **Compression issues**: Some distributions may not enable compression by default

### Persistence Issues
- **Changes not persisting**: Verify persistence partition is properly configured
- **Boot failures with persistence**: Try reducing persistence size
- **Slow performance with persistence**: This is normal, especially on USB 2.0 drives

### General Issues
- **USB not detected in boot menu**: Ensure USB is properly connected and try a different USB port
- **Linux fails to boot**: Verify the ISO file is not corrupted
- **Slow boot time**: This is normal for USB drives, especially USB 2.0

## Implementation Recommendations

Based on the test results, the following recommendations can be made for implementing F2FS and BTRFS support in WowUSB-DS9:

### F2FS Implementation
1. **Default Parameters**:
   - Block size: 4KB
   - Segment size: 2MB
   - Sections per zone: 1
   - Overprovisioning factor: 5%

2. **Device-Specific Optimizations**:
   - For USB flash drives: Increase overprovisioning to 10%
   - For SSDs: Use default parameters
   - For older USB 2.0 drives: Reduce segment size to 1MB

3. **Persistence Implementation**:
   - Use a separate F2FS partition for persistence
   - Create a persistence.conf file with appropriate settings
   - Add boot parameters for the specific distribution

### BTRFS Implementation
1. **Default Parameters**:
   - Node size: 16KB
   - Sector size: 4KB
   - Enable compression: zstd:3

2. **Device-Specific Optimizations**:
   - For USB flash drives: Enable SSD mode
   - For SSDs: Enable SSD mode and TRIM
   - For older USB 2.0 drives: Use lighter compression (zstd:1)

3. **Persistence Implementation**:
   - Use subvolumes for persistence
   - Create a "rootfs" subvolume for the Linux distribution
   - Create a "persistence" subvolume for persistent changes
   - Configure boot parameters to use both subvolumes

## Conclusion
This test plan provides a comprehensive approach to verify WowUSB-DS9's F2FS and BTRFS filesystem implementations with various Linux distributions. By following these procedures, testers can ensure that the implementation meets the requirements for reliable Linux bootable USB creation with advanced filesystem features and persistence options.
