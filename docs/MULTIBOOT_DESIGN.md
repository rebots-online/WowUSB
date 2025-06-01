# WowUSB-DS9 Multi-Boot Foundation Design

**(C)2025 Robin L. M. Cheung, MBA**

## Overview

This document outlines the technical design for implementing a GRUB2-based multi-boot foundation in WowUSB-DS9. The multi-boot capability will allow users to create USB drives containing multiple operating systems (Windows and Linux) that can be selected at boot time.

## Goals and Requirements

### Primary Goals

1. Enable creation of multi-boot USB drives with multiple Windows and Linux installations
2. Provide a user-friendly boot menu for selecting the operating system to boot
3. Support both UEFI and Legacy BIOS boot modes
4. Maintain compatibility with existing WowUSB-DS9 features (filesystem support, Windows-To-Go)

### Technical Requirements

1. GRUB2-based boot manager for maximum flexibility and compatibility
2. Support for chainloading Windows installations (standard and Windows-To-Go)
3. Support for direct booting Linux distributions
4. Configurable boot menu with customizable timeout and default selection
5. Partition layout that accommodates multiple operating systems
6. Secure Boot compatibility where possible

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Multi-Boot Foundation                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐│
│  │  Partition      │   │  Boot Manager   │   │  OS Integration ││
│  │  Management     │   │  Configuration  │   │  Modules        ││
│  └─────────────────┘   └─────────────────┘   └─────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Partition Management

The partition management component will handle:
- Creating appropriate partition layouts for multi-boot scenarios
- Allocating space for each operating system
- Managing shared data partitions
- Ensuring compatibility between different operating systems

### Boot Manager Configuration

The boot manager component will handle:
- Installing GRUB2 bootloader
- Generating GRUB2 configuration files
- Detecting installed operating systems
- Creating boot menu entries
- Managing boot parameters

### OS Integration Modules

The OS integration modules will handle:
- Windows-specific boot requirements
- Linux-specific boot requirements
- Chainloading configurations
- OS-specific customizations

## Partition Layout Design

### Multi-Boot Partition Layout (GPT)

```
┌─────────────────────────────────────────────────────────────────┐
│ Partition 1: EFI System Partition - FAT32 (200MB)               │
├─────────────────────────────────────────────────────────────────┤
│ Partition 2: GRUB2 Boot Partition - FAT32 (200MB)               │
├─────────────────────────────────────────────────────────────────┤
│ Partition 3: Shared Data - exFAT (User-defined)                 │
├─────────────────────────────────────────────────────────────────┤
│ Partition 4: Windows 1 - NTFS/exFAT (User-defined)              │
├─────────────────────────────────────────────────────────────────┤
│ Partition 5: Linux 1 - ext4/F2FS/BTRFS (User-defined)           │
├─────────────────────────────────────────────────────────────────┤
│ Partition 6+: Additional OSes - Various FS (User-defined)       │
└─────────────────────────────────────────────────────────────────┘
```

### Multi-Boot Partition Layout (MBR for Legacy Systems)

```
┌─────────────────────────────────────────────────────────────────┐
│ Partition 1: GRUB2 Boot Partition - FAT32 (200MB)               │
├─────────────────────────────────────────────────────────────────┤
│ Partition 2: Shared Data - FAT32/exFAT (User-defined)           │
├─────────────────────────────────────────────────────────────────┤
│ Partition 3: Windows - NTFS/exFAT (User-defined)                │
├─────────────────────────────────────────────────────────────────┤
│ Partition 4: Extended Partition                                 │
│  ├─────────────────────────────────────────────────────────────┤
│  │ Logical Partition 5: Linux 1 - ext4/F2FS/BTRFS              │
│  ├─────────────────────────────────────────────────────────────┤
│  │ Logical Partition 6+: Additional OSes - Various FS          │
│  └─────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
```

### Partition Type Codes

| Partition Type | GPT GUID | MBR Code | Description |
|----------------|----------|----------|-------------|
| EFI System | C12A7328-F81F-11D2-BA4B-00A0C93EC93B | 0xEF | EFI bootloader partition |
| Microsoft Reserved | E3C9E316-0B5C-4DB8-817D-F92DF00215AE | 0x0C | Required for Windows |
| Windows Basic Data | EBD0A0A2-B9E5-4433-87C0-68B6B72699C7 | 0x07 | Windows NTFS partition |
| Linux Filesystem | 0FC63DAF-8483-4772-8E79-3D69D8477DE4 | 0x83 | Linux native filesystem |
| Linux Swap | 0657FD6D-A4AB-43C4-84E5-0933C84B4F4F | 0x82 | Linux swap partition |
| exFAT | 516E7CB4-6ECF-11D6-8FF8-00022D09712B | 0x07 | exFAT partition |

