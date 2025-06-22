# WowUSB-DS9: Core Logic (`WowUSB/core.py`)

The `WowUSB/core.py` module is the heart of the WowUSB-DS9 application, containing the primary logic for creating bootable Windows USB drives. It's designed to be callable from both the CLI (`woeusb`) and GUI (`woeusbgui`) frontends.

*Self-correction: The `core.py` file has two distinct `main` functions and two `init` functions. The `run()` function, which is the entry point for the CLI, uses the older `init()` and older `main()`. The newer `main(args, temp_dir)` is primarily designed for the multiboot functionality. The following diagram and explanation will focus on the traditional single OS USB creation flow as primarily orchestrated by `run()` -> `init()` (older) -> `main()` (older).*

## 1. Main Orchestration Functions

*   **`run()`:**
    *   The main entry point when called from `WowUSB/woeusb` (CLI).
    *   Calls `setup_arguments()` to parse CLI args.
    *   Handles `--list-devices` separately.
    *   Calls `init()` (the older version, which itself calls `setup_arguments()` if CLI) to prepare parameters, mount points, temp directory.
    *   Calls `main()` (the older version, see below) to perform the USB creation.
    *   Ensures `cleanup()` is called in a `finally` block.

*   **`init(from_cli=True, ...)` (Older version, called by `run()`):**
    *   If `from_cli` is True, it calls `setup_arguments()` to parse args.
    *   Defines source/target mount point paths and creates a temporary directory.
    *   Populates variables like `install_mode`, `source_media`, `target_media`, `target_filesystem_type`, `verbose`, `debug` from arguments.
    *   Returns a list of these parameters.

*   **`main(source_fs_mountpoint, target_fs_mountpoint, source_media, target_media, install_mode, temp_directory, target_filesystem_type, workaround_bios_boot_flag, parser=None, skip_legacy_bootloader=False)` (Older version):**
    *   This is the primary workhorse function for single OS USB creation.
    *   The `parser` argument is somewhat misleading here as args are usually pre-processed by `init()`.
    *   The `wintogo` flag is fetched from `parser.wintogo` if `parser` is provided.

## 2. Core `main()` Function Activity Diagram (Simplified for single OS creation)

```mermaid
graph TD
    A[Start main_older] --> B{Check OS UID};
    B --> C{Check Runtime Params};
    C --> D{Determine Target Params};
    D --> E{Check Source/Target Not Busy};
    E --> F[Mount Source Filesystem];
    F --> G{Error?};
    G -- Yes --> Z[End with Error];
    G -- No --> H{Auto-select Filesystem?};
    H -- Yes --> I[fs_handlers.get_optimal_filesystem_for_iso];
    I --> J[Set target_filesystem_type];
    H -- No --> J;
    J --> K{Check FS Handler Deps & Capabilities};
    K --> L{Error?};
    L -- Yes --> Z;
    L -- No --> M{WinToGo Mode?};

    M -- Yes --> N[create_wintogo_partition_layout];
    N --> O{Error?};
    O -- Yes --> Z;
    O -- No --> P[Set target_partition to WinToGo Windows Part];
    P --> Q[Mount Target Filesystem];

    M -- No --> R{Install Mode == 'device'?};
    R -- Yes --> S[Wipe Target Sigs];
    S --> T[Create Target Partition Table (Legacy)];
    T --> U[Create Target Partition (Format)];
    U --> V{FS Handler Needs UEFI Support Part?};
    V -- Yes --> W[Create UEFI Support Partition];
    W --> X[Install UEFI Support Files];
    X --> Q;
    V -- No --> Q;
    R -- No (Partition Mode) --> Y[Check Target Partition Valid];
    Y --> Q;

    Q --> Aa{Error Mounting Target?};
    Aa -- Yes --> Z;
    Aa -- No --> Ab[Check Target Free Space];
    Ab --> Ac{Error?};
    Ac -- Yes --> Z;
    Ac -- No --> Ad[Copy Filesystem Files (Threaded)];
    Ad --> Ae{WinToGo Mode?};

    Ae -- Yes --> Af[Detect Win Version];
    Af --> Ag{Win11?};
    Ag -- Yes --> Ah[workaround.bypass_windows11_tpm_requirement];
    Ah --> Ai[workaround.prepare_windows_portable_drivers];
    Ai --> Aj[Mount ESP Partition];
    Aj --> Ak[Copy Bootloader Files to ESP];
    Ak --> Al[Create BCD Store];
    Al --> Am[Unmount ESP];
    Am --> An[workaround.support_windows_7_uefi_boot];
    Ag -- No --> Ai;

    Ae -- No --> An;

    An --> Ao{Skip Legacy Bootloader?};
    Ao -- No --> Ap[install_legacy_pc_bootloader_grub];
    Ap --> Aq[install_legacy_pc_bootloader_grub_config];
    Aq --> Ar{Workaround BIOS Boot Flag?};
    Ao -- Yes --> Ar;

    Ar -- Yes --> As[workaround.buggy_motherboards_that_ignore_disks_without_boot_flag_toggled];
    As --> At[Return Success];
    Ar -- No --> At;
    At --> End[Finished];

    Z --> End;
```

