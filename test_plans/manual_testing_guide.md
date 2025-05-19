# WowUSB-DS9 Manual Testing Guide

**(C)2025 Robin L. M. Cheung, MBA**

## Overview

This document provides a comprehensive guide for manually testing WowUSB-DS9's exFAT and NTFS implementations with large ISOs across diverse hardware configurations and virtual machines. The tests focus on verifying bootability in different boot modes (Legacy BIOS, UEFI) and testing Windows-To-Go functionality.

## Prerequisites

### Required Hardware
- At least 2 different physical computers with different hardware configurations
  - Ideally, include both newer UEFI-based systems and older BIOS-based systems
  - Include at least one system with Secure Boot capability
- At least 2 different USB drives
  - One USB 3.0+ drive (16GB or larger, preferably 32GB for Windows-To-Go tests)
  - One USB 2.0 drive (8GB or larger)

### Required Software
- Windows 10 ISO (64-bit, latest build)
- Windows 11 ISO (64-bit, latest build)
- VirtualBox, VMware, or QEMU for VM testing
- WowUSB-DS9 installed on a Linux system

### Test Environment Setup
- Create a test matrix tracking sheet (use the template in Appendix A)
- Prepare backup copies of all test ISOs
- Ensure all USB drives are properly identified and labeled

## Test Matrix

The test matrix covers combinations of:
1. **Filesystem Types**: exFAT, NTFS
2. **Windows Versions**: Windows 10, Windows 11
3. **Boot Modes**: Legacy BIOS, UEFI (Secure Boot off), UEFI (Secure Boot on)
4. **Installation Types**: Standard Installation, Windows-To-Go
5. **Hardware Types**: Physical machines, Virtual machines

## Test Procedures

### 1. Standard Installation Tests

#### 1.1 exFAT with Windows 10 ISO

**Test ID**: EX-W10-STD

**Preparation**:
1. Insert USB drive into Linux system
2. Run WowUSB-DS9:
   ```bash
   sudo wowusb --device /path/to/windows10.iso /dev/sdX --target-filesystem EXFAT
   ```
3. Wait for the process to complete
4. Verify the filesystem type:
   ```bash
   lsblk -f /dev/sdX1  # Should show exfat filesystem
   ```

**Test Procedure**:
1. **Legacy BIOS Boot Test**:
   - Insert USB drive into test machine
   - Enter boot menu (typically F12, F10, or ESC)
   - Select USB drive from boot menu
   - Verify Windows installer starts correctly
   - Proceed to the language selection screen
   - Exit installer

2. **UEFI Boot Test (Secure Boot OFF)**:
   - Enter UEFI settings on test machine
   - Disable Secure Boot
   - Save and exit
   - Enter boot menu
   - Select USB drive from UEFI boot options
   - Verify Windows installer starts correctly
   - Proceed to the language selection screen
   - Exit installer

3. **UEFI Boot Test (Secure Boot ON)**:
   - Enter UEFI settings on test machine
   - Enable Secure Boot
   - Save and exit
   - Enter boot menu
   - Select USB drive from UEFI boot options
   - Note if Windows installer starts correctly
   - If successful, proceed to the language selection screen
   - Exit installer

**Expected Results**:
- USB drive should boot in Legacy BIOS mode
- USB drive should boot in UEFI mode with Secure Boot disabled
- USB drive may or may not boot in UEFI mode with Secure Boot enabled (document the result)
- Windows installer should start correctly in all successful boot scenarios
- No filesystem errors should be reported

#### 1.2 NTFS with Windows 10 ISO

**Test ID**: NTFS-W10-STD

**Preparation**:
1. Insert USB drive into Linux system
2. Run WowUSB-DS9:
   ```bash
   sudo wowusb --device /path/to/windows10.iso /dev/sdX --target-filesystem NTFS
   ```
3. Wait for the process to complete
4. Verify the filesystem type:
   ```bash
   lsblk -f /dev/sdX1  # Should show ntfs filesystem
   ```

**Test Procedure**:
- Follow the same test procedure as in Test ID: EX-W10-STD

**Expected Results**:
- Same as Test ID: EX-W10-STD

#### 1.3 exFAT with Windows 11 ISO

**Test ID**: EX-W11-STD

**Preparation**:
1. Insert USB drive into Linux system
2. Run WowUSB-DS9:
   ```bash
   sudo wowusb --device /path/to/windows11.iso /dev/sdX --target-filesystem EXFAT
   ```
3. Wait for the process to complete
4. Verify the filesystem type:
   ```bash
   lsblk -f /dev/sdX1  # Should show exfat filesystem
   ```

**Test Procedure**:
- Follow the same test procedure as in Test ID: EX-W10-STD

