
# WowUSB-DS9 Technical Design Document

This document provides detailed technical specifications for the implementation of WowUSB-DS9, including extended filesystem support, multi-boot capability, and Windows-To-Go functionality.

## Architecture Overview

WowUSB-DS9 is built with a modular architecture that separates core functionality from filesystem-specific operations, allowing for easy extension and maintenance.

```
┌─────────────────────────────────────────────┐
│                  Core Module                 │
├─────────────────────────────────────────────┤
│ + main()                                    │
│ + create_target_partition_table()           │
│ + create_target_partition()                 │
│ + create_wintogo_partition_layout()         │
│ + mount_source_filesystem()                 │
│ + mount_target_filesystem()                 │
│ + copy_filesystem_files()                   │
└───────────────┬─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│           Filesystem Handlers                │
├─────────────────────────────────────────────┤
│ + get_filesystem_handler()                  │
│ + get_optimal_filesystem_for_iso()          │
│ + get_available_filesystem_handlers()       │
└───────────────┬─────────────────────────────┘
                │
                ├─────────────────┬─────────────────┬─────────────────┬─────────────────┐
                │                 │                 │                 │                 │
                ▼                 ▼                 ▼                 ▼                 ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  FatHandler       │ │  NtfsHandler      │ │  ExfatHandler     │ │  F2fsHandler      │ │  BtrfsHandler     │
├───────────────────┤ ├───────────────────┤ ├───────────────────┤ ├───────────────────┤ ├───────────────────┤
│ + format()        │ │ + format()        │ │ + format()        │ │ + format()        │ │ + format()        │
│ + check_limits()  │ │ + check_limits()  │ │ + check_limits()  │ │ + check_limits()  │ │ + check_limits()  │
│ + setup_boot()    │ │ + setup_boot()    │ │ + setup_boot()    │ │ + setup_boot()    │ │ + setup_boot()    │
└───────────────────┘ │ + validate()      │ │ + validate()      │ └───────────────────┘ └───────────────────┘
                      └───────────────────┘ └───────────────────┘
```

## 1. Filesystem Implementation Details

### 1.1 Filesystem Handler Architecture

The `FilesystemHandler` abstract class defines the interface that all filesystem implementations must follow:

```python
class FilesystemHandler:
    """Base class for filesystem handlers"""
    
    @classmethod
    def name(cls):
        """Return the name of the filesystem"""
        raise NotImplementedError
        
    @classmethod
    def supports_file_size_greater_than_4gb(cls):
        """Check if the filesystem supports files larger than 4GB"""
        raise NotImplementedError
        
    @classmethod
    def parted_fs_type(cls):
        """Return the filesystem type for parted"""
        raise NotImplementedError
        
    @classmethod
    def format_partition(cls, partition, label):
        """Format the partition with this filesystem"""
        raise NotImplementedError
        
    @classmethod
    def check_dependencies(cls):
        """Check if the required dependencies are installed"""
        raise NotImplementedError
        
    @classmethod
    def needs_uefi_support_partition(cls):
        """Check if this filesystem needs a separate UEFI support partition"""
        raise NotImplementedError
```

Each filesystem handler implements these methods with filesystem-specific logic.

### 1.2 Filesystem Selection Algorithm

The filesystem selection algorithm automatically chooses the optimal filesystem based on:
1. Whether the ISO contains files larger than 4GB
2. Available filesystem tools on the host system
3. A preference order (exFAT > NTFS > F2FS > BTRFS > FAT32)

```python
def get_optimal_filesystem_for_iso(source_path):
    """
    Get the optimal filesystem type for the given ISO
    
    Args:
        source_path (str): Path to the source ISO
        
    Returns:
        str: Optimal filesystem type
    """
    # Check if there are files larger than 4GB
    has_large_files = utils.check_fat32_filesize_limitation(source_path)
    
    # Get available filesystem handlers
    available_fs = get_available_filesystem_handlers()
    
    if has_large_files:
        # Prefer filesystems that support large files
        for fs_type in ["EXFAT", "NTFS", "F2FS", "BTRFS"]:
            if fs_type in available_fs:
                return fs_type
    
    # Default to FAT32 for maximum compatibility
    if "FAT" in available_fs:
        return "FAT"
    
    # If FAT32 is not available, use the first available filesystem
    if available_fs:
        return available_fs[0]
    
    # No filesystem handlers available
    raise ValueError("No filesystem handlers available")
```
    
                           v                                                              |
                    <Windows 11 ISO?> ──Yes──> [Check Windows-To-Go option]               |
                           |                         |                                    |
                           No                        v                                    |
                           |              <WTG option selected?> ──Yes──> [Configure WTG partitions]
                           |                         |                          |
                           |                        No                          v
                           └─────────────────┬──────┘                  [Apply selected options]
                                            |                                   |
                                            v                                   v
                                   [Configure standard partitions] <───────────┘
                                            |
                                            v
                                          END