**Key Steps in `main()` (older version):**

1.  **Initial Checks:**
    *   Verifies if running as root (warns if not).
    *   Checks runtime parameters (source, target, mode).
    *   Determines target device and partition from `install_mode` and `target_media`.
    *   Ensures source and target are not busy (mounted elsewhere).

2.  **Mount Source:**
    *   Calls `mount_source_filesystem()` to mount the ISO or DVD. Handles errors.

3.  **Filesystem Selection & Validation:**
    *   If `target_filesystem_type` is "AUTO", calls `fs_handlers.get_optimal_filesystem_for_iso()`.
    *   Validates if the chosen filesystem can handle large files from the source (e.g., if FAT32 is chosen but source has >4GB files, it attempts to switch to exFAT or NTFS if available).
    *   Gets the appropriate filesystem handler using `fs_handlers.get_filesystem_handler()`.
    *   Checks if dependencies for the selected filesystem handler are met.

4.  **Windows-To-Go Specific Preparations (if `wintogo` is True and `install_mode` is 'device'):**
    *   Calls `create_wintogo_partition_layout()` to create a specific GPT layout (ESP, MSR, Windows, Recovery - *actual implementation might vary*).
    *   Updates `target_partition` to point to the main Windows partition of this layout.

5.  **Target Device Preparation (if `install_mode` is 'device' and not WinToGo):**
    *   `wipe_existing_partition_table_and_filesystem_signatures()`: Clears existing signatures.
    *   `create_target_partition_table()`: Creates a new partition table (typically MBR/legacy for this flow).
    *   `create_target_partition()`: Creates and formats the main partition using the selected `target_filesystem_type` and `filesystem_label` via the corresponding `fs_handler`.
    *   **UEFI Support Partition (if needed by FS handler, e.g., for NTFS):**
        *   `create_uefi_ntfs_support_partition()`: Creates a small FAT32 partition.
        *   `install_uefi_support_partition()`: Installs UEFI boot files (e.g., UEFI:NTFS drivers) to this partition.

6.  **Target Partition Validation (if `install_mode` is 'partition'):**
    *   `utils.check_target_partition()`: Validates the user-provided partition.

7.  **Mount Target:**
    *   Calls `mount_target_filesystem()` to mount the prepared target partition.

8.  **Space Check:**
    *   `utils.check_target_filesystem_free_space()`: Ensures enough space on target.

9.  **File Copying:**
    *   `copy_filesystem_files()`: Copies all files from source mount point to target mount point.
        *   This function starts `ReportCopyProgress(threading.Thread)` to provide progress updates (to console or GUI via callbacks).
        *   Uses `copy_large_file()` for files > 5MB, which allows for `utils.check_kill_signal()` to be called periodically for cancellation.

