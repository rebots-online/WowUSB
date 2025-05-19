
# WowUSB-DS9 Architecture Documentation

## System Overview

WowUSB-DS9 is a Linux utility for creating bootable Windows USB installers from Windows ISO images or DVDs. The software supports both legacy BIOS booting and UEFI booting, with multiple filesystem options including FAT32, NTFS, exFAT, F2FS, and BTRFS, as well as Windows-To-Go functionality.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          WowUSB System                              │
├─────────────────┬─────────────────────────┬───────────────────────┬─┘
│                 │                         │                       │
│  Command Line   │         Core            │      Utilities        │
│  Interface      │     Processing          │                       │
│ (wowusb script) │     (core.py)           │     (utils.py)        │
│                 │                         │                       │
└─────────────────┘                         │                       │
                   │                        │                       │
                   │                        │                       │
┌─────────────────┐│                        │                       │
│                 ││                        │                       │
│  GUI Interface  ││                        │                       │
│ (woeusbgui,     ││                        │                       │
│  gui.py)        ││                        │                       │
│                 ││                        │                       │
└─────────────────┘│                        │                       │
                   │                        │                       │
┌──────────────────┴──────────┐  ┌──────────┴───────────┐  ┌───────┴───────────────┐
│                             │  │                      │  │                       │
│ Filesystem Operations       │  │ Device Operations    │  │ Workarounds           │
│ - Format partitions         │  │ - Partition creation │  │ - UEFI:NTFS support  │
│ - Mount/unmount             │  │ - Device detection   │  │ - Windows 7 UEFI boot │
│ - Copy files                │  │ - Block operations   │  │ - Boot flag fixes     │
│                             │  │                      │  │ - Windows-To-Go       │
└─────────┬─────────────────┬─┘  └──────────────────────┘  └───────────────────────┘
          │                 │
┌─────────┴─────────┐ ┌────┴────────────┐
│                   │ │                 │
│ Filesystem        │ │ Bootloader      │
│ Handlers          │ │ Management      │
│ - FAT32           │ │ - UEFI:NTFS     │
│ - NTFS            │ │ - Bundled files │
│ - exFAT           │ │ - Fallback      │
│ - F2FS            │ │ - Verification  │
│ - BTRFS           │ │                 │
└───────────────────┘ └─────────────────┘
```

## Process Flow

```
┌────────────────┐     ┌───────────────────┐     ┌─────────────────────┐
│                │     │                   │     │                     │
│ Parse Command  │────▶│ Check Runtime     │────▶│ Prepare Target      │
│ Line Arguments │     │ Dependencies      │     │ Device/Partition    │
│                │     │                   │     │                     │
└────────────────┘     └───────────────────┘     └──────────┬──────────┘
                                                            │
                                                            ▼
┌────────────────┐     ┌───────────────────┐     ┌─────────────────────┐
│                │     │                   │     │                     │
│ Mount Source & │◀────│ Create & Format   │◀────│ Check Source Files  │
│ Target FS      │     │ Target Partition  │     │ & Select Filesystem │
│                │     │                   │     │                     │
└───────┬────────┘     └───────────────────┘     └─────────────────────┘
        │
        ▼
┌────────────────┐     ┌───────────────────┐     ┌─────────────────────┐
│                │     │                   │     │                     │
│ Copy Files     │────▶│ Install Boot      │────▶│ Apply Workarounds   │
│ from Source    │     │ Loaders           │     │ (as needed)         │
│                │     │                   │     │                     │
└────────────────┘     └───────────────────┘     └──────────┬──────────┘
                                                            │
                                                            ▼
                                                 ┌─────────────────────┐
                                                 │                     │
                                                 │ Unmount & Cleanup   │
                                                 │                     │
                                                 └─────────────────────┘
```

## Filesystem Selection Logic

```
┌────────────────┐
│                │
│ Start with     │
│ Target FS=AUTO │
│                │
└───────┬────────┘
        │
        ▼
┌────────────────────────┐    Yes    ┌─────────────────────────┐
│                        │           │                         │
│ Any file > 4GB in      ├──────────▶│ Select from available   │
│ source filesystem?     │           │ filesystems:            │
│                        │           │ exFAT > NTFS > F2FS >   │
└───────┬────────────────┘           │ BTRFS                   │
        │                            │                         │
        │ No                         └────────────┬────────────┘
        ▼                                         │
┌────────────────┐                    ┌─────────────────────────┐
│                │                    │                         │
│ Use FAT32      │                    │ Create UEFI support     │
│ filesystem     │                    │ partition if needed     │
│                │                    │                         │
└────────────────┘                    └─────────────────────────┘
```

## Windows-To-Go Support

```
┌────────────────┐
│                │
│ Windows-To-Go  │
│ option enabled │
│                │
└───────┬────────┘
        │
        ▼
