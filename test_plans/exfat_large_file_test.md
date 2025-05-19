
# Enhanced Test Plan: exFAT and NTFS Large File Handling

**(C)2025 Robin L. M. Cheung, MBA**

## Objective
Verify that WowUSB-DS9 correctly creates bootable USB drives with exFAT and NTFS filesystems and properly handles large ISO files (>4GB) across diverse hardware configurations.

## Test Environment Requirements

### Hardware
* At least 2 different USB drives:
  * USB 3.0+ drive (16GB or larger)
  * USB 2.0 drive (8GB or larger)
* At least 2 different test computers:
  * Modern system with UEFI firmware
  * Older system with Legacy BIOS

### Software
* Windows 10 or 11 ISO file larger than 4GB
* Linux machine with WowUSB-DS9 installed
* Required tools:
  * exfatprogs or exfat-utils
  * ntfs-3g
  * md5sum or sha256sum

## Test Matrix

| Test ID           | Filesystem | USB Type | Boot Mode | Computer Type | Expected Result |
|-------------------|------------|----------|-----------|---------------|-----------------|
| EX-USB3-UEFI      | exFAT      | USB 3.0  | UEFI      | Modern        | Pass            |
| EX-USB3-LEGACY    | exFAT      | USB 3.0  | Legacy    | Older         | Pass            |
| EX-USB2-UEFI      | exFAT      | USB 2.0  | UEFI      | Modern        | Pass            |
| EX-USB2-LEGACY    | exFAT      | USB 2.0  | Legacy    | Older         | Pass            |
| NTFS-USB3-UEFI    | NTFS       | USB 3.0  | UEFI      | Modern        | Pass            |
| NTFS-USB3-LEGACY  | NTFS       | USB 3.0  | Legacy    | Older         | Pass            |
| NTFS-USB2-UEFI    | NTFS       | USB 2.0  | UEFI      | Modern        | Pass            |
| NTFS-USB2-LEGACY  | NTFS       | USB 2.0  | Legacy    | Older         | Pass            |

## Detailed Test Procedures

### 1. exFAT Filesystem Tests

#### 1.1 Preparation
- [ ] Insert the USB drive into the Linux machine  
- [ ] Ensure that the USB drive is not mounted  
  ```bash
  # Replace sdX1 with your device partition
  sudo umount /dev/sdX1
  ```  
- [ ] Identify the Windows ISO and verify it contains files larger than 4GB  
  ```bash
  # Mount the ISO
  sudo mkdir -p /mnt/iso
  sudo mount -o loop /path/to/windows.iso /mnt/iso

  # Find files larger than 4GB
  find /mnt/iso -type f -size +4G -exec ls -lh {} \;

  # Calculate checksums of large files for later verification
  find /mnt/iso -type f -size +4G -exec md5sum {} \; > /tmp/original_checksums.txt

  # Unmount the ISO
  sudo umount /mnt/iso
  ```

#### 1.2 Create exFAT USB Drive
- [ ] Run WowUSB-DS9 with exFAT filesystem  
  ```bash
  # For GUI
  sudo wowusbgui
  # For CLI
  sudo wowusb --device /path/to/windows.iso /dev/sdX --target-filesystem EXFAT
  ```  
- [ ] Monitor progress indicators  
- [ ] Note any warnings or errors  
- [ ] Record the total time taken for the operation  

#### 1.3 Verify exFAT Filesystem
- [ ] Check for completion message  
- [ ] Verify filesystem was created as exFAT  
  ```bash
  lsblk -f /dev/sdX1  # Should show exfat filesystem
  ```  
- [ ] Mount the USB drive  
  ```bash
  sudo mkdir -p /mnt/usb
  sudo mount /dev/sdX1 /mnt/usb
  ```  
- [ ] Verify large files were copied correctly  
  ```bash
  # Find files larger than 4GB
  find /mnt/usb -type f -size +4G -exec ls -lh {} \;

  # Calculate checksums of large files
  find /mnt/usb -type f -size +4G -exec md5sum {} \; > /tmp/usb_checksums.txt

  # Compare checksums
  diff /tmp/original_checksums.txt /tmp/usb_checksums.txt
  ```  
- [ ] Unmount the USB drive  
  ```bash
  sudo umount /mnt/usb
  ```

#### 1.4 Test Bootability (UEFI Mode)
- [ ] Insert USB drive into test computer with UEFI firmware  
- [ ] Enter UEFI boot menu (typically F12, F10, or ESC)  
- [ ] Select USB drive from UEFI boot options  
- [ ] Verify Windows installer starts correctly  
- [ ] Proceed to the language selection screen  
- [ ] Exit installer  
- [ ] Record boot time and any issues encountered  