**Expected Results**:
- Same as Test ID: EX-W10-STD

#### 1.4 NTFS with Windows 11 ISO

**Test ID**: NTFS-W11-STD

**Preparation**:
1. Insert USB drive into Linux system
2. Run WowUSB-DS9:
   ```bash
   sudo wowusb --device /path/to/windows11.iso /dev/sdX --target-filesystem NTFS
   ```
3. Wait for the process to complete
4. Verify the filesystem type:
   ```bash
   lsblk -f /dev/sdX1  # Should show ntfs filesystem
   ```

**Test Procedure**:
- Follow the same test procedure as in Test ID: EX-W10-STD

**Expected Results**:
- Same as Test ID: EX-W10-STD

### 2. Windows-To-Go Tests

#### 2.1 exFAT with Windows 10 ISO (Windows-To-Go)

**Test ID**: EX-W10-WTG

**Preparation**:
1. Insert USB 3.0+ drive (32GB recommended) into Linux system
2. Run WowUSB-DS9 with Windows-To-Go option:
   ```bash
   sudo wowusb --device /path/to/windows10.iso /dev/sdX --target-filesystem EXFAT --wintogo
   ```
3. Wait for the process to complete (this will take longer than standard installation)
4. Verify the partition layout:
   ```bash
   lsblk /dev/sdX  # Should show 3 partitions: ESP, MSR, and Windows
   ```

**Test Procedure**:
1. **Boot Test on Machine A**:
   - Insert USB drive into test machine A
   - Boot from USB drive (UEFI mode preferred)
   - Verify Windows boots to setup screen
   - Complete initial Windows setup
   - Verify Windows desktop appears
   - Check Device Manager for driver issues
   - Shut down Windows

2. **Boot Test on Machine B (Different Hardware)**:
   - Insert USB drive into test machine B (with different hardware)
   - Boot from USB drive
   - Verify Windows boots correctly
   - Verify previously created user account and settings are preserved
   - Check Device Manager for driver issues
   - Shut down Windows

3. **Performance Test**:
   - Boot Windows-To-Go on the fastest available machine
   - Measure boot time
   - Open File Explorer and navigate through folders
   - Note any lag or performance issues
   - Run basic applications (Notepad, Calculator, etc.)
   - Shut down Windows

**Expected Results**:
- Windows-To-Go should boot successfully on different hardware
- User settings should persist between boots on different machines
- Windows should automatically adapt to different hardware
- Performance may vary based on USB drive speed, but should be usable

#### 2.2 NTFS with Windows 10 ISO (Windows-To-Go)

**Test ID**: NTFS-W10-WTG

**Preparation**:
1. Insert USB 3.0+ drive (32GB recommended) into Linux system
2. Run WowUSB-DS9 with Windows-To-Go option:
   ```bash
   sudo wowusb --device /path/to/windows10.iso /dev/sdX --target-filesystem NTFS --wintogo
   ```
3. Wait for the process to complete
4. Verify the partition layout:
   ```bash
   lsblk /dev/sdX  # Should show 3 partitions: ESP, MSR, and Windows
   ```

**Test Procedure**:
- Follow the same test procedure as in Test ID: EX-W10-WTG

**Expected Results**:
- Same as Test ID: EX-W10-WTG

#### 2.3 exFAT with Windows 11 ISO (Windows-To-Go)

**Test ID**: EX-W11-WTG

**Preparation**:
1. Insert USB 3.0+ drive (32GB recommended) into Linux system
2. Run WowUSB-DS9 with Windows-To-Go option:
   ```bash
   sudo wowusb --device /path/to/windows11.iso /dev/sdX --target-filesystem EXFAT --wintogo
   ```
3. Wait for the process to complete
4. Verify the partition layout:
   ```bash
   lsblk /dev/sdX  # Should show 3 partitions: ESP, MSR, and Windows
   ```

**Test Procedure**:
- Follow the same test procedure as in Test ID: EX-W10-WTG
- Additionally, verify that Windows 11 runs without TPM/Secure Boot errors

**Expected Results**:
- Windows 11 should boot successfully despite TPM/Secure Boot requirements
- Other results same as Test ID: EX-W10-WTG

#### 2.4 NTFS with Windows 11 ISO (Windows-To-Go)

**Test ID**: NTFS-W11-WTG

**Preparation**:
1. Insert USB 3.0+ drive (32GB recommended) into Linux system
2. Run WowUSB-DS9 with Windows-To-Go option:
   ```bash
   sudo wowusb --device /path/to/windows11.iso /dev/sdX --target-filesystem NTFS --wintogo
   ```
3. Wait for the process to complete
4. Verify the partition layout:
   ```bash
   lsblk /dev/sdX  # Should show 3 partitions: ESP, MSR, and Windows
   ```

