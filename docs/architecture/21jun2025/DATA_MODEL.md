# WowUSB-DS9: Conceptual Data Model / Key Entities

This document describes the key conceptual data entities and structures that WowUSB-DS9 manages during its operation. This is not a formal database schema but rather a representation of the main pieces of information the application works with.

## 1. Core Entities

```mermaid
erDiagram
    SOURCE_MEDIA {
        string path "Path to ISO file or device (e.g., /dev/sr0)"
        string type "ISO_FILE, DVD_DEVICE"
        string mount_point "Temporary mount location (e.g., /media/wowusb_source_...)"
        bool has_large_files "True if files > 4GB detected"
        string detected_windows_version "e.g., Windows 10, Windows 11"
    }

    TARGET_DEVICE {
        string path "Device path (e.g., /dev/sdb)"
        string model "Device model (from lsblk)"
        string size "Total device size (human-readable)"
        string original_fs_signatures "Signatures before wiping (if any)"
        PARTITION_TABLE table_type "MBR, GPT (GPT for WinToGo/Multiboot)"
    }

    TARGET_PARTITION {
        string path "Partition path (e.g., /dev/sdb1)"
        string type "PRIMARY, LOGICAL, ESP, MSR, DATA, RECOVERY, UEFI_SUPPORT, OS_INSTALL"
        string filesystem_type "FAT32, NTFS, EXFAT, F2FS, BTRFS"
        string label "User-defined or default label"
        string size_request "Requested size (e.g., from multiboot config)"
        string actual_size "Actual formatted size"
        string mount_point "Temporary mount location (e.g., /media/wowusb_target_...)"
        bool is_bootable "Boot flag set (for MBR)"
        string uuid "Partition UUID"
    }

    FILESYSTEM_HANDLER_CONFIG {
        string fs_name "Name (FAT32, NTFS, etc.)"
        list required_tools "e.g., ['mkfs.ntfs', 'ntfs-3g']"
        bool supports_large_files
        bool needs_uefi_support_partition
    }

    BOOTLOADER_CONFIG {
        string type "GRUB_LEGACY, UEFI_WINDOWS, UEFI_NTFS_WRAPPER, GRUB_MULTIBOOT"
        string install_location "MBR, Filesystem_Root, ESP_Partition"
        string config_file_path "Path to grub.cfg or BCD"
        list required_files "e.g., [bootmgfw.efi, bootx64.efi, uefi-ntfs.img]"
    }

    APP_CONFIGURATION {
        string install_mode "DEVICE, PARTITION, MULTIBOOT"
        bool wintogo_enabled
        bool skip_legacy_bootloader
        bool workaround_bios_boot_flag
        string persistence_size_mb "(For Linux in Multiboot)"
        bool verbose_output
        bool no_color_output
        bool debug_mode
        string temp_directory_base "/tmp/WowUSB."
    }

    OS_INSTALL_CONFIG {
        string os_type "WINDOWS, LINUX"
        string name "User-friendly name (e.g., 'Windows 10 Pro', 'Ubuntu 22.04')"
        string iso_path "Path to the OS ISO file"
        string requested_size_gb "(For multiboot partition)"
        string target_filesystem "Filesystem for this OS partition"
        TARGET_PARTITION os_partition_ref
        BOOTLOADER_CONFIG bootloader_entry_details
    }

    SHARED_PARTITION_CONFIG {
        string requested_size_gb "(For multiboot)"
        string target_filesystem "e.g., EXFAT, NTFS"
        TARGET_PARTITION shared_partition_ref
    }

    TARGET_DEVICE ||--o{ TARGET_PARTITION : "has"
    SOURCE_MEDIA }o--|| APP_CONFIGURATION : "influences choices in"
    TARGET_DEVICE ||--| APP_CONFIGURATION : "is configured by"
    TARGET_PARTITION }o--|| FILESYSTEM_HANDLER_CONFIG : "is formatted using"
    TARGET_PARTITION ||--o{ BOOTLOADER_CONFIG : "may host"
    TARGET_DEVICE ||--o{ BOOTLOADER_CONFIG : "may host (MBR)"
    APP_CONFIGURATION ||--o{ OS_INSTALL_CONFIG : "details (multiboot)"
    APP_CONFIGURATION ||--o{ SHARED_PARTITION_CONFIG : "details (multiboot)"
    OS_INSTALL_CONFIG }o--|| SOURCE_MEDIA : "uses (ISO)"


```

## 2. Entity Descriptions

*   **`SOURCE_MEDIA`**:
    *   Represents the input Windows installation source (ISO file or physical DVD).
    *   Key attributes: path, type (to distinguish ISO from device), temporary mount point after mounting, and derived information like whether it contains files larger than 4GB (critical for filesystem selection) and the detected Windows version (for version-specific workarounds like Win11 TPM bypass).

*   **`TARGET_DEVICE`**:
    *   Represents the physical USB drive.
    *   Key attributes: device path (e.g., `/dev/sdb`), model, size, and the type of partition table (MBR or GPT) that will be/is written to it. `original_fs_signatures` might be stored before wiping for informational or rollback (though rollback is not a current feature).

