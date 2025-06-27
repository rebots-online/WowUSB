#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Partitioning utilities for WowUSB-DS9.
Handles creation of GPT partition layouts for multiboot USB drives.
"""

import subprocess
import shutil
import os
import time
import WowUSB.utils as utils
import WowUSB.filesystem_handlers as fs_handlers
from WowUSB.miscellaneous import i18n as _

MIN_WIN_TO_GO_SIZE_GB = 64 # Minimum recommended size for Windows-To-Go

def check_tool_availability(tool_name):
    """Checks if a command-line tool is available in PATH."""
    return shutil.which(tool_name) is not None

def get_partition_uuid(partition_device):
    """Gets the PARTUUID of a partition."""
    try:
        result = subprocess.run(
            ["blkid", "-s", "PARTUUID", "-o", "value", partition_device],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        utils.print_with_color(_("Error getting PARTUUID for {0}: {1}").format(partition_device, e.stderr), "red")
        return None
    except FileNotFoundError:
        utils.print_with_color(_("Error: blkid command not found. Cannot get PARTUUID."), "red")
        return None


def create_multiboot_partition_layout(target_device, win_to_go_size_gb=None, payload_fs_type="F2FS"):
    """
    Creates a GPT partition layout for multiboot USB.

    Args:
        target_device (str): The target block device (e.g., /dev/sdX).
        win_to_go_size_gb (int, optional): Size for the Windows-To-Go partition in GB.
                                           Defaults to MIN_WIN_TO_GO_SIZE_GB if not provided or too small.
        payload_fs_type (str): Filesystem type for the payload/data partition.

    Returns:
        dict: A dictionary containing paths to the created partitions
              (e.g., {'efi': '/dev/sdX1', 'bios_grub': '/dev/sdX2', ...})
              or None if creation fails.
    """
    utils.print_with_color(_("Starting multiboot partition layout creation on {0}").format(target_device), "blue")

    if not os.path.exists(target_device):
        utils.print_with_color(_("Error: Target device {0} does not exist.").format(target_device), "red")
        return None

    # Ensure Win-To-Go size is adequate
    if win_to_go_size_gb is None or win_to_go_size_gb < MIN_WIN_TO_GO_SIZE_GB:
        utils.print_with_color(
            _("Windows-To-Go size not specified or too small ({0}GB). Defaulting to {1}GB.")
            .format(win_to_go_size_gb, MIN_WIN_TO_GO_SIZE_GB), "yellow"
        )
        win_to_go_size_gb = MIN_WIN_TO_GO_SIZE_GB

    # Prefer sgdisk if available, fallback to parted
    use_sgdisk = check_tool_availability("sgdisk")
    use_parted = check_tool_availability("parted")

    if not use_sgdisk and not use_parted:
        utils.print_with_color(_("Error: Neither sgdisk nor parted found. Cannot create partitions."), "red")
        return None

    # --- 1. Wipe existing signatures and create a new GPT ---
    utils.print_with_color(_("Wiping existing signatures and creating new GPT on {0}...").format(target_device), "blue")
    if utils.run_command(["wipefs", "--all", "--force", target_device],
                         message=_("Wiping filesystem signatures from {0}").format(target_device),
                         error_message=_("Failed to wipe signatures from {0}").format(target_device)):
        return None

    time.sleep(1) # Give kernel time to recognize changes

    if use_sgdisk:
        if utils.run_command(["sgdisk", "--zap-all", target_device],
                             message=_("Zapping all GPT structures on {0} with sgdisk").format(target_device),
                             error_message=_("sgdisk failed to zap all structures on {0}").format(target_device)):
            return None
        if utils.run_command(["sgdisk", "--clear", target_device], # Ensure MBR is also cleared
                             message=_("Clearing partition table on {0} with sgdisk").format(target_device),
                             error_message=_("sgdisk failed to clear partition table on {0}").format(target_device)):
            return None
    else: # use_parted
        if utils.run_command(["parted", "--script", target_device, "mklabel", "gpt"],
                             message=_("Creating GPT partition table on {0} with parted").format(target_device),
                             error_message=_("parted failed to create GPT on {0}").format(target_device)):
            return None

    time.sleep(2) # Give kernel time to recognize new partition table

    partition_paths = {}
    current_partition_number = 1

    # --- 2. Create EFI System Partition (ESP) ---
    # Size: 512MiB, Type: FAT32
    esp_size_mib = 512
    esp_start_mib = 1 # Standard 1MiB offset for alignment
    esp_end_mib = esp_start_mib + esp_size_mib
    esp_partition_device = f"{target_device}{current_partition_number}"
    partition_paths['efi'] = esp_partition_device

    utils.print_with_color(_("Creating EFI System Partition ({0}, {1}MiB)...").format(esp_partition_device, esp_size_mib), "blue")
    if use_sgdisk:
        # sgdisk: n=<partnum>:start_sector:end_sector[:typecode[:name]]
        # sgdisk uses sectors, parted uses MiB/GiB etc.
        # Assuming 512 byte sectors for sgdisk calculations.
        # Start: 1MiB = 2048 sectors. End: 1MiB + 512MiB = 513MiB = 1050624 sectors
        cmd = [
            "sgdisk", target_device,
            f"--new={current_partition_number}:{esp_start_mib}M:+{esp_size_mib}M", # sgdisk understands M for MiB
            f"--typecode={current_partition_number}:EF00", # EF00 is ESP type
            f"--change-name={current_partition_number}:EFI System Partition"
        ]
    else: # use_parted
        cmd = [
            "parted", "--script", target_device,
            "mkpart", "'EFI System Partition'", "fat32", f"{esp_start_mib}MiB", f"{esp_end_mib}MiB",
            "set", str(current_partition_number), "esp", "on",
            "set", str(current_partition_number), "boot", "on" # 'boot' flag for ESP is often redundant with 'esp' but some older systems might like it
        ]

    if utils.run_command(cmd, error_message=_("Failed to create EFI System Partition.")): return None
    current_partition_number += 1
    time.sleep(1)

    # --- 3. Create BIOS Boot Partition (bios_grub) ---
    # Size: 1MiB
    bios_grub_size_mib = 1
    bios_grub_start_mib = esp_end_mib
    bios_grub_end_mib = bios_grub_start_mib + bios_grub_size_mib
    bios_grub_partition_device = f"{target_device}{current_partition_number}"
    partition_paths['bios_grub'] = bios_grub_partition_device

    utils.print_with_color(_("Creating BIOS Boot Partition ({0}, {1}MiB)...").format(bios_grub_partition_device, bios_grub_size_mib), "blue")
    if use_sgdisk:
        cmd = [
            "sgdisk", target_device,
            f"--new={current_partition_number}:{bios_grub_start_mib}M:+{bios_grub_size_mib}M",
            f"--typecode={current_partition_number}:EF02", # EF02 is BIOS boot partition type
            f"--change-name={current_partition_number}:BIOS boot"
        ]
    else: # use_parted
        cmd = [
            "parted", "--script", target_device,
            "mkpart", "'BIOS boot partition'", f"{bios_grub_start_mib}MiB", f"{bios_grub_end_mib}MiB",
            "set", str(current_partition_number), "bios_grub", "on"
        ]

    if utils.run_command(cmd, error_message=_("Failed to create BIOS Boot Partition.")): return None
    current_partition_number += 1
    time.sleep(1)

    # --- 4. Create Windows-To-Go Partition ---
    # Size: user-specified (win_to_go_size_gb), Type: NTFS
    win_start_mib = bios_grub_end_mib
    win_end_mib = win_start_mib + (win_to_go_size_gb * 1024) # Convert GB to MiB
    win_partition_device = f"{target_device}{current_partition_number}"
    partition_paths['win_to_go'] = win_partition_device

    utils.print_with_color(_("Creating Windows-To-Go Partition ({0}, {1}GB)...").format(win_partition_device, win_to_go_size_gb), "blue")
    if use_sgdisk:
        cmd = [
            "sgdisk", target_device,
            f"--new={current_partition_number}:{win_start_mib}M:+{win_to_go_size_gb}G", # sgdisk understands G for GiB
            f"--typecode={current_partition_number}:0700", # 0700 is Microsoft basic data
            f"--change-name={current_partition_number}:Windows-To-Go"
        ]
    else: # use_parted
        # parted needs fs type for mkpart, even if not formatting here
        # We'll use 'ntfs' as the intended type. Formatting happens later.
        cmd = [
            "parted", "--script", target_device,
            "mkpart", "'Windows-To-Go'", "ntfs", f"{win_start_mib}MiB", f"{win_end_mib}MiB"
            # No specific flags needed for a standard data partition with parted beyond type
        ]

    if utils.run_command(cmd, error_message=_("Failed to create Windows-To-Go Partition.")): return None
    current_partition_number += 1
    time.sleep(1)

    # --- 5. Create Payload/Data Partition ---
    # Size: Remaining space, Type: payload_fs_type (default F2FS)
    payload_start_mib = win_end_mib
    # For payload, use "100%" to take remaining space
    payload_partition_device = f"{target_device}{current_partition_number}"
    partition_paths['payload'] = payload_partition_device

    utils.print_with_color(_("Creating Payload/Data Partition ({0}, {1}, Remaining Space)...").format(payload_partition_device, payload_fs_type), "blue")

    payload_fs_handler = fs_handlers.get_filesystem_handler(payload_fs_type)
    parted_payload_fs_str = payload_fs_handler.parted_fs_type() # e.g. 'ext4' for F2FS, 'btrfs' for BTRFS

    if use_sgdisk:
        # For sgdisk, start sector is specific, end sector 0 means "to the end of the disk"
        cmd = [
            "sgdisk", target_device,
            f"--new={current_partition_number}:{payload_start_mib}M:0", # 0 for end means use all remaining space
            f"--typecode={current_partition_number}:0700", # Default to Microsoft basic data, actual fs type determined by mkfs
            # Or use Linux filesystem type 8300 if payload_fs_type is Linux-native
            # For simplicity, 0700 is fine as mkfs defines the actual FS.
            # However, for F2FS/BTRFS, 8300 (Linux filesystem) is more appropriate.
            # Let's adjust typecode based on payload_fs_type
            # (This is mostly for OSes that inspect type codes, GRUB usually uses UUID/label)
            f"--typecode={current_partition_number}:{'8300' if payload_fs_type in ['F2FS', 'BTRFS', 'EXT4'] else '0700'}",
            f"--change-name={current_partition_number}:PayloadData"
        ]
    else: # use_parted
        cmd = [
            "parted", "--script", target_device,
            "mkpart", "'PayloadData'", parted_payload_fs_str, f"{payload_start_mib}MiB", "100%"
        ]

    if utils.run_command(cmd, error_message=_("Failed to create Payload/Data Partition.")): return None
    time.sleep(2) # More time for the last partition

    # --- 6. Format Partitions ---
    utils.print_with_color(_("Formatting partitions..."), "blue")

    # Format ESP as FAT32
    if fs_handlers.FatFilesystemHandler.format_partition(esp_partition_device, "ESP"):
        utils.print_with_color(_("Failed to format EFI System Partition {0}.").format(esp_partition_device), "red")
        return None

    # BIOS Boot partition does not need formatting. GRUB installs raw data there.

    # Format Win-To-Go as NTFS
    if fs_handlers.NtfsFilesystemHandler.format_partition(win_partition_device, "WINTOUSB"):
        utils.print_with_color(_("Failed to format Windows-To-Go partition {0}.").format(win_partition_device), "red")
        return None

    # Format Payload/Data partition
    if payload_fs_handler.format_partition(payload_partition_device, "PAYLOAD"):
        utils.print_with_color(_("Failed to format Payload/Data partition {0} as {1}.").format(payload_partition_device, payload_fs_type), "red")
        return None

    utils.print_with_color(_("Partitioning and formatting completed successfully."), "green")

    # Retrieve PARTUUIDs for GRUB configuration
    for name, device_path in partition_paths.items():
        if name not in ['bios_grub']: # bios_grub won't have a filesystem UUID
            uuid = get_partition_uuid(device_path)
            if uuid:
                partition_paths[name + '_uuid'] = uuid
            else:
                utils.print_with_color(_("Warning: Could not retrieve PARTUUID for {0} ({1})").format(name, device_path), "yellow")
                partition_paths[name + '_uuid'] = None # Explicitly set to None if retrieval fails


    return partition_paths

if __name__ == '__main__':
    # Example Usage (for testing purposes, requires root and a spare block device like /dev/sdd)
    # Be very careful with the target_device!
    if os.geteuid() != 0:
        print("This script needs to be run as root for partitioning.")
    else:
        # List available devices to help the user choose
        try:
            print("Available block devices (be careful!):")
            subprocess.run(["lsblk", "-dno", "NAME,SIZE,MODEL"], check=True)
            target = input("Enter target device (e.g., /dev/sdX): ")
            if not target.startswith("/dev/"):
                print("Invalid device path.")
            else:
                confirm = input(f"ARE YOU SURE you want to partition {target}? This will WIPE the device. (yes/no): ")
                if confirm.lower() == 'yes':
                    # Check for dependencies
                    if not check_tool_availability("sgdisk") and not check_tool_availability("parted"):
                        print("Error: sgdisk or parted is required.")
                    elif not check_tool_availability("wipefs"):
                        print("Error: wipefs is required.")
                    elif not fs_handlers.FatFilesystemHandler.check_dependencies()[0]:
                        print("Error: dosfstools (for mkfs.fat) is required.")
                    elif not fs_handlers.NtfsFilesystemHandler.check_dependencies()[0]:
                        print("Error: ntfs-3g (for mkfs.ntfs) is required.")
                    elif not fs_handlers.F2fsFilesystemHandler.check_dependencies()[0]:
                        print("Error: f2fs-tools (for mkfs.f2fs) is required.")
                    else:
                        paths = create_multiboot_partition_layout(target, win_to_go_size_gb=64, payload_fs_type="F2FS")
                        if paths:
                            print("Partition layout created successfully:")
                            for name, path_or_uuid in paths.items():
                                print(f"  {name}: {path_or_uuid}")
                            print("\nVerifying with lsblk:")
                            subprocess.run(["lsblk", target], check=True)
                            print("\nVerifying with sgdisk (if available):")
                            if check_tool_availability("sgdisk"):
                                subprocess.run(["sgdisk", "-p", target], check=True)
                            elif check_tool_availability("parted"):
                                subprocess.run(["parted", target, "print"], check=True)

                        else:
                            print("Partition layout creation failed.")
                else:
                    print("Operation cancelled.")
        except Exception as e:
            print(f"An error occurred: {e}")