┌────────────────────────┐
│                        │
│ Create GPT partition   │
│ table with:            │
│ 1. ESP (FAT32)         │
│ 2. MSR                 │
│ 3. Windows (NTFS/exFAT)│
│                        │
└───────┬────────────────┘
        │
        ▼
┌────────────────────────┐    Yes    ┌─────────────────────────┐
│                        │           │                         │
│ Windows 11 detected?   ├──────────▶│ Apply TPM and Secure    │
│                        │           │ Boot bypass             │
└───────┬────────────────┘           │                         │
        │                            └────────────┬────────────┘
        │ No                                      │
        ▼                                         ▼
┌────────────────────────┐           ┌─────────────────────────┐
│                        │           │                         │
│ Configure portable     ├──────────▶│ Install bootloader      │
│ drivers and registry   │           │ to ESP partition        │
│                        │           │                         │
└────────────────────────┘           └─────────────────────────┘
```

## UEFI:NTFS Bootloader Integration

```
┌────────────────────────┐
│                        │
│ Target filesystem      │
│ is NTFS or exFAT       │
│                        │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│                        │
│ Create main partition  │
│ for Windows files      │
│                        │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│                        │
│ Create small FAT16     │
│ partition for UEFI     │
│ bootloader             │
│                        │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────────────────────────────┐
│                                                │
│ Check for bundled UEFI:NTFS bootloader         │
│ (WowUSB/data/bootloaders/uefi-ntfs.img)        │
│                                                │
└───────────┬────────────────────────────────────┘
            │
            ▼
┌────────────────────────┐    No     ┌─────────────────────────┐
│                        │           │                         │
│ Bundled bootloader     ├──────────▶│ Download bootloader     │
│ available and valid?   │           │ from GitHub             │
│                        │           │                         │
└───────────┬────────────┘           └────────────┬────────────┘
            │ Yes                                 │
            │                                     │
            ▼                                     ▼
┌────────────────────────────────────────────────────────────┐
│                                                            │
│ Write bootloader image to UEFI support partition           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Filesystem Types and Constraints

| Filesystem | Max File Size | Max Volume Size | UEFI Boot Support | Optimized For      | Notes                                                                 |
|------------|---------------|-----------------|-------------------|--------------------|-----------------------------------------------------------------------|
| FAT32      | 4GB           | 32GB (typical)  | Native           | Compatibility      | Default choice, directly bootable in UEFI mode                       |
| NTFS       | 16TB          | 256TB           | Via UEFI:NTFS    | Windows            | Good for large files, requires UEFI:NTFS bridge                       |
| exFAT      | 16EB          | 128PB           | Via UEFI:NTFS    | Flash drives       | Best balance of performance and compatibility                          |
| F2FS       | 4GB - 3.94TB  | 16TB            | Via UEFI support | Flash drives       | Linux-optimized flash-friendly filesystem                              |
| BTRFS      | 16EB          | 16EB            | Via UEFI support | Advanced features  | Compression, snapshots, Linux-focused                                 |

## Filesystem Handler Architecture

The `FilesystemHandler` abstract class defines the interface that all filesystem implementations must follow:

```python
class FilesystemHandler:
    @classmethod
    def name(cls):
        """Return the name of the filesystem"""

    @classmethod
    def supports_file_size_greater_than_4gb(cls):
        """Check if the filesystem supports files larger than 4GB"""

    @classmethod
    def parted_fs_type(cls):
        """Return the filesystem type for parted"""

    @classmethod
    def format_partition(cls, partition, label):
        """Format the partition with this filesystem"""

    @classmethod
    def check_dependencies(cls):
        """Check if the required dependencies are installed"""

    @classmethod
    def needs_uefi_support_partition(cls):
        """Check if this filesystem needs a separate UEFI support partition"""

    @classmethod
    def get_uefi_bootloader_file(cls):
        """Get the appropriate UEFI bootloader file for this filesystem"""
```

Each filesystem handler implements these methods with filesystem-specific logic, allowing for a consistent interface while accommodating the unique requirements of each filesystem.

## Current Limitations

1. **FAT32 4GB file size limit**: The system automatically switches to NTFS when files larger than 4GB are detected.
2. **UEFI booting from NTFS**: Requires downloading and installing the UEFI:NTFS bootloader.
3. **Filesystem options**: Expanded to include exFAT, F2FS, and BTRFS beyond FAT32 and NTFS.
    