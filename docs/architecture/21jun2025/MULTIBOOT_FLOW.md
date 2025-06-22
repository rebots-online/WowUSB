# WowUSB-DS9: Multiboot Flow (`WowUSB/multiboot.py`)

This document outlines the conceptual control flow and component interaction when WowUSB-DS9 is used to create a multi-boot USB drive. This functionality is primarily managed by the `WowUSB/multiboot.py` module, orchestrated by `WowUSB.core.main(args, temp_dir)`.

## 1. Entry and Orchestration

*   **CLI Trigger:** The user specifies `--multiboot` along with `--add-os` parameters via the `woeusb` command line.
*   **`WowUSB.core.setup_arguments()`:** Parses these arguments, setting `args.install_mode = "multiboot"` and populating `args.add_os` (list of OS configurations) and shared partition details.
*   **`WowUSB.core.run()`:** Detects `args.install_mode == "multiboot"`.
*   **`WowUSB.core.main(args, temp_dir)` (Newer Version):** This specific `main` function is invoked.
    *   It imports `WowUSB.multiboot`.
    *   It performs initial validation of multiboot parameters (target device specified, at least one OS added).
    *   It prepares `os_configs` (a list of dictionaries, each detailing an OS to install: type, name, ISO path, size, filesystem) and shared partition parameters.
    *   It calls `WowUSB.multiboot.create_multiboot_usb(...)`.

## 2. `WowUSB.multiboot.create_multiboot_usb()`

This is the main function within `multiboot.py` that handles the entire multi-boot creation process.

```mermaid
graph TD
    Start[Start create_multiboot_usb] --> A{Validate Inputs};
    A -- Invalid --> ExitFail[Exit with Error];
    A -- Valid --> B[Wipe Target Device Signatures];
    B --> C[Unmount All Partitions on Target];
    C --> D[Create GPT Partition Table];
    D --> E[Calculate Partition Layout];
    subgraph PartitionCreationLoop [For each OS in os_configs + Shared Partition]
        direction LR
        F[Define OS/Shared Partition] --> G[Add Partition using Parted];
        G --> H{Error?};
        H -- Yes --> ExitFail;
        H -- No --> I[Store Partition Path];
    end
    E --> F;
    I --> J[Create and Mount ESP Partition];
    J --> K[Install Main GRUB to ESP];

    subgraph OSInstallationLoop [For each OS in os_configs]
        direction LR
        L[Get OS Config: ISO, Target Partition, FS] --> M[Format OS Partition (using fs_handler)];
        M --> N[Mount OS Partition];
        N --> O[Mount OS ISO];
        O --> P[Copy Files from ISO to OS Partition];
        P --> Q[Install OS-Specific Bootloader/Chainloader Config];
        Q --> R[Unmount OS ISO];
        R --> S[Unmount OS Partition];
    end
    K --> L;
    S --> T[Format Shared Partition (if any)];
    T --> U[Generate Main GRUB Config (grub.cfg on ESP)];
    U --> V[Unmount ESP];
    V --> W[Finalize, Print Success];
    W --> ExitSuccess[Exit with Success];

    ExitFail --> Cleanup;
    ExitSuccess --> Cleanup;
    Cleanup --> End;
```

**Detailed Steps within `create_multiboot_usb()`:**

1.  **Input Validation:**
    *   Ensures `target_device` is valid and accessible.
    *   Ensures `os_configs` is not empty.
    *   Validates individual OS configurations (ISO paths exist, sizes are reasonable, filesystems are supported).
    *   Validates shared partition configuration.

2.  **Target Device Preparation:**
    *   **Wipe Signatures:** Similar to single-OS mode, existing filesystem and partition table signatures on the `target_device` are wiped (e.g., using `wipefs` or `dd`).
    *   **Unmount:** Ensure all partitions on the target device are unmounted.
    *   **Create GPT:** A new GPT (GUID Partition Table) is created on the `target_device`. GPT is preferred for multi-boot and modern systems.

3.  **Partition Layout Calculation & Creation:**
    *   **ESP (EFI System Partition):** A dedicated ESP partition (e.g., 500MB, FAT32) is planned. This will host the main GRUB bootloader.
    *   **OS Partitions:** For each OS in `os_configs`:
        *   A partition is allocated based on `requested_size_mb` and `filesystem`.
    *   **Shared Data Partition:** If `shared_size_mb` > 0, a partition is allocated for shared data with the specified `shared_filesystem`.
    *   **Order & Alignment:** Partitions are created in a specific order, ensuring proper alignment. `parted` is used for creating these partitions.
    *   The paths to the created partitions (e.g., `/dev/sdb1`, `/dev/sdb2`, etc.) are stored.

4.  **ESP Setup & Main GRUB Installation:**
    *   The ESP partition is formatted as FAT32.
    *   It's mounted temporarily.
    *   GRUB (for EFI systems, e.g., `grub-install --target=x86_64-efi --efi-directory=<ESP_mount> --bootloader-id=WowUSBMultiboot ...`) is installed to the ESP. This GRUB will be the primary boot manager.