*   **`TARGET_PARTITION`**:
    *   Represents a partition created or used on the `TARGET_DEVICE`. A device can have multiple partitions, especially in WinToGo or Multiboot scenarios.
    *   Key attributes: path (e.g., `/dev/sdb1`), type (purpose of the partition), chosen filesystem, label, requested and actual sizes, temporary mount point, and bootable status.
    *   **Partition Types (Examples):**
        *   `OS_INSTALL`: Main partition for Windows files.
        *   `UEFI_SUPPORT`: Small FAT32 partition for UEFI boot files when main FS is NTFS/exFAT.
        *   `ESP` (EFI System Partition): Standard FAT32 partition for UEFI bootloaders (especially in GPT setups for WinToGo/Multiboot).
        *   `MSR` (Microsoft Reserved Partition): Used with GPT.
        *   `DATA`: A shared data partition in multiboot setups.
        *   `RECOVERY`: Windows Recovery Environment partition.

*   **`FILESYSTEM_HANDLER_CONFIG`**:
    *   Represents the properties and requirements of a supported filesystem (FAT32, NTFS, exFAT, F2FS, BTRFS). This is more of a configuration/metadata entity, embodied by the filesystem handler classes in `filesystem_handlers.py`.
    *   Key attributes: name, list of required system tools for formatting, support for large files, and whether it typically needs a separate UEFI support partition for Windows booting.

*   **`BOOTLOADER_CONFIG`**:
    *   Represents the configuration for a bootloader to be installed.
    *   Key attributes: type (e.g., GRUB for legacy, specific UEFI setup), installation location (MBR, a partition's boot sector, or files in ESP), path to its configuration file (like `grub.cfg` or BCD store), and any required binary files.

*   **`APP_CONFIGURATION`**:
    *   Holds the overall settings and options for the current WowUSB operation, derived from user input (CLI arguments or GUI selections).
    *   Key attributes: installation mode, flags for WinToGo, skipping legacy bootloader, applying specific workarounds, persistence settings (for Linux in multiboot), verbosity, and temporary directory path.

*   **`OS_INSTALL_CONFIG` (Primarily for Multiboot):**
    *   Defines the specifics for one OS to be installed in a multiboot setup.
    *   Key attributes: OS type (Windows/Linux), user-friendly name, path to its ISO, requested partition size, target filesystem for its partition, a reference to the actual `TARGET_PARTITION` created for it, and details for its bootloader entry.

*   **`SHARED_PARTITION_CONFIG` (Primarily for Multiboot):**
    *   Defines the specifics for the shared data partition in a multiboot setup.
    *   Key attributes: requested size, target filesystem, and a reference to the actual `TARGET_PARTITION`.

## 3. Relationships

*   A `SOURCE_MEDIA` is processed based on `APP_CONFIGURATION`.
*   A `TARGET_DEVICE` is partitioned and configured according to `APP_CONFIGURATION`.
*   A `TARGET_DEVICE` has one or more `TARGET_PARTITION`s.
*   Each `TARGET_PARTITION` is formatted using rules from a `FILESYSTEM_HANDLER_CONFIG` and may host components of a `BOOTLOADER_CONFIG`.
*   The MBR of a `TARGET_DEVICE` can also host parts of a `BOOTLOADER_CONFIG` (e.g., legacy GRUB).
*   In multiboot mode, `APP_CONFIGURATION` will contain multiple `OS_INSTALL_CONFIG` entries and potentially one `SHARED_PARTITION_CONFIG`. Each `OS_INSTALL_CONFIG` uses a `SOURCE_MEDIA` (its ISO).

## 4. Data Flow during Operations

1.  **Input Gathering:** `APP_CONFIGURATION` is populated from user arguments/GUI. `SOURCE_MEDIA` path is identified.
2.  **Source Analysis:** `SOURCE_MEDIA` is mounted, `has_large_files` and `detected_windows_version` are determined.
3.  **Target Preparation:** `TARGET_DEVICE` is identified. Based on `APP_CONFIGURATION.install_mode`:
    *   **Device Mode:** Existing partitions on `TARGET_DEVICE` are wiped. New `TARGET_PARTITION`(s) are defined (e.g., one main partition, or ESP + Main for WinToGo, or Main + UEFI_SUPPORT for NTFS/exFAT).
    *   **Partition Mode:** An existing `TARGET_PARTITION` is used.
    *   **Multiboot Mode:** Multiple `TARGET_PARTITION`s are planned based on `OS_INSTALL_CONFIG`s and `SHARED_PARTITION_CONFIG`.
4.  **Formatting:** Each `TARGET_PARTITION` is formatted. The choice of filesystem (and thus the relevant `FILESYSTEM_HANDLER_CONFIG`) is determined by `APP_CONFIGURATION.target_filesystem`, `SOURCE_MEDIA.has_large_files`, and available tools.
5.  **File Copy:** Data is copied from the mounted `SOURCE_MEDIA` to the primary `TARGET_PARTITION` for the OS.
6.  **Bootloader Installation:** `BOOTLOADER_CONFIG` is determined based on `APP_CONFIGURATION` (legacy, UEFI, WinToGo specifics, multiboot GRUB). Bootloader files are written to the appropriate `TARGET_PARTITION` (e.g., ESP, UEFI_SUPPORT partition) or the MBR of `TARGET_DEVICE`. Configuration files (grub.cfg, BCD) are created/modified.

This conceptual model helps in understanding how different pieces of information are related and transformed during the WowUSB-DS9 execution process.
```