10. **Linux Persistence (if `args.persistence` is set - *Note: this seems to be handled by the newer `main(args, temp_dir)` flow, but stubbed in older flow's argument parsing*):**
    *   `setup_linux_persistence()`: If this were called, it would configure persistence for Linux ISOs (not typically for Windows).

11. **Windows-To-Go Post-Copy Steps (if `wintogo` is True):**
    *   Detects Windows version (`utils.detect_windows_version`).
    *   If Windows 11, applies TPM bypass (`workaround.bypass_windows11_tpm_requirement`).
    *   Prepares portable drivers (`workaround.prepare_windows_portable_drivers`).
    *   Mounts the ESP partition created earlier.
    *   Copies bootloader files (e.g., `bootmgfw.efi`, `bootmgr.efi`) from the Windows partition to `ESP/EFI/Boot/`.
    *   Creates BCD store on ESP, possibly copying from Windows partition.
    *   Unmounts ESP.

12. **Windows 7 UEFI Workaround:**
    *   `workaround.support_windows_7_uefi_boot()`: Applies necessary changes for Win7 UEFI boot.

13. **Legacy Bootloader Installation (if `skip_legacy_bootloader` is False):**
    *   `install_legacy_pc_bootloader_grub()`: Installs GRUB to the target device's MBR using `grub-install`.
    *   `install_legacy_pc_bootloader_grub_config()`: Creates a simple `grub.cfg` to chainload Windows' `bootmgr`.

14. **Workaround for Buggy Motherboards (if `workaround_bios_boot_flag` is True):**
    *   `workaround.buggy_motherboards_that_ignore_disks_without_boot_flag_toggled()`: Toggles the boot flag on the target partition using `parted`.

15. **Return Status:** Returns 0 for success, 1 for failure.

## 3. Helper and Utility Functions within `core.py`

*   **`setup_arguments()`:** Parses CLI arguments using `argparse`.
*   **`mount_source_filesystem()`, `mount_target_filesystem()`:** Wrapper functions for mounting.
*   **`copy_filesystem_files()`, `copy_large_file()`:** Handle file copying with progress.
*   **`setup_linux_persistence()`, `detect_linux_distribution()`, `setup_btrfs_persistence()`, `setup_f2fs_persistence()`:** Logic for Linux ISO persistence (less relevant for Windows ISOs but present).
*   **`install_legacy_pc_bootloader_grub()`, `install_legacy_pc_bootloader_grub_config()`:** GRUB installation specifics.
*   **`cleanup_mountpoint()`, `cleanup()`:** Unmounting and temporary file removal.
*   **`ReportCopyProgress(threading.Thread)`:** Class for threaded progress reporting during file copy.
*   **`create_parser()`:** Creates the argparse parser instance (used by `setup_arguments`).
*   **`main(args, temp_dir)` (Newer version):**
    *   This function is distinct from the one described above.
    *   It's called by `run()` if `args.install_mode == "multiboot"`.
    *   It imports `WowUSB.multiboot` and calls `multiboot.create_multiboot_usb()`.
    *   It also seems to be intended as a refactored entry point for single OS creation if `run()` were updated, as it handles `args.persistence` more directly.

## 4. Key Data Structures (Conceptual)

*   **`args` (Namespace):** From `argparse`, holds all CLI options and positional arguments.
*   **Mount points (strings):** Paths like `/media/wowusbeds9_source_...`, `/tmp/WowUSB.XXXXXX`.
*   **Device paths (strings):** `/dev/sdb`, `/dev/sdb1`.
*   **Filesystem handler objects:** Instances of classes from `filesystem_handlers.py`.

## 5. External Interactions

*   **`WowUSB.utils`:** Heavily used for system commands, checks, printing.
*   **`WowUSB.filesystem_handlers`:** For all filesystem-specific operations.
*   **`WowUSB.workaround`:** For applying specific fixes.
*   **`WowUSB.multiboot`:** If multiboot mode is active (via the newer `main` function).
*   **OS Commands:** `mount`, `umount`, `mkdir`, `parted`, `mkfs.*`, `grub-install`, `dd`, `lsblk`, etc. (many called via `subprocess` in `utils.py`).

## 6. Current State & Potential Refinements

*   The presence of two `main` functions and the way `init` is structured for both CLI and GUI suggests that the module has evolved and might benefit from some refactoring to clarify the control flow for single OS vs. multi-boot OS creation, and how parameters are passed from CLI/GUI through `init` to the respective `main` processing logic.
*   The older `main` function is very long and could be broken down into smaller, more manageable sub-functions.
*   Error handling is generally done by printing a message and returning 1, with `core.run()` catching exceptions.

Despite these points, `core.py` centralizes the complex logic of USB creation effectively.
```