5.  **OS Installation Loop (for each OS in `os_configs`):**
    *   **Get OS Details:** Retrieve the ISO path, target partition path (e.g., `/dev/sdb2`), and filesystem type for the current OS.
    *   **Format OS Partition:**
        *   The target OS partition is formatted using the specified filesystem (e.g., NTFS for Windows, EXT4/F2FS for Linux). This involves getting the appropriate `filesystem_handler` from `WowUSB.filesystem_handlers` and calling its format method.
    *   **Mount OS Partition:** The newly formatted OS partition is mounted temporarily.
    *   **Mount OS ISO:** The ISO image for the current OS is loop-mounted (read-only).
    *   **Copy Files:** All files are copied from the mounted ISO to the mounted OS partition. This uses similar logic to `core.copy_filesystem_files`, potentially with progress reporting.
    *   **Install OS-Specific Bootloader/Chainloader Config:**
        *   **For Windows:**
            *   Necessary UEFI boot files (`bootmgfw.efi`, BCD store) are copied from the Windows installation files (within the OS partition) to a standard location within that *same* OS partition's `EFI/Microsoft/Boot/` directory if the partition is FAT32/NTFS and intended to be chainloaded directly by GRUB.
            *   Alternatively, if the Windows partition is NTFS, and the main GRUB on ESP has an NTFS driver, GRUB can be configured to chainload `bootmgfw.efi` directly from the NTFS partition.
            *   If Windows is installed in legacy mode (unlikely for a new GPT multiboot setup, but if supported), GRUB would chainload `bootmgr`.
        *   **For Linux:**
            *   A simple GRUB configuration snippet or a symlink might be placed, or the main GRUB on ESP will be configured to directly boot the kernel and initrd from this Linux partition. Some Linux distributions might try to install their own GRUB into their partition's boot sector, which is usually ignored by the main GRUB on ESP unless explicitly chainloaded.
    *   **Unmount ISO and OS Partition.**

6.  **Shared Partition Setup:**
    *   If a shared data partition was created, it's formatted with its specified filesystem (e.g., exFAT, NTFS).

7.  **Generate Main GRUB Configuration (`grub.cfg` on ESP):**
    *   A `grub.cfg` file is generated and written to the ESP (e.g., at `ESP_mount/EFI/WowUSBMultiboot/grub.cfg`).
    *   This `grub.cfg` will contain menu entries for each installed OS.
        *   **Windows entries:** Configured to chainload the Windows Boot Manager (`bootmgfw.efi`) from its respective OS partition (or its `EFI/Microsoft/Boot/` path).
        *   **Linux entries:** Configured to load the kernel and initramfs from their respective OS partitions, along with necessary kernel parameters.
    *   This step requires knowledge of where each OS places its boot files and how to configure GRUB to boot them. UUIDs are typically used to identify partitions in `grub.cfg` for robustness.

8.  **Unmount ESP.**

9.  **Finalization:**
    *   Print success messages.
    *   Return status code (0 for success).

## 6. Interactions with Other Modules

*   **`WowUSB.core`:** Calls `multiboot.create_multiboot_usb()` and provides initial parameters.
*   **`WowUSB.utils`:** Heavily used by `multiboot.py` for:
    *   Running system commands (`parted`, `mkfs.*`, `grub-install`, `mount`, `umount`, `wipefs`).
    *   Device and partition information.
    *   File/directory operations.
*   **`WowUSB.filesystem_handlers`:** Used to get handlers for formatting each OS partition and the shared partition according to their specified filesystems.
*   **`WowUSB.bootloader` (or embedded logic):** Logic for installing GRUB to ESP and generating the `grub.cfg` content.

## 7. Key Challenges & Considerations

*   **Robust GRUB Configuration:** Generating correct `grub.cfg` entries that can boot various Windows and Linux versions from different filesystems is complex.
*   **UEFI vs. Legacy:** This flow primarily targets UEFI booting via GPT and GRUB on ESP. Supporting legacy MBR multi-boot would require a different approach for bootloader installation.
*   **Secure Boot:** The installed GRUB and chainloaded OSes might need to be signed or Secure Boot might need to be disabled on the target machine. This is not explicitly handled by WowUSB but is an external factor.
*   **Filesystem Drivers in GRUB:** GRUB needs to be able to read the filesystems of the OS partitions it's trying to boot (e.g., NTFS driver for Windows partitions, ext4 driver for Linux partitions). These drivers are typically built into the GRUB EFI executable.
*   **Error Handling & Rollback:** If any step fails (e.g., formatting a partition, copying files for one OS), the process should ideally stop and provide clear error messages. Full rollback is very complex.

The `multiboot.py` module encapsulates significant complexity to provide a streamlined multi-OS USB creation experience.
```