**Test Procedure**:
- Follow the same test procedure as in Test ID: EX-W11-WTG

**Expected Results**:
- Same as Test ID: EX-W11-WTG

### 3. Virtual Machine Tests

#### 3.1 VirtualBox Tests

**Test ID**: VM-VB-TEST

**Preparation**:
1. Create a new VM in VirtualBox:
   - Type: Microsoft Windows
   - Version: Windows 10/11 (64-bit)
   - Memory: 4GB or more
   - Do not create a virtual hard disk
2. Configure VM settings:
   - System > Motherboard > Enable EFI (for UEFI tests)
   - USB > Enable USB 3.0 Controller
   - Add a filter for your USB drive

**Test Procedure**:
1. Insert prepared USB drive into computer
2. Start the VM with the USB drive attached
3. If necessary, enter boot menu (typically F12)
4. Select USB drive from boot options
5. Verify Windows installer/Windows-To-Go starts correctly
6. Exit VM

**Expected Results**:
- USB drive should boot in the VM
- Windows installer or Windows-To-Go should start correctly
- No filesystem errors should be reported

#### 3.2 VMware Tests

**Test ID**: VM-VMW-TEST

**Preparation**:
1. Create a new VM in VMware:
   - Guest OS: Windows 10/11 x64
   - Do not create a virtual disk
2. Configure VM settings:
   - Options > Advanced > Firmware Type > UEFI (for UEFI tests)
   - USB Controller > USB 3.0
   - Add the USB drive to the VM

**Test Procedure**:
- Follow the same test procedure as in Test ID: VM-VB-TEST

**Expected Results**:
- Same as Test ID: VM-VB-TEST

### 4. Large File Handling Tests

#### 4.1 exFAT Large File Test

**Test ID**: EX-LARGE-FILE

**Preparation**:
1. Identify files larger than 4GB in the Windows ISO
   ```bash
   find /path/to/mounted/windows/iso -type f -size +4G
   ```
2. Create a USB drive with exFAT filesystem
   ```bash
   sudo wowusb --device /path/to/windows.iso /dev/sdX --target-filesystem EXFAT
   ```

**Test Procedure**:
1. Mount the USB drive
   ```bash
   sudo mkdir -p /mnt/usb
   sudo mount /dev/sdX1 /mnt/usb
   ```
2. Verify large files were copied correctly
   ```bash
   find /mnt/usb -type f -size +4G -exec ls -lh {} \;
   ```
3. Compare checksums of large files
   ```bash
   # For each large file
   md5sum /path/to/original/large/file
   md5sum /mnt/usb/path/to/copied/large/file
   ```
4. Unmount the USB drive
   ```bash
   sudo umount /mnt/usb
   ```

**Expected Results**:
- All files larger than 4GB should be present on the USB drive
- Checksums should match between original and copied files
- No filesystem errors should be reported

#### 4.2 NTFS Large File Test

**Test ID**: NTFS-LARGE-FILE

**Preparation**:
1. Identify files larger than 4GB in the Windows ISO
   ```bash
   find /path/to/mounted/windows/iso -type f -size +4G
   ```
2. Create a USB drive with NTFS filesystem
   ```bash
   sudo wowusb --device /path/to/windows.iso /dev/sdX --target-filesystem NTFS
   ```

**Test Procedure**:
- Follow the same test procedure as in Test ID: EX-LARGE-FILE

**Expected Results**:
- Same as Test ID: EX-LARGE-FILE

## Test Results Documentation

For each test, document the following information:

1. **Test Environment**:
   - Test ID
   - Date and time
   - Tester name
   - Hardware details (make/model, CPU, RAM, firmware version)
   - USB drive details (make/model, capacity, interface)
   - Windows ISO version

2. **Test Results**:
   - Pass/Fail status
   - Boot time (if applicable)
   - Any errors or warnings encountered
   - Screenshots of key steps (if possible)
   - Notes on performance or behavior

3. **Issues and Observations**:
   - Any unexpected behavior
   - Workarounds applied (if any)
   - Suggestions for improvement

## Appendix A: Test Matrix Template