## Boot Manager Implementation

### GRUB2 Installation

GRUB2 will be installed to both the MBR/GPT and the boot partition to ensure compatibility with both UEFI and Legacy BIOS systems:

```python
def install_grub2_bootloader(target_device, boot_partition, efi_partition=None):
    """
    Install GRUB2 bootloader for multi-boot support
    
    Args:
        target_device (str): Target device path (e.g., /dev/sdX)
        boot_partition (str): Boot partition path (e.g., /dev/sdX2)
        efi_partition (str, optional): EFI partition path for UEFI systems
        
    Returns:
        int: 0 on success, non-zero on failure
    """
    # Mount boot partition
    boot_mount = tempfile.mkdtemp(prefix="WowUSB_boot.")
    subprocess.run(["mount", boot_partition, boot_mount], check=True)
    
    try:
        # Install GRUB2 for Legacy BIOS
        subprocess.run([
            "grub-install",
            "--target=i386-pc",
            "--boot-directory=" + os.path.join(boot_mount, "boot"),
            "--recheck",
            target_device
        ], check=True)
        
        # Install GRUB2 for UEFI if EFI partition is provided
        if efi_partition:
            # Mount EFI partition
            efi_mount = tempfile.mkdtemp(prefix="WowUSB_efi.")
            subprocess.run(["mount", efi_partition, efi_mount], check=True)
            
            try:
                subprocess.run([
                    "grub-install",
                    "--target=x86_64-efi",
                    "--boot-directory=" + os.path.join(boot_mount, "boot"),
                    "--efi-directory=" + efi_mount,
                    "--removable",
                    "--recheck"
                ], check=True)
            finally:
                # Unmount EFI partition
                subprocess.run(["umount", efi_mount])
                os.rmdir(efi_mount)
        
        return 0
    finally:
        # Unmount boot partition
        subprocess.run(["umount", boot_mount])
        os.rmdir(boot_mount)
```

### GRUB2 Configuration

The GRUB2 configuration will be generated dynamically based on the installed operating systems:

```python
def generate_grub2_config(boot_partition, os_entries):
    """
    Generate GRUB2 configuration file
    
    Args:
        boot_partition (str): Boot partition path (e.g., /dev/sdX2)
        os_entries (list): List of OS entry dictionaries
        
    Returns:
        int: 0 on success, non-zero on failure
    """
    # Mount boot partition
    boot_mount = tempfile.mkdtemp(prefix="WowUSB_boot.")
    subprocess.run(["mount", boot_partition, boot_mount], check=True)
    
    try:
        # Create GRUB2 configuration directory
        grub_dir = os.path.join(boot_mount, "boot", "grub")
        os.makedirs(grub_dir, exist_ok=True)
        
        # Generate GRUB2 configuration file
        with open(os.path.join(grub_dir, "grub.cfg"), "w") as f:
            # Write header
            f.write("# GRUB2 configuration file generated by WowUSB-DS9\n")
            f.write("# DO NOT EDIT THIS FILE\n\n")
            
            # Set timeout and default entry
            f.write("set timeout=10\n")
            f.write("set default=0\n\n")
            
            # Load modules
            f.write("insmod part_gpt\n")
            f.write("insmod part_msdos\n")
            f.write("insmod fat\n")
            f.write("insmod ntfs\n")
            f.write("insmod ext2\n")
            f.write("insmod f2fs\n")
            f.write("insmod btrfs\n")
            f.write("insmod chain\n")
            f.write("insmod search_fs_uuid\n")
            f.write("insmod search_label\n\n")
            
            # Write OS entries
            for i, entry in enumerate(os_entries):
                f.write(f"# {entry['name']}\n")
                
                if entry['type'] == 'windows':
                    # Windows entry
                    f.write(f"menuentry \"{entry['name']}\" {{\n")
                    f.write("    insmod part_gpt\n")
                    f.write("    insmod search_fs_uuid\n")
                    f.write("    insmod chain\n")
                    f.write(f"    search --fs-uuid --set=root {entry['uuid']}\n")
                    
                    if entry.get('wintogo', False):
                        # Windows-To-Go entry
                        f.write("    chainloader /EFI/Microsoft/Boot/bootmgfw.efi\n")
                    else:
                        # Standard Windows entry
                        f.write("    chainloader /bootmgr\n")
                    
                    f.write("}\n\n")
                
                elif entry['type'] == 'linux':
                    # Linux entry
                    f.write(f"menuentry \"{entry['name']}\" {{\n")
                    f.write("    insmod part_gpt\n")
                    f.write("    insmod search_fs_uuid\n")
                    
                    # Load appropriate filesystem module
                    if entry['filesystem'] == 'ext4':
                        f.write("    insmod ext2\n")
                    elif entry['filesystem'] == 'f2fs':
                        f.write("    insmod f2fs\n")
                    elif entry['filesystem'] == 'btrfs':
                        f.write("    insmod btrfs\n")
                    
                    f.write(f"    search --fs-uuid --set=root {entry['uuid']}\n")
                    
                    # Set kernel and initrd paths
                    f.write(f"    linux {entry['kernel']} {entry['kernel_params']}\n")
                    f.write(f"    initrd {entry['initrd']}\n")
                    f.write("}\n\n")
        
        return 0
    finally:
        # Unmount boot partition
        subprocess.run(["umount", boot_mount])
        os.rmdir(boot_mount)
```