```


### 1.3 exFAT Implementation

The exFAT implementation includes optimizations for flash drives and comprehensive validation:

```python
class ExfatFilesystemHandler(FilesystemHandler):
    """Handler for exFAT filesystem operations"""
    
    @classmethod
    def format_partition(cls, partition, label):
        """Format the partition as exFAT"""
        # Get device type (HDD, SSD, USB Flash)
        device_base = partition.rstrip('0123456789')
        is_rotational = 1  # Default to HDD
        
        try:
            with open(f"/sys/block/{os.path.basename(device_base)}/queue/rotational", 'r') as f:
                is_rotational = int(f.read().strip())
        except (IOError, OSError):
            pass
            
        # Set optimal parameters based on device type
        format_opts = [
            "--volume-label", label,
        ]
        
        if not is_rotational:
            # For SSDs and flash drives
            format_opts.extend([
                "--cluster-size=128K",  # Reduce write amplification
                "--alignment=1M"        # Align with flash erase blocks
            ])
        else:
            # For HDDs
            format_opts.extend([
                "--cluster-size=32K"    # Better for general HDD use
            ])
            
        # Format the partition
        command_mkexfat = utils.check_command("mkexfatfs") or utils.check_command("mkfs.exfat")
        if not command_mkexfat:
            utils.print_with_color(_("Error: mkexfatfs/mkfs.exfat command not found"), "red")
            return 1
            
        cmd = [command_mkexfat] + format_opts + [partition]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            utils.print_with_color(_("Error: Unable to create exFAT filesystem"), "red")
            return 1
            
        # Validate the filesystem
        if not cls.validate_filesystem(partition):
            return 1
            
        return 0
```

Key features of the exFAT implementation:

1. **Device-Specific Optimizations**:
   - For SSDs and flash drives: 128KB cluster size and 1MB alignment
   - For HDDs: 32KB cluster size for better performance

2. **Comprehensive Validation**:
   - Filesystem check using fsck.exfat
   - Large file write test (>4GB)
   - Mount/unmount test

3. **UEFI Boot Support**:
   - Uses UEFI:NTFS bootloader for UEFI booting
   - Creates a small FAT32 partition for UEFI boot support
    


### 1.4 NTFS Enhancements

The NTFS implementation includes improved validation and optimized formatting:

```python
class NtfsFilesystemHandler(FilesystemHandler):
    """Handler for NTFS filesystem operations"""
    
    @classmethod
    def format_partition(cls, partition, label):
        """Format the partition as NTFS"""
        # Get device type (HDD, SSD, USB Flash)
        device_base = partition.rstrip('0123456789')
        is_rotational = 1  # Default to HDD
        
        try:
            with open(f"/sys/block/{os.path.basename(device_base)}/queue/rotational", 'r') as f:
                is_rotational = int(f.read().strip())
        except (IOError, OSError):
            pass
            
        # Set optimal parameters based on device type
        format_opts = [
            "-f",  # Fast format
            "-L", label,
            "-v"   # Verbose output
        ]
        
        if not is_rotational:
            # For SSDs and flash drives
            format_opts.extend([
                "-c", "4096",  # 4K cluster size for SSDs
                "-a", "4096"   # 4K alignment for better performance
            ])
        else:
            # For HDDs
            format_opts.extend([
                "-c", "16384"  # 16K cluster size for HDDs
            ])
            
        # Format the partition
        command_mkntfs = utils.check_command("mkntfs")
        if not command_mkntfs:
            utils.print_with_color(_("Error: mkntfs command not found"), "red")
            return 1
            
        cmd = [command_mkntfs] + format_opts + [partition]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            utils.print_with_color(_("Error: Unable to create NTFS filesystem"), "red")
            return 1
            
        # Validate the filesystem
        if not cls.validate_filesystem(partition):
            return 1
            
        return 0
