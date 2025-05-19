# WowUSB-DS9 Troubleshooting Guide

This guide provides solutions to common issues encountered when using WowUSB-DS9.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [USB Drive Issues](#usb-drive-issues)
3. [Filesystem Issues](#filesystem-issues)
4. [Bootloader Issues](#bootloader-issues)
5. [Windows-To-Go Issues](#windows-to-go-issues)
6. [Error Messages](#error-messages)
7. [Performance Issues](#performance-issues)

## Installation Issues

### Missing Dependencies

**Problem**: Error about missing dependencies when installing or running WowUSB-DS9.

**Solution**:
```bash
# For Debian/Ubuntu
sudo apt install git p7zip-full python3-pip python3-wxgtk4.0 grub2-common grub-pc-bin parted dosfstools ntfs-3g exfat-utils f2fs-tools btrfs-progs

# For Fedora
sudo dnf install git p7zip p7zip-plugins python3-pip python3-wxpython4 grub2-common grub2-tools parted dosfstools ntfs-3g exfatprogs f2fs-tools btrfs-progs

# For Arch Linux
sudo pacman -Suy p7zip python-pip python-wxpython grub parted dosfstools ntfs-3g exfatprogs f2fs-tools btrfs-progs
```

### Permission Issues

**Problem**: "Permission denied" errors when running WowUSB-DS9.

**Solution**:
- Run the command with sudo: `sudo wowusb` or `sudo woeusbgui`
- Check if polkit is installed and working correctly
- Verify that the policy file is installed: `/usr/share/polkit-1/actions/com.rebots.wowusb.ds9.policy`

### GUI Not Starting

**Problem**: The graphical interface fails to start.

**Solution**:
- Verify wxPython is installed: `pip3 show wxPython`
- Try running from terminal to see error messages: `woeusbgui`
- Check if the desktop file is installed: `/usr/share/applications/WowUSB-DS9.desktop`
- Try reinstalling: `sudo pip3 install --force-reinstall WowUSB-DS9`

## USB Drive Issues

### Cannot Detect USB Drive

**Problem**: WowUSB-DS9 cannot detect the USB drive.

**Solution**:
- Ensure the USB drive is properly connected
- List all drives to verify it's recognized by the system: `lsblk`
- Try a different USB port
- Check if the drive is mounted and unmount it: `sudo umount /dev/sdX*`

### Write Protection

**Problem**: "Read-only file system" or write protection errors.

**Solution**:
- Check if the drive has a physical write-protect switch
- Try to force disable write protection:
  ```bash
  sudo hdparm -r0 /dev/sdX
  ```
- Try reformatting the drive with GParted before using WowUSB-DS9

### Insufficient Space

**Problem**: "Not enough space" errors during installation.

**Solution**:
- Use a larger USB drive (8GB minimum, 16GB+ recommended)
- Try a different filesystem (NTFS or exFAT) which may have better compression
- Check if the drive has hidden partitions using: `sudo fdisk -l /dev/sdX`
- Completely wipe the drive before using WowUSB-DS9:
  ```bash
  sudo wipefs -a /dev/sdX
  ```

## Filesystem Issues

### FAT32 File Size Limitation

**Problem**: "File too large" errors when using FAT32.

**Solution**:
- Use a different filesystem (NTFS, exFAT, F2FS, or BTRFS)
- Use the automatic filesystem selection: `--target-filesystem AUTO`
- Split large files (not recommended)

### exFAT Not Available

**Problem**: exFAT filesystem option is not available.

**Solution**:
- Install exFAT tools:
  ```bash
  # Debian/Ubuntu
  sudo apt install exfat-utils exfat-fuse
  
  # Fedora
  sudo dnf install exfatprogs
  
  # Arch Linux
  sudo pacman -S exfatprogs
  ```
- Verify the tools are installed: `which mkfs.exfat`

### Filesystem Corruption

**Problem**: The created USB drive shows filesystem errors or corruption.

**Solution**:
- Check the USB drive for bad sectors:
  ```bash
  sudo badblocks -v /dev/sdX
  ```
- Try a different USB drive
- Use a more reliable filesystem like NTFS or exFAT
- Ensure proper ejection after use

## Bootloader Issues

### USB Drive Not Bootable

**Problem**: The computer doesn't boot from the USB drive.

**Solution**:
- Check if your BIOS/UEFI is configured to boot from USB
- Try both UEFI and Legacy boot modes in BIOS settings
- Ensure Secure Boot is disabled in UEFI settings
- Try recreating the USB with a different filesystem
- Verify the bootloader was installed correctly:
  ```bash
  sudo dd if=/dev/sdX bs=440 count=1 | hexdump -C
  ```
  (The output should start with a boot code, not all zeros)

### UEFI Boot Fails

**Problem**: The USB drive doesn't boot in UEFI mode.

**Solution**:
- Ensure the drive was created with GPT partition table
- Check if the EFI partition is properly formatted (FAT32)
- For NTFS/exFAT, verify the UEFI:NTFS bootloader was installed
- Try disabling Secure Boot in UEFI settings
- Use the `--workaround-bios-boot-flag` option

### Legacy Boot Fails

**Problem**: The USB drive doesn't boot in Legacy/BIOS mode.

**Solution**:
- Ensure the drive has an MBR partition table
- Check if the boot flag is set on the partition
- Try the `--workaround-bios-boot-flag` option
- Recreate the USB with FAT32 filesystem for maximum compatibility

## Windows-To-Go Issues

### Windows-To-Go Not Booting

**Problem**: Windows-To-Go installation doesn't boot.

**Solution**:
- Ensure you used a Windows 10 or 11 ISO (Windows-To-Go doesn't work with older versions)
- Use a high-quality USB 3.0+ drive (32GB+ recommended)
- Check if the correct partition layout was created (ESP, MSR, and Windows partitions)
- Try disabling Secure Boot in UEFI settings
- For Windows 11, ensure the TPM bypass was applied

### Hardware Detection Issues

**Problem**: Windows-To-Go doesn't recognize hardware or has driver issues.

**Solution**:
- Boot into Safe Mode first time on new hardware
- Let Windows detect and install drivers automatically
- For graphics issues, use basic display drivers initially
- Consider pre-installing common drivers on the Windows-To-Go drive

### Performance Issues with Windows-To-Go

**Problem**: Windows-To-Go runs very slowly.

**Solution**:
- Use a USB 3.0+ port and drive
- Use a high-performance USB drive with good random I/O
- Disable Windows features that are not needed:
  - Search indexing
  - Windows Defender real-time protection
  - Visual effects
- Consider using exFAT or F2FS filesystem for better flash drive performance

## Error Messages

### "Error: Unable to mount source filesystem"

**Problem**: WowUSB-DS9 cannot mount the source ISO.

**Solution**:
- Verify the ISO file is not corrupted: `md5sum your-windows.iso`
- Check if the ISO can be mounted manually:
  ```bash
  sudo mkdir -p /mnt/iso
  sudo mount -o loop your-windows.iso /mnt/iso
  ```
- Try a different ISO file

### "Error: Unable to create target filesystem"

**Problem**: WowUSB-DS9 cannot create the filesystem on the USB drive.

**Solution**:
- Check if the drive is write-protected
- Verify you have the necessary filesystem tools installed
- Try manually formatting the drive first:
  ```bash
  sudo mkfs.ntfs -f -L "Windows USB" /dev/sdX1
  ```
- Check for bad sectors on the drive

### "Error: Failed to install bootloader"

**Problem**: WowUSB-DS9 cannot install the bootloader.

**Solution**:
- Check if GRUB is installed: `which grub-install`
- Try manually installing the bootloader:
  ```bash
  sudo grub-install --target=i386-pc --boot-directory=/path/to/mounted/usb /dev/sdX
  ```
- For UEFI boot, check if the EFI partition is properly formatted

## Performance Issues

### Slow Copy Speed

**Problem**: Files copy very slowly to the USB drive.

**Solution**:
- Use a USB 3.0+ port and drive
- Try a different filesystem (exFAT or F2FS often perform better on flash drives)
- Check if the drive is fragmented or has bad sectors
- Close other applications that might be using disk I/O
- Try using the `--workaround-skip-grub` option to speed up the process

### High CPU Usage

**Problem**: WowUSB-DS9 uses excessive CPU resources.

**Solution**:
- This is normal during file copying and compression
- Try using a different filesystem that requires less processing
- Close other CPU-intensive applications
- For very large ISOs, consider running the process overnight

### Application Freezes

**Problem**: WowUSB-DS9 freezes during operation.

**Solution**:
- Run with verbose output to see where it's hanging: `wowusb --verbose`
- Check system logs: `journalctl -f`
- Try running from terminal to see all output
- Ensure your system has enough RAM and swap space
- For GUI freezes, try the command-line version instead

## Still Having Issues?

If you're still experiencing problems after trying these solutions:

1. Run WowUSB-DS9 with verbose output: `wowusb --verbose` or `woeusbgui --verbose`
2. Check system logs: `journalctl -f`
3. Create an issue on the GitHub repository with:
   - Exact command used
   - Complete error output
   - Your Linux distribution and version
   - USB drive model and size
   - Windows ISO version
4. Try the latest development version from GitHub