## OS Integration

### Windows Integration

Windows installations will be chainloaded using GRUB2. This approach works for both standard Windows installations and Windows-To-Go:

```
menuentry "Windows 10" {
    insmod part_gpt
    insmod ntfs
    insmod search_fs_uuid
    insmod chain
    search --fs-uuid --set=root XXXX-XXXX
    chainloader /bootmgr
}

menuentry "Windows 11 To-Go" {
    insmod part_gpt
    insmod ntfs
    insmod search_fs_uuid
    insmod chain
    search --fs-uuid --set=root YYYY-YYYY
    chainloader /EFI/Microsoft/Boot/bootmgfw.efi
}
```

For Windows installations, the following considerations apply:
- Standard Windows installations will chainload `/bootmgr` for Legacy BIOS or `/EFI/Microsoft/Boot/bootmgfw.efi` for UEFI
- Windows-To-Go installations will use the same approach as standard installations
- Windows partitions must be accessible by GRUB2 (typically NTFS or exFAT)
- Windows installations must be properly prepared for multi-boot scenarios

### Linux Integration

Linux distributions will be booted directly by GRUB2 by loading the kernel and initrd:

```
menuentry "Ubuntu 22.04" {
    insmod part_gpt
    insmod ext2
    insmod search_fs_uuid
    search --fs-uuid --set=root ZZZZ-ZZZZ
    linux /boot/vmlinuz-5.15.0-25-generic root=UUID=ZZZZ-ZZZZ ro quiet splash
    initrd /boot/initrd.img-5.15.0-25-generic
}

menuentry "Fedora 38" {
    insmod part_gpt
    insmod ext2
    insmod search_fs_uuid
    search --fs-uuid --set=root AAAA-AAAA
    linux /boot/vmlinuz-6.2.9-300.fc38.x86_64 root=UUID=AAAA-AAAA ro quiet
    initrd /boot/initramfs-6.2.9-300.fc38.x86_64.img
}
```

For Linux installations, the following considerations apply:
- Linux kernels and initrds will be loaded directly by GRUB2
- Linux partitions must be accessible by GRUB2 (ext4, F2FS, BTRFS, etc.)
- Linux installations must be properly prepared for multi-boot scenarios
- Kernel parameters must be set correctly for each distribution

## Implementation Plan

### Phase 1: Partition Management

1. Implement partition layout creation for multi-boot scenarios
2. Support both GPT and MBR partition tables
3. Allow user-defined partition sizes
4. Ensure compatibility with existing WowUSB-DS9 features

### Phase 2: Boot Manager Implementation

1. Implement GRUB2 installation for both UEFI and Legacy BIOS
2. Develop GRUB2 configuration generation
3. Create boot menu entry templates for Windows and Linux
4. Implement OS detection and UUID retrieval

### Phase 3: OS Integration

1. Implement Windows chainloading support
2. Develop Linux direct boot support
3. Create OS-specific customization options
4. Test with various Windows versions and Linux distributions

### Phase 4: User Interface Integration