| Test ID | Filesystem | Windows Version | Boot Mode | Installation Type | Hardware Type | Result | Notes |
|---------|------------|-----------------|-----------|-------------------|---------------|--------|-------|
| EX-W10-STD-LEGACY | exFAT | Windows 10 | Legacy BIOS | Standard | Physical | | |
| EX-W10-STD-UEFI | exFAT | Windows 10 | UEFI (SB Off) | Standard | Physical | | |
| EX-W10-STD-UEFI-SB | exFAT | Windows 10 | UEFI (SB On) | Standard | Physical | | |
| NTFS-W10-STD-LEGACY | NTFS | Windows 10 | Legacy BIOS | Standard | Physical | | |
| NTFS-W10-STD-UEFI | NTFS | Windows 10 | UEFI (SB Off) | Standard | Physical | | |
| NTFS-W10-STD-UEFI-SB | NTFS | Windows 10 | UEFI (SB On) | Standard | Physical | | |
| EX-W11-STD-LEGACY | exFAT | Windows 11 | Legacy BIOS | Standard | Physical | | |
| EX-W11-STD-UEFI | exFAT | Windows 11 | UEFI (SB Off) | Standard | Physical | | |
| EX-W11-STD-UEFI-SB | exFAT | Windows 11 | UEFI (SB On) | Standard | Physical | | |
| NTFS-W11-STD-LEGACY | NTFS | Windows 11 | Legacy BIOS | Standard | Physical | | |
| NTFS-W11-STD-UEFI | NTFS | Windows 11 | UEFI (SB Off) | Standard | Physical | | |
| NTFS-W11-STD-UEFI-SB | NTFS | Windows 11 | UEFI (SB On) | Standard | Physical | | |
| EX-W10-WTG-A | exFAT | Windows 10 | UEFI | Windows-To-Go | Physical A | | |
| EX-W10-WTG-B | exFAT | Windows 10 | UEFI | Windows-To-Go | Physical B | | |
| NTFS-W10-WTG-A | NTFS | Windows 10 | UEFI | Windows-To-Go | Physical A | | |
| NTFS-W10-WTG-B | NTFS | Windows 10 | UEFI | Windows-To-Go | Physical B | | |
| EX-W11-WTG-A | exFAT | Windows 11 | UEFI | Windows-To-Go | Physical A | | |
| EX-W11-WTG-B | exFAT | Windows 11 | UEFI | Windows-To-Go | Physical B | | |
| NTFS-W11-WTG-A | NTFS | Windows 11 | UEFI | Windows-To-Go | Physical A | | |
| NTFS-W11-WTG-B | NTFS | Windows 11 | UEFI | Windows-To-Go | Physical B | | |
| VM-VB-EX-W10 | exFAT | Windows 10 | UEFI | Standard | VirtualBox | | |
| VM-VB-NTFS-W10 | NTFS | Windows 10 | UEFI | Standard | VirtualBox | | |
| VM-VB-EX-W11 | exFAT | Windows 11 | UEFI | Standard | VirtualBox | | |
| VM-VB-NTFS-W11 | NTFS | Windows 11 | UEFI | Standard | VirtualBox | | |
| VM-VMW-EX-W10 | exFAT | Windows 10 | UEFI | Standard | VMware | | |
| VM-VMW-NTFS-W10 | NTFS | Windows 10 | UEFI | Standard | VMware | | |
| VM-VMW-EX-W11 | exFAT | Windows 11 | UEFI | Standard | VMware | | |
| VM-VMW-NTFS-W11 | NTFS | Windows 11 | UEFI | Standard | VMware | | |
| EX-LARGE-FILE | exFAT | N/A | N/A | N/A | N/A | | |
| NTFS-LARGE-FILE | NTFS | N/A | N/A | N/A | N/A | | |

## Appendix B: Troubleshooting Common Issues

### Boot Issues
- **USB not detected in boot menu**: Ensure USB is properly connected and try a different USB port
- **UEFI boot fails**: Check if Secure Boot is disabled, verify UEFI:NTFS bootloader was installed correctly
- **Legacy boot fails**: Verify boot flag is set on the partition, try using the `--workaround-bios-boot-flag` option

### Windows-To-Go Issues
- **Blue screen during boot**: This may indicate hardware compatibility issues, try booting in Safe Mode
- **Driver issues**: Windows may need time to detect and install drivers for new hardware
- **Performance issues**: Use a high-quality USB 3.0+ drive, consider using exFAT for better flash drive performance

### Filesystem Issues
- **Corruption after large file copy**: Verify USB drive quality, try a different drive
- **exFAT not recognized**: Some older systems may not have exFAT drivers, consider using NTFS instead
- **NTFS permission issues**: These are normal and can be ignored during testing

## Appendix C: Reporting Test Results

After completing the tests, compile the results into a comprehensive report including:

1. **Executive Summary**:
   - Overall pass/fail status
   - Major findings
   - Recommendations

2. **Detailed Test Results**:
   - Completed test matrix
   - Detailed observations for each test
   - Screenshots and logs

3. **Issues and Recommendations**:
   - List of all issues encountered
   - Recommended fixes or improvements
   - Prioritization of issues

Submit the report to the development team for review and action.