```

Key enhancements to NTFS support:

1. **Optimized Formatting**:
   - For SSDs: 4KB cluster size and alignment
   - For HDDs: 16KB cluster size

2. **Improved Validation**:
   - Filesystem check using ntfsfix/ntfsck
   - Large file write test (>4GB)
   - Mount/unmount test

3. **Integrated UEFI:NTFS Bootloader**:
   - Bundled bootloader image
   - Fallback download mechanism
   - Automatic installation for UEFI boot support
    

## 2. Partition Management System

### 2.1 GPT Partition Table Implementation

```python
def create_gpt_partition_table(target_device):
    """Create GPT partition table on target device"""
    # Wipe existing partition table
    subprocess.run(["wipefs", "--all", target_device])
    
    # Create GPT partition table
    subprocess.run(["parted", "--script", target_device, "mklabel", "gpt"])
    
    # Create protective MBR for compatibility
    subprocess.run(["sgdisk", "--hybrid", target_device])
```

### 2.2 Partition Layout Templates

#### Standard Windows USB Layout (GPT)
```
┌─────────────────────────────────────────────────────────────────┐
│ Partition 1: Microsoft reserved (16MB)                          │
├─────────────────────────────────────────────────────────────────┤
│ Partition 2: EFI System Partition - FAT32 (200MB)               │
├─────────────────────────────────────────────────────────────────┤
│ Partition 3: Main Windows partition - NTFS/exFAT (Remaining)    │
└─────────────────────────────────────────────────────────────────┘
```

#### Windows-To-Go Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ Partition 1: Microsoft reserved (16MB)                          │
├─────────────────────────────────────────────────────────────────┤
│ Partition 2: EFI System Partition - FAT32 (200MB)               │
├─────────────────────────────────────────────────────────────────┤
│ Partition 3: Windows OS - NTFS (30GB+)                          │
├─────────────────────────────────────────────────────────────────┤
│ Partition 4: Windows data - NTFS/exFAT (Remaining)              │
└─────────────────────────────────────────────────────────────────┘
```

#### Multi-Boot Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ Partition 1: Microsoft reserved (16MB)                          │
├─────────────────────────────────────────────────────────────────┤
│ Partition 2: EFI System Partition - FAT32 (200MB)               │
├─────────────────────────────────────────────────────────────────┤
│ Partition 3: Shared data - exFAT (User-defined)                 │
├─────────────────────────────────────────────────────────────────┤
│ Partition 4: Windows 1 - NTFS/exFAT (User-defined)              │
├─────────────────────────────────────────────────────────────────┤
│ Partition 5+: Additional OSes - Various FS (User-defined)       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Partition Type Codes

| Partition Type | GPT GUID | MBR Code | Description |
|----------------|----------|----------|-------------|
| Microsoft Reserved | E3C9E316-0B5C-4DB8-817D-F92DF00215AE | 0x0C | Required for Windows |
| EFI System | C12A7328-F81F-11D2-BA4B-00A0C93EC93B | 0xEF | EFI bootloader partition |
| Windows Basic Data | EBD0A0A2-B9E5-4433-87C0-68B6B72699C7 | 0x07 | Windows NTFS partition |
| exFAT | 516E7CB4-6ECF-11D6-8FF8-00022D09712B | 0x07 | exFAT partition |
| Windows Recovery | DE94BBA4-06D1-4D40-A16A-BFD50179D6AC | 0x27 | Windows recovery partition |

## 3. Multi-Boot Implementation

### 3.1 Boot Manager Configuration

GRUB2 will be used as the primary boot manager with the following configuration:

```
menuentry "Windows 10" {
    insmod part_gpt
    insmod search_fs_uuid
    insmod chain
    search --fs-uuid --set=root XXXX-XXXX
    chainloader /EFI/Microsoft/Boot/bootmgfw.efi
}

menuentry "Windows 11 To-Go" {
    insmod part_gpt
    insmod search_fs_uuid
    insmod ntfs
    insmod chain
    search --fs-uuid --set=root YYYY-YYYY
    chainloader /EFI/Boot/bootx64.efi
}
```

### 3.2 Boot Manager Installation

```python
def install_grub_bootloader(target_device, efi_partition, config_entries):
    """Install GRUB bootloader for multi-boot support"""
    # Mount EFI partition
    subprocess.run(["mount", efi_partition, "/mnt/efi"])
    
    # Install GRUB for UEFI
    subprocess.run(["grub-install", "--target=x86_64-efi", 
                   "--efi-directory=/mnt/efi", "--boot-directory=/mnt/efi/boot",
                   "--removable", target_device])
    
    # Generate configuration
    generate_grub_config("/mnt/efi/boot/grub/grub.cfg", config_entries)
    
    # Unmount
    subprocess.run(["umount", "/mnt/efi"])
```

## 4. Windows-To-Go Implementation


### 4.1 Partition Layout

Windows-To-Go requires a specific partition layout:

```
┌─────────────────────────────────────────────────────────────────┐
│ Partition 1: EFI System Partition - FAT32 (260MB)              │
├─────────────────────────────────────────────────────────────────┤
│ Partition 2: Microsoft Reserved Partition (MSR) - 128MB        │
├─────────────────────────────────────────────────────────────────┤
│ Partition 3: Windows OS Partition - NTFS/exFAT (Remaining)     │
└─────────────────────────────────────────────────────────────────┘
```

This layout is created using the `create_wintogo_partition_layout` function:

```python
def create_wintogo_partition_layout(target_device, filesystem_type, filesystem_label):
    """Create a specialized partition layout for Windows-To-Go"""
    # Wipe existing partition table
    wipe_existing_partition_table_and_filesystem_signatures(target_device)
    
    # Create GPT partition table (required for Windows-To-Go)
    subprocess.run(["parted", "--script", target_device, "mklabel", "gpt"])
    
    # Create EFI System Partition (ESP)
    subprocess.run([
        "parted", "--script", target_device,
        "mkpart", "ESP", "fat32", "1MiB", "261MiB",
        "set", "1", "boot", "on",
        "set", "1", "esp", "on"
    ])
    
    # Create Microsoft Reserved Partition (MSR)
    subprocess.run([
        "parted", "--script", target_device,
        "mkpart", "MSR", "261MiB", "389MiB",
        "set", "2", "msftres", "on"
    ])
    
    # Create Windows partition with remaining space
    subprocess.run([
        "parted", "--script", target_device,
        "mkpart", "Windows", "389MiB", "100%"
    ])
    
    # Format EFI System Partition
    esp_partition = target_device + "1"
    subprocess.run([
        "mkfs.fat", "-F", "32", "-n", "ESP", esp_partition
    ])
    
    # Format Windows partition with selected filesystem
    windows_partition = target_device + "3"
    fs_handler = fs_handlers.get_filesystem_handler(filesystem_type)
    fs_handler.format_partition(windows_partition, filesystem_label)
    
    return 0
```

### 4.2 TPM Bypass for Windows 11

Windows 11 requires TPM 2.0, Secure Boot, and other hardware requirements that may not be available on all systems. WowUSB-DS9 implements a bypass for these requirements:

```python
def bypass_windows11_tpm_requirement(target_fs_mountpoint):
    """Bypass Windows 11 TPM, Secure Boot, and RAM requirements for Windows-To-Go"""
    # Create registry files directory
    registry_dir = os.path.join(target_fs_mountpoint, "Windows", "System32", "config")
    os.makedirs(registry_dir, exist_ok=True)
    
    # Create registry bypass file
    bypass_reg_path = os.path.join(target_fs_mountpoint, "bypass_requirements.reg")
    
    with open(bypass_reg_path, "w") as reg_file:
        reg_file.write("""Windows Registry Editor Version 5.00

; Bypass TPM 2.0 requirement
[HKEY_LOCAL_MACHINE\\SYSTEM\\Setup\\LabConfig]
"BypassTPMCheck"=dword:00000001
"BypassSecureBootCheck"=dword:00000001
"BypassRAMCheck"=dword:00000001

; Disable TPM check for Windows Update
[HKEY_LOCAL_MACHINE\\SYSTEM\\Setup\\MoSetup]
"AllowUpgradesWithUnsupportedTPMOrCPU"=dword:00000001
""")
    
    # Create setup completion script to apply registry modifications
    setup_script_path = os.path.join(target_fs_mountpoint, "Windows", "Setup", "Scripts")
    os.makedirs(setup_script_path, exist_ok=True)
    
    with open(os.path.join(setup_script_path, "SetupComplete.cmd"), "w") as script_file:
        script_file.write("""@echo off
reg import %SystemDrive%\\bypass_requirements.reg
""")
    
    return 0
```

### 4.3 Portable Windows Configuration

To make Windows work properly in a portable environment, additional registry modifications are applied:

```python
def prepare_windows_portable_drivers(target_fs_mountpoint):
    """Prepare Windows for portable operation by configuring drivers and hardware detection"""
    # Create registry file for portable operation
    portable_reg_path = os.path.join(target_fs_mountpoint, "portable_config.reg")
    
    with open(portable_reg_path, "w") as reg_file:
        reg_file.write("""Windows Registry Editor Version 5.00

; Enable driver database for multiple hardware profiles
[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\PnP]
"DisableCrossSessionDriverLoad"=dword:00000000

; Enable all storage controllers
[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\storahci]
"Start"=dword:00000000

[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\stornvme]
"Start"=dword:00000000

; Disable fast startup (causes issues with hardware changes)
[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Power]
"HiberbootEnabled"=dword:00000000
""")
    
    # Update setup completion script to apply portable configuration
    setup_script_path = os.path.join(target_fs_mountpoint, "Windows", "Setup", "Scripts", "SetupComplete.cmd")
    
    with open(setup_script_path, "a") as script_file:
        script_file.write("""
reg import %SystemDrive%\\portable_config.reg

rem Enable all network adapters
powershell -Command "Get-NetAdapter | Enable-NetAdapter -Confirm:$false"

rem Optimize for portable operation
powershell -Command "Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Power' -Name 'HibernateEnabled' -Value 0"
""")
    
    return 0
```

### 4.4 Bootloader Configuration

For Windows-To-Go to boot properly, the bootloader must be configured correctly:

1. **EFI System Partition (ESP)** is created and formatted with FAT32  
2. **Bootloader files** are copied from the Windows partition to the ESP  
3. **BCD store** is created for Windows boot configuration  

This ensures that the Windows-To-Go drive can boot on both UEFI and legacy BIOS systems.
    

## 5. UI Enhancements for New Features

### 5.1 Filesystem and Partition Editor Component

```python
class DiskVisualizationPanel(wx.Panel):
    """Interactive disk visualization and partitioning panel"""
    
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        
        # Set up visualization
        self.disk_bitmap = wx.StaticBitmap(self)
        self.partition_sliders = []
        
        # Set up controls
        self.filesystem_choices = wx.Choice(self, choices=["FAT32", "NTFS", "exFAT", "F2FS"])
        self.partition_type_choices = wx.Choice(self, choices=["Primary", "EFI System", "MSR", "Data"])
        
        # Bind events
        self.filesystem_choices.Bind(wx.EVT_CHOICE, self.on_filesystem_changed)
        
        # Layout components
        self._do_layout()
    
    def update_visualization(self, partition_info):
        """Update the visual representation based on partition info"""
        # Generate disk image here
        # ...
        
    def on_filesystem_changed(self, event):
        """Handle filesystem selection changes"""
        selected_fs = self.filesystem_choices.GetStringSelection()
        # Update UI elements based on filesystem selection
        # ...
```

### 5.2 Configuration Profile System

```python
class ConfigProfile:
    """Configuration profile for saving/loading WoeUSB settings"""
    
    def __init__(self, name="Default"):
        self.name = name
        self.settings = {
            "filesystem": "FAT32",
            "partition_scheme": "MBR",
            "boot_options": {
                "windows_to_go": False,
                "multi_boot": False,
                "persistence": False
            },
            "partitions": []
        }
    
    def save(self, filename):
        """Save profile to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.settings, f, indent=2)
    
    @classmethod
    def load(cls, filename):
        """Load profile from JSON file"""
        profile = cls()
        with open(filename, 'r') as f:
            profile.settings = json.load(f)
        return profile
```

## 6. Integration Tests

### 6.1 Filesystem Format and Boot Tests

```python
def test_filesystem_format_and_boot(filesystem_type, device, iso_path):
    """Test formatting and booting with specified filesystem"""
    # Format device
    format_device(device, filesystem_type)
    
    # Install Windows
    install_windows(device, iso_path)
    
    # Test bootability (simulate in VM)
    result = test_boot_in_vm(device)
    
    return result
```

### 6.2 Multi-Boot Configuration Tests

```python
def test_multi_boot_configuration(device, iso_paths):
    """Test multi-boot setup with multiple Windows ISOs"""
    # Set up partitions
    setup_multi_boot_partitions(device, len(iso_paths))
    
    # Install each ISO
    for i, iso_path in enumerate(iso_paths):
        install_windows_to_partition(device, i+1, iso_path)
    
    # Install boot manager
    install_boot_manager(device)
    
    # Test bootability of each entry
    results = []
    for i in range(len(iso_paths)):
        results.append(test_boot_entry_in_vm(device, i))
    
    return results
```

## 7. Dependency Management

| Feature | Required Packages | Optional Packages |
|---------|-------------------|-------------------|
| exFAT support | exfatprogs/exfat-utils, exfat-fuse | - |
| NTFS support | ntfs-3g | ntfsprogs |
| GPT partitioning | gdisk, sgdisk | gptfdisk |
| Windows-To-Go | wimlib-imagex | dism (Windows) |
| TPM emulation | reged (chntpw) | - |
| Multi-boot | grub2 | os-prober |
| Boot management | efibootmgr | - |

The implementation will check for these dependencies and provide clear error messages if they are missing.