1. Add multi-boot options to WowUSB-DS9 CLI and GUI
2. Implement OS selection and configuration UI
3. Develop partition size adjustment UI
4. Create boot menu customization options

## Technical Challenges and Solutions

### Challenge 1: Secure Boot Compatibility

**Challenge**: Secure Boot requires signed bootloaders and kernels, which can complicate multi-boot setups.

**Solution**:
- Use shim bootloader for UEFI Secure Boot
- Sign GRUB2 with a custom key if necessary
- Provide option to disable Secure Boot requirement
- Document Secure Boot limitations and workarounds

### Challenge 2: Windows Boot Manager Conflicts

**Challenge**: Windows Boot Manager can overwrite or conflict with GRUB2.

**Solution**:
- Install GRUB2 after Windows installations
- Use separate EFI partition for GRUB2 if necessary
- Modify Windows BCD store to prevent automatic repairs
- Document Windows-specific considerations

### Challenge 3: Linux Kernel Updates

**Challenge**: Linux kernel updates can break GRUB2 configurations.

**Solution**:
- Use UUID-based identification instead of partition numbers
- Implement kernel version detection
- Provide mechanism for updating GRUB2 configuration
- Document Linux-specific considerations

### Challenge 4: Filesystem Compatibility

**Challenge**: Different operating systems have different filesystem compatibility.

**Solution**:
- Use FAT32 for shared boot partitions
- Use exFAT for shared data partitions
- Use OS-specific filesystems for OS partitions
- Document filesystem compatibility matrix

## User Interface Design

### CLI Interface

```
wowusb --multiboot --device /dev/sdX
       --add-os windows --iso /path/to/windows.iso --size 10G --filesystem NTFS
       --add-os linux --iso /path/to/ubuntu.iso --size 8G --filesystem EXT4
       --shared-size 4G --filesystem EXFAT
```

### GUI Interface

The GUI will include:
- Multi-boot mode selection
- OS addition interface
- Partition size adjustment controls
- Boot menu customization options
- Filesystem selection for each partition

## Testing Strategy

### Test Matrix

| Test ID | Boot Mode | Partition Table | OS Combinations | Expected Result |
|---------|-----------|-----------------|-----------------|-----------------|
| MB-01 | UEFI | GPT | Windows 10 + Ubuntu | Pass |
| MB-02 | UEFI | GPT | Windows 11 + Fedora | Pass |
| MB-03 | UEFI | GPT | Windows 10 + Windows 11 | Pass |
| MB-04 | UEFI | GPT | Ubuntu + Fedora | Pass |
| MB-05 | Legacy | MBR | Windows 10 + Ubuntu | Pass |
| MB-06 | Legacy | MBR | Windows 10 + Windows 11 | Pass |
| MB-07 | Legacy | MBR | Ubuntu + Fedora | Pass |
| MB-08 | UEFI | GPT | Windows To-Go + Ubuntu | Pass |
| MB-09 | UEFI | GPT | Windows 10 + Ubuntu + Fedora | Pass |
| MB-10 | Legacy | MBR | Windows 10 + Ubuntu + Fedora | Pass |

### Test Procedures

1. Create multi-boot USB drive with specified configuration
2. Boot from USB drive on test system
3. Verify GRUB2 menu appears with correct entries
4. Boot each operating system and verify functionality
5. Test shared data partition accessibility
6. Verify boot menu customization options

## Future Enhancements

1. **Persistence Support**: Add persistence options for Linux distributions
2. **Theme Customization**: Allow customization of GRUB2 theme
3. **Automated Updates**: Implement mechanism for updating GRUB2 configuration
4. **Rescue Mode**: Add rescue mode for recovering from boot failures
5. **Encryption Support**: Add support for encrypted partitions
6. **Advanced Boot Options**: Add advanced boot options for each operating system

## Conclusion

The GRUB2-based multi-boot foundation will enable WowUSB-DS9 to create versatile bootable USB drives containing multiple operating systems. This capability will significantly enhance the utility of WowUSB-DS9, making it a comprehensive solution for creating bootable USB drives for various purposes.

The implementation will follow a phased approach, starting with partition management and boot manager implementation, followed by OS integration and user interface enhancements. The design prioritizes compatibility, flexibility, and user-friendliness while addressing technical challenges related to Secure Boot, Windows Boot Manager conflicts, Linux kernel updates, and filesystem compatibility.
