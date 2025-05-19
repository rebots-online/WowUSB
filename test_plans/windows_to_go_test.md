# Test Plan: Windows-To-Go Functionality

**(C)2025 Robin L. M. Cheung, MBA**

## Objective
Verify that WowUSB-DS9 correctly creates Windows-To-Go installations that can boot and run from USB drives across different hardware configurations, with special focus on Windows 11 TPM bypass functionality.

## Test Environment Requirements

### Hardware
* USB 3.0+ drive (32GB or larger recommended)
* At least 2 different test computers:
  * Computer A: Modern system with TPM 2.0 and UEFI firmware
  * Computer B: Older system without TPM or with TPM 1.2 only

### Software
* Windows 10 ISO (64-bit, latest build)
* Windows 11 ISO (64-bit, latest build)
* Linux machine with WowUSB-DS9 installed

## Test Matrix

| Test ID | Windows Version | Filesystem | Computer | TPM Present | Expected Result |
|---------|-----------------|------------|----------|-------------|-----------------|
| W10-EX-A | Windows 10 | exFAT | Computer A | Yes | Pass |
| W10-EX-B | Windows 10 | exFAT | Computer B | No | Pass |
| W10-NTFS-A | Windows 10 | NTFS | Computer A | Yes | Pass |
| W10-NTFS-B | Windows 10 | NTFS | Computer B | No | Pass |
| W11-EX-A | Windows 11 | exFAT | Computer A | Yes | Pass |
| W11-EX-B | Windows 11 | exFAT | Computer B | No | Pass |
| W11-NTFS-A | Windows 11 | NTFS | Computer A | Yes | Pass |
| W11-NTFS-B | Windows 11 | NTFS | Computer B | No | Pass |

## Detailed Test Procedures

### 1. Windows 10 To-Go with exFAT

#### 1.1 Preparation
- [ ] Insert the USB drive into the Linux machine
- [ ] Ensure that the USB drive is not mounted
  ```bash
  # Replace sdX with your device
  sudo umount /dev/sdX*
  ```

#### 1.2 Create Windows 10 To-Go USB Drive with exFAT
- [ ] Run WowUSB-DS9 with Windows-To-Go option and exFAT filesystem
  ```bash
  sudo wowusb --device /path/to/windows10.iso /dev/sdX --target-filesystem EXFAT --wintogo
  ```
- [ ] Monitor progress indicators (this will take longer than standard installation)
- [ ] Note any warnings or errors
- [ ] Record the total time taken for the operation

#### 1.3 Verify Partition Layout
- [ ] Check for completion message
- [ ] Verify partition layout
  ```bash
  lsblk /dev/sdX  # Should show 3 partitions: ESP, MSR, and Windows
  ```
- [ ] Verify ESP partition is FAT32
  ```bash
  lsblk -f /dev/sdX1  # Should show vfat filesystem
  ```
- [ ] Verify Windows partition is exFAT
  ```bash
  lsblk -f /dev/sdX3  # Should show exfat filesystem
  ```

#### 1.4 First Boot Test on Computer A
- [ ] Insert USB drive into Computer A
- [ ] Boot from USB drive (UEFI mode)
- [ ] Verify Windows boots to setup screen
- [ ] Complete initial Windows setup
  - [ ] Create a user account named "WTGTest"
  - [ ] Set a simple password for testing
  - [ ] Skip Microsoft account setup if possible
  - [ ] Complete all setup steps
- [ ] Verify Windows desktop appears
- [ ] Create a test file on the desktop named "TestFileA.txt"
- [ ] Check Device Manager for driver issues
  - [ ] Open Device Manager (right-click Start > Device Manager)
  - [ ] Look for devices with warning icons
  - [ ] Note any driver issues
- [ ] Check Windows version and build number
  - [ ] Open System Information (Win+R > msinfo32)
  - [ ] Note OS Name, Version, and Build Number
- [ ] Shut down Windows

#### 1.5 Second Boot Test on Computer B
- [ ] Insert USB drive into Computer B
- [ ] Boot from USB drive
- [ ] Verify Windows boots correctly
- [ ] Verify previously created user account "WTGTest" is available
- [ ] Log in using the password set during first boot
- [ ] Verify the test file "TestFileA.txt" is present on the desktop
- [ ] Create a new test file named "TestFileB.txt"
- [ ] Check Device Manager for driver issues
  - [ ] Note how Windows adapted to the new hardware
  - [ ] Document any driver issues
- [ ] Shut down Windows

#### 1.6 Return to Computer A
- [ ] Insert USB drive into Computer A again
- [ ] Boot from USB drive
- [ ] Verify Windows boots correctly
- [ ] Log in using the "WTGTest" account
- [ ] Verify both test files are present on the desktop
- [ ] Check Device Manager to see if Windows readapted to the original hardware
- [ ] Shut down Windows

### 2. Windows 10 To-Go with NTFS

#### 2.1 Preparation
- [ ] Insert the USB drive into the Linux machine
- [ ] Ensure that the USB drive is not mounted
  ```bash
  sudo umount /dev/sdX*
  ```

#### 2.2 Create Windows 10 To-Go USB Drive with NTFS
- [ ] Run WowUSB-DS9 with Windows-To-Go option and NTFS filesystem
  ```bash
  sudo wowusb --device /path/to/windows10.iso /dev/sdX --target-filesystem NTFS --wintogo
  ```
- [ ] Follow the same verification steps as in 1.3
- [ ] Perform the same boot tests as in 1.4, 1.5, and 1.6

### 3. Windows 11 To-Go with exFAT

#### 3.1 Preparation
- [ ] Insert the USB drive into the Linux machine
- [ ] Ensure that the USB drive is not mounted
  ```bash
  sudo umount /dev/sdX*
  ```