#### 1.5 Test Bootability (Legacy BIOS Mode)
- [ ] Insert USB drive into test computer with Legacy BIOS  
- [ ] Enter boot menu  
- [ ] Select USB drive from boot options  
- [ ] Verify Windows installer starts correctly  
- [ ] Proceed to the language selection screen  
- [ ] Exit installer  
- [ ] Record boot time and any issues encountered  

### 2. NTFS Filesystem Tests

#### 2.1 Preparation
- [ ] Insert the USB drive into the Linux machine  
- [ ] Ensure that the USB drive is not mounted  
  ```bash
  # Replace sdX1 with your device partition
  sudo umount /dev/sdX1
  ```  
- [ ] Identify the Windows ISO and verify it contains files larger than 4GB (as in step 1.1)  

#### 2.2 Create NTFS USB Drive
- [ ] Run WowUSB-DS9 with NTFS filesystem  
  ```bash
  # For GUI
  sudo wowusbgui
  # For CLI
  sudo wowusb --device /path/to/windows.iso /dev/sdX --target-filesystem NTFS
  ```  
- [ ] Monitor progress indicators  
- [ ] Note any warnings or errors  
- [ ] Record the total time taken for the operation  

#### 2.3 Verify NTFS Filesystem
- [ ] Check for completion message  
- [ ] Verify filesystem was created as NTFS  
  ```bash
  lsblk -f /dev/sdX1  # Should show ntfs filesystem
  ```  
- [ ] Mount the USB drive  
  ```bash
  sudo mkdir -p /mnt/usb
  sudo mount /dev/sdX1 /mnt/usb
  ```  
- [ ] Verify large files were copied correctly (as in step 1.3)  
- [ ] Unmount the USB drive  
  ```bash
  sudo umount /mnt/usb
  ```

#### 2.4 Test Bootability (UEFI Mode)
- [ ] Follow the same procedure as in step 1.4  

#### 2.5 Test Bootability (Legacy BIOS Mode)
- [ ] Follow the same procedure as in step 1.5  

### 3. Performance Comparison

#### 3.1 Creation Time Comparison
- [ ] Compare the time taken to create exFAT vs NTFS USB drives  
- [ ] Record the results in the table below:

| Filesystem | USB Type | Creation Time |
|------------|----------|---------------|
| exFAT      | USB 3.0  |               |
| exFAT      | USB 2.0  |               |
| NTFS       | USB 3.0  |               |
| NTFS       | USB 2.0  |               |

#### 3.2 Boot Time Comparison
- [ ] Compare the boot time for exFAT vs NTFS USB drives  
- [ ] Record the results in the table below:

| Filesystem | USB Type | Boot Mode | Boot Time |
|------------|----------|-----------|-----------|
| exFAT      | USB 3.0  | UEFI      |           |
| exFAT      | USB 3.0  | Legacy    |           |
| exFAT      | USB 2.0  | UEFI      |           |
| exFAT      | USB 2.0  | Legacy    |           |
| NTFS       | USB 3.0  | UEFI      |           |
| NTFS       | USB 3.0  | Legacy    |           |
| NTFS       | USB 2.0  | UEFI      |           |
| NTFS       | USB 2.0  | Legacy    |           |

## Test Results

### Installation Phase
* Errors encountered (if any): _____________________  
* Installation duration: _____________________  
* Final filesystem type: _____________________  

### Boot Testing
* Successfully booted? (Yes/No): _____________________  
* Windows installer started? (Yes/No): _____________________  
* Boot time: _____________________  

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

### exFAT-Specific Issues
- "exFAT filesystem not supported": Ensure exfat-utils/exfatprogs is installed  
- Slow performance: Try using a different USB drive, preferably USB 3.0+  
- Corruption after large file copy: Verify USB drive quality, try a different drive  

### NTFS-Specific Issues
- "UEFI boot fails with NTFS": Verify UEFI:NTFS bootloader was installed correctly  
- Permission issues: These are normal and can be ignored during testing  
- "NTFS signature is missing": Try reformatting the drive and recreating the bootable USB  

### General Issues
- USB not detected in boot menu: Ensure USB is properly connected and try a different USB port  
- Windows installer crashes: Verify the ISO file is not corrupted  
- Slow boot time: This is normal for USB drives, especially USB 2.0  

## Conclusion
This test plan provides a comprehensive approach to verify WowUSB-DS9's handling of large files with exFAT and NTFS filesystems across diverse hardware configurations. By following these procedures, testers can ensure that the implementation meets the requirements for reliable Windows installation media creation.