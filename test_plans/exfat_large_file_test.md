# Test Plan: exFAT Large File Handling

**(C)2025 Robin L. M. Cheung, MBA**

## Objective
Verify that WowUSB-DS9 correctly creates bootable USB drives with exFAT filesystem and supports large ISO files.

## Test Environment Requirements

* A USB drive (at least 8GB recommended)
* A Windows ISO file larger than 4GB (e.g., a recent Windows 10 or 11 ISO)
* A Linux machine with WowUSB-DS9 installed

## Test Steps

### 1. Prepare the USB Drive
- [ ] Insert the USB drive into the Linux machine
- [ ] Ensure that the USB drive is not mounted
  ```bash
  # Replace sdX1 with your device partition
  umount /dev/sdX1
  ```

### 2. Run WowUSB-DS9
- [ ] Launch WowUSB-DS9 (GUI or CLI)
  ```bash
  # For GUI
  ./WoeUSB/woeusbgui
  # For CLI
  ./WoeUSB/woeusb --device /path/to/windows.iso /dev/sdX --target-filesystem EXFAT
  ```

### 3. Select Source and Target
- [ ] Select Windows ISO file as source
- [ ] Select USB drive as target
- [ ] Choose "exFAT (Fast, supports >4GB files)" as target filesystem

### 4. Installation Process
- [ ] Start the installation
- [ ] Monitor progress indicators
- [ ] Note any warnings or errors

### 5. Verify Installation
- [ ] Check for completion message
- [ ] Note any errors in the output
- [ ] Verify filesystem was created as exFAT
  ```bash
  lsblk -f /dev/sdX1  # Should show exfat filesystem
  ```

### 6. Test Bootability
- [ ] Insert USB drive into test computer
- [ ] Boot from USB
- [ ] Verify Windows installer starts correctly

### 7. Hardware Compatibility (Optional)
- [ ] Test on additional computers if available
- [ ] Test with different USB controllers if possible

## Expected Results

* Installation completes without errors
* USB drive is bootable
* Windows installer launches successfully

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
* Test Computer:
  - Make/Model: _____________________
  - BIOS/UEFI Mode: _____________________
  - Boot type (Legacy/UEFI): _____________________

### Additional Observations
_____________________
_____________________
_____________________

## Notes
* This test focuses on large file handling and bootability with exFAT filesystem
* UEFI:NTFS bootloader is used to enable bootability
* Any file larger than 4GB should be handled correctly