#### 3.2 Create Windows 11 To-Go USB Drive with exFAT
- [ ] Run WowUSB-DS9 with Windows-To-Go option and exFAT filesystem
  ```bash
  sudo wowusb --device /path/to/windows11.iso /dev/sdX --target-filesystem EXFAT --wintogo
  ```
- [ ] Follow the same verification steps as in 1.3

#### 3.3 First Boot Test on Computer A (with TPM)
- [ ] Insert USB drive into Computer A
- [ ] Boot from USB drive (UEFI mode)
- [ ] Verify Windows 11 boots to setup screen without TPM errors
- [ ] Complete initial Windows setup
- [ ] Verify Windows desktop appears
- [ ] Create a test file on the desktop named "Win11TestA.txt"
- [ ] Check Device Manager for driver issues
- [ ] Check Windows version and build number
- [ ] Verify TPM status
  - [ ] Open Run dialog (Win+R)
  - [ ] Type "tpm.msc" and press Enter
  - [ ] Note if TPM is recognized or bypassed
- [ ] Shut down Windows

#### 3.4 Boot Test on Computer B (without TPM or with TPM 1.2)
- [ ] Insert USB drive into Computer B
- [ ] Boot from USB drive
- [ ] Verify Windows 11 boots correctly despite TPM requirements
- [ ] Verify previously created user account is available
- [ ] Log in and verify the test file is present
- [ ] Create a new test file named "Win11TestB.txt"
- [ ] Check Device Manager for driver issues
- [ ] Verify TPM status (should show as bypassed or not required)
- [ ] Shut down Windows

### 4. Windows 11 To-Go with NTFS

#### 4.1 Preparation
- [ ] Insert the USB drive into the Linux machine
- [ ] Ensure that the USB drive is not mounted
  ```bash
  sudo umount /dev/sdX*
  ```

#### 4.2 Create Windows 11 To-Go USB Drive with NTFS
- [ ] Run WowUSB-DS9 with Windows-To-Go option and NTFS filesystem
  ```bash
  sudo wowusb --device /path/to/windows11.iso /dev/sdX --target-filesystem NTFS --wintogo
  ```
- [ ] Follow the same verification steps as in 1.3
- [ ] Perform the same boot tests as in 3.3 and 3.4

## Performance Testing

### 1. Boot Time Measurement
- [ ] For each Windows-To-Go configuration, measure and record:
  - [ ] Time from power on to boot menu
  - [ ] Time from selecting USB to Windows logo
  - [ ] Time from Windows logo to login screen
  - [ ] Time from login to usable desktop

### 2. Disk Performance Testing
- [ ] For each Windows-To-Go configuration, run basic disk performance tests:
  - [ ] Copy a large file (1GB) to the desktop and measure time
  - [ ] Open and save a large document
  - [ ] Install a small application

### 3. Hardware Adaptation Testing
- [ ] For each Windows-To-Go configuration, document:
  - [ ] Time taken for Windows to detect new hardware
  - [ ] Success rate of driver installation
  - [ ] Any devices that fail to work properly

## Test Results

### Windows 10 To-Go with exFAT
* Creation time: _____________________
* First boot time (Computer A): _____________________
* Second boot time (Computer B): _____________________
* Driver issues: _____________________
* Performance notes: _____________________

### Windows 10 To-Go with NTFS
* Creation time: _____________________
* First boot time (Computer A): _____________________
* Second boot time (Computer B): _____________________
* Driver issues: _____________________
* Performance notes: _____________________

### Windows 11 To-Go with exFAT
* Creation time: _____________________
* First boot time (Computer A): _____________________
* Second boot time (Computer B): _____________________
* TPM bypass successful: _____________________
* Driver issues: _____________________
* Performance notes: _____________________

### Windows 11 To-Go with NTFS
* Creation time: _____________________
* First boot time (Computer A): _____________________
* Second boot time (Computer B): _____________________
* TPM bypass successful: _____________________
* Driver issues: _____________________
* Performance notes: _____________________

### Hardware Details
* USB Drive: 
  - Make/Model: _____________________
  - Capacity: _____________________
  - Interface: _____________________
* Computer A:
  - Make/Model: _____________________
  - CPU: _____________________
  - RAM: _____________________
  - TPM Version: _____________________
  - BIOS/UEFI Version: _____________________
* Computer B:
  - Make/Model: _____________________
  - CPU: _____________________
  - RAM: _____________________
  - TPM Version: _____________________
  - BIOS/UEFI Version: _____________________

### Additional Observations
_____________________
_____________________
_____________________

## Troubleshooting Common Issues

### Windows 10 To-Go Issues
- **Blue screen during boot**: This may indicate hardware compatibility issues, try booting in Safe Mode
- **Driver issues**: Windows may need time to detect and install drivers for new hardware
- **Performance issues**: Use a high-quality USB 3.0+ drive, consider using exFAT for better flash drive performance

### Windows 11 To-Go Issues
- **TPM errors despite bypass**: Verify that the bypass registry entries were created correctly
- **Secure Boot errors**: Some systems may require Secure Boot to be disabled in UEFI settings
- **Activation issues**: Windows 11 To-Go may show as not activated, which is normal for portable installations

### Filesystem-Specific Issues
- **exFAT corruption**: exFAT may be more prone to corruption if not properly ejected, always shut down Windows properly
- **NTFS permission issues**: These are normal and can be ignored during testing

## Conclusion
This test plan provides a comprehensive approach to verify WowUSB-DS9's Windows-To-Go functionality across different hardware configurations. By following these procedures, testers can ensure that the implementation meets the requirements for portable Windows installations, including the critical Windows 11 TPM bypass feature.
