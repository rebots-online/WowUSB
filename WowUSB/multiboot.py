#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Multi-Boot Foundation for WowUSB-DS9
This module provides functionality for creating multi-boot USB drives.
"""

import os
import sys
import subprocess
import tempfile
import uuid
import shutil
from typing import List, Dict, Optional, Tuple, Any

# Import WowUSB modules
import WowUSB.utils as utils
import WowUSB.filesystem_handlers as fs_handlers
import WowUSB.miscellaneous as miscellaneous # Added for i18n

# Internationalization
_ = miscellaneous.i18n # Corrected: gettext should come from miscellaneous

class MultiBootManager:
    """Manager for multi-boot functionality"""
    
    def __init__(self, target_device: str, verbose: bool = False):
        """
        Initialize the multi-boot manager
        
        Args:
            target_device (str): Target device path (e.g., /dev/sdX)
            verbose (bool, optional): Enable verbose output
        """
        self.target_device = target_device
        self.verbose = verbose
        self.os_entries = []
        self.efi_partition = None
        self.boot_partition = None
        self.shared_partition = None
        self.temp_mounts = {}
    
    def create_partition_layout(self, 
                              partition_table: str = "gpt", 
                              efi_size_mb: int = 200,
                              boot_size_mb: int = 200,
                              shared_size_mb: int = 4096,
                              shared_filesystem: str = "EXFAT") -> int:
        """
        Create partition layout for multi-boot
        
        Args:
            partition_table (str): Partition table type (gpt or mbr)
            efi_size_mb (int): Size of EFI partition in MB
            boot_size_mb (int): Size of boot partition in MB
            shared_size_mb (int): Size of shared data partition in MB
            shared_filesystem (str): Filesystem type for shared partition
            
        Returns:
            int: 0 on success, non-zero on failure
        """
        utils.print_with_color(_("Creating partition layout for multi-boot..."), "green")
        
        # Wipe existing partition table
        utils.print_with_color(_("Wiping existing partition table..."), "green" if self.verbose else None)
        result = subprocess.run(["wipefs", "--all", self.target_device], capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Failed to wipe partition table"), "red")
            utils.print_with_color(result.stderr, "red")
            return 1
        
        # Create partition table
        utils.print_with_color(_("Creating {} partition table...").format(partition_table.upper()), 
                             "green" if self.verbose else None)
        result = subprocess.run(["parted", "--script", self.target_device, "mklabel", partition_table], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Failed to create partition table"), "red")
            utils.print_with_color(result.stderr, "red")
            return 1
        
        # Calculate partition sizes and offsets
        current_offset_mb = 1  # Start at 1MB for alignment
        
        if partition_table == "gpt":
            # GPT partition layout
            
            # Create EFI partition
            utils.print_with_color(_("Creating EFI partition..."), "green" if self.verbose else None)
            result = subprocess.run([
                "parted", "--script", self.target_device,
                "mkpart", "ESP", "fat32", f"{current_offset_mb}MiB", f"{current_offset_mb + efi_size_mb}MiB",
                "set", "1", "boot", "on",
                "set", "1", "esp", "on"
            ], capture_output=True, text=True)
            if result.returncode != 0:
                utils.print_with_color(_("Error: Failed to create EFI partition"), "red")
                utils.print_with_color(result.stderr, "red")
                return 1
            
            self.efi_partition = f"{self.target_device}1"
            current_offset_mb += efi_size_mb
            
            # Create boot partition
            utils.print_with_color(_("Creating boot partition..."), "green" if self.verbose else None)
            result = subprocess.run([
                "parted", "--script", self.target_device,
                "mkpart", "BOOT", "fat32", f"{current_offset_mb}MiB", f"{current_offset_mb + boot_size_mb}MiB"
            ], capture_output=True, text=True)
            if result.returncode != 0:
                utils.print_with_color(_("Error: Failed to create boot partition"), "red")
                utils.print_with_color(result.stderr, "red")
                return 1
            
            self.boot_partition = f"{self.target_device}2"
            current_offset_mb += boot_size_mb
            
            # Create shared data partition
            utils.print_with_color(_("Creating shared data partition..."), "green" if self.verbose else None)
            result = subprocess.run([
                "parted", "--script", self.target_device,
                "mkpart", "SHARED", f"{current_offset_mb}MiB", f"{current_offset_mb + shared_size_mb}MiB"
            ], capture_output=True, text=True)
            if result.returncode != 0:
                utils.print_with_color(_("Error: Failed to create shared data partition"), "red")
                utils.print_with_color(result.stderr, "red")
                return 1
            
            self.shared_partition = f"{self.target_device}3"
            current_offset_mb += shared_size_mb
            
        else:
            # MBR partition layout
            
            # Create boot partition
            utils.print_with_color(_("Creating boot partition..."), "green" if self.verbose else None)
            result = subprocess.run([
                "parted", "--script", self.target_device,
                "mkpart", "primary", "fat32", f"{current_offset_mb}MiB", f"{current_offset_mb + boot_size_mb}MiB",
                "set", "1", "boot", "on"
            ], capture_output=True, text=True)
            if result.returncode != 0:
                utils.print_with_color(_("Error: Failed to create boot partition"), "red")
                utils.print_with_color(result.stderr, "red")
                return 1
            
            self.boot_partition = f"{self.target_device}1"
            current_offset_mb += boot_size_mb
            
            # Create shared data partition
            utils.print_with_color(_("Creating shared data partition..."), "green" if self.verbose else None)
            result = subprocess.run([
                "parted", "--script", self.target_device,
                "mkpart", "primary", f"{current_offset_mb}MiB", f"{current_offset_mb + shared_size_mb}MiB"
            ], capture_output=True, text=True)
            if result.returncode != 0:
                utils.print_with_color(_("Error: Failed to create shared data partition"), "red")
                utils.print_with_color(result.stderr, "red")
                return 1
            
            self.shared_partition = f"{self.target_device}2"
            current_offset_mb += shared_size_mb
        
        # Format partitions
        
        # Format EFI partition (if exists)
        if self.efi_partition:
            utils.print_with_color(_("Formatting EFI partition..."), "green" if self.verbose else None)
            result = subprocess.run(["mkfs.fat", "-F", "32", "-n", "ESP", self.efi_partition], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                utils.print_with_color(_("Error: Failed to format EFI partition"), "red")
                utils.print_with_color(result.stderr, "red")
                return 1
        
        # Format boot partition
        utils.print_with_color(_("Formatting boot partition..."), "green" if self.verbose else None)
        result = subprocess.run(["mkfs.fat", "-F", "32", "-n", "BOOT", self.boot_partition], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Failed to format boot partition"), "red")
            utils.print_with_color(result.stderr, "red")
            return 1
        
        # Format shared data partition
        utils.print_with_color(_("Formatting shared data partition..."), "green" if self.verbose else None)
        fs_handler = fs_handlers.get_filesystem_handler(shared_filesystem)
        if fs_handler.format_partition(self.shared_partition, "SHARED") != 0:
            utils.print_with_color(_("Error: Failed to format shared data partition"), "red")
            return 1
        
        utils.print_with_color(_("Partition layout created successfully"), "green")
        return 0
    
    def add_os_partition(self, 
                       os_type: str, 
                       size_mb: int, 
                       filesystem: str, 
                       label: str) -> Optional[str]:
        """
        Add a new OS partition
        
        Args:
            os_type (str): OS type (windows or linux)
            size_mb (int): Partition size in MB
            filesystem (str): Filesystem type
            label (str): Partition label
            
        Returns:
            str: Partition path on success, None on failure
        """
        utils.print_with_color(_("Adding {} partition...").format(os_type), "green")
        
        # Get the last partition number
        lsblk_output = subprocess.run(["lsblk", "-no", "NAME", self.target_device], 
                                    capture_output=True, text=True).stdout
        partition_numbers = []
        for line in lsblk_output.splitlines():
            if line.startswith(os.path.basename(self.target_device)) and line != os.path.basename(self.target_device):
                try:
                    partition_numbers.append(int(line.replace(os.path.basename(self.target_device), "")))
                except ValueError:
                    pass
        
        last_partition_number = max(partition_numbers) if partition_numbers else 0
        new_partition_number = last_partition_number + 1
        
        # Calculate partition start and end
        parted_output = subprocess.run(["parted", "--script", self.target_device, "unit", "MB", "print"], 
                                     capture_output=True, text=True).stdout
        
        # Find the end of the last partition
        last_end_mb = 1  # Default start at 1MB
        for line in parted_output.splitlines():
            if str(last_partition_number) in line and "MB" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.endswith("MB"):
                        try:
                            last_end_mb = float(part.replace("MB", ""))
                            break
                        except ValueError:
                            pass
        
        # Create the new partition
        utils.print_with_color(_("Creating partition..."), "green" if self.verbose else None)
        result = subprocess.run([
            "parted", "--script", self.target_device,
            "mkpart", "primary", f"{last_end_mb}MB", f"{last_end_mb + size_mb}MB"
        ], capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Failed to create partition"), "red")
            utils.print_with_color(result.stderr, "red")
            return None
        
        # Set partition type for Windows
        if os_type == "windows":
            result = subprocess.run([
                "parted", "--script", self.target_device,
                "set", str(new_partition_number), "msftdata", "on"
            ], capture_output=True, text=True)
            if result.returncode != 0:
                utils.print_with_color(_("Warning: Failed to set partition type"), "yellow")
        
        # Format the partition
        new_partition = f"{self.target_device}{new_partition_number}"
        utils.print_with_color(_("Formatting partition..."), "green" if self.verbose else None)
        fs_handler = fs_handlers.get_filesystem_handler(filesystem)
        if fs_handler.format_partition(new_partition, label) != 0:
            utils.print_with_color(_("Error: Failed to format partition"), "red")
            return None
        
        utils.print_with_color(_("OS partition added successfully"), "green")
        return new_partition
    
    def install_grub2_bootloader(self) -> int:
        """
        Install GRUB2 bootloader
        
        Returns:
            int: 0 on success, non-zero on failure
        """
        utils.print_with_color(_("Installing GRUB2 bootloader..."), "green")
        
        # Mount boot partition
        boot_mount = tempfile.mkdtemp(prefix="WowUSB_boot.")
        self.temp_mounts["boot"] = boot_mount
        
        utils.print_with_color(_("Mounting boot partition..."), "green" if self.verbose else None)
        result = subprocess.run(["mount", self.boot_partition, boot_mount], capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Failed to mount boot partition"), "red")
            utils.print_with_color(result.stderr, "red")
            return 1
        
        # Create boot directory
        boot_dir = os.path.join(boot_mount, "boot")
        os.makedirs(boot_dir, exist_ok=True)
        
        # Install GRUB2 for Legacy BIOS
        utils.print_with_color(_("Installing GRUB2 for Legacy BIOS..."), "green" if self.verbose else None)
        result = subprocess.run([
            "grub-install",
            "--target=i386-pc",
            f"--boot-directory={boot_dir}",
            "--recheck",
            self.target_device
        ], capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Failed to install GRUB2 for Legacy BIOS"), "red")
            utils.print_with_color(result.stderr, "red")
            return 1
        
        # Install GRUB2 for UEFI if EFI partition exists
        if self.efi_partition:
            # Mount EFI partition
            efi_mount = tempfile.mkdtemp(prefix="WowUSB_efi.")
            self.temp_mounts["efi"] = efi_mount
            
            utils.print_with_color(_("Mounting EFI partition..."), "green" if self.verbose else None)
            result = subprocess.run(["mount", self.efi_partition, efi_mount], capture_output=True, text=True)
            if result.returncode != 0:
                utils.print_with_color(_("Error: Failed to mount EFI partition"), "red")
                utils.print_with_color(result.stderr, "red")
                return 1
            
            utils.print_with_color(_("Installing GRUB2 for UEFI..."), "green" if self.verbose else None)
            result = subprocess.run([
                "grub-install",
                "--target=x86_64-efi",
                f"--boot-directory={boot_dir}",
                f"--efi-directory={efi_mount}",
                "--removable",
                "--recheck"
            ], capture_output=True, text=True)
            if result.returncode != 0:
                utils.print_with_color(_("Error: Failed to install GRUB2 for UEFI"), "red")
                utils.print_with_color(result.stderr, "red")
                return 1
        
        utils.print_with_color(_("GRUB2 bootloader installed successfully"), "green")
        return 0
    
    def add_os_entry(self, 
                   name: str, 
                   os_type: str, 
                   partition: str, 
                   filesystem: str, 
                   **kwargs) -> int:
        """
        Add an OS entry to the boot menu
        
        Args:
            name (str): OS name
            os_type (str): OS type (windows or linux)
            partition (str): Partition path
            filesystem (str): Filesystem type
            **kwargs: Additional OS-specific parameters
            
        Returns:
            int: 0 on success, non-zero on failure
        """
        utils.print_with_color(_("Adding OS entry: {}").format(name), "green")
        
        # Get partition UUID
        blkid_output = subprocess.run(["blkid", "-s", "UUID", "-o", "value", partition], 
                                    capture_output=True, text=True).stdout.strip()
        if not blkid_output:
            utils.print_with_color(_("Error: Failed to get partition UUID"), "red")
            return 1
        
        # Create OS entry
        entry = {
            "name": name,
            "type": os_type,
            "partition": partition,
            "filesystem": filesystem,
            "uuid": blkid_output
        }
        
        # Add OS-specific parameters
        if os_type == "windows":
            entry["wintogo"] = kwargs.get("wintogo", False)
        elif os_type == "linux":
            entry["kernel"] = kwargs.get("kernel", "/boot/vmlinuz")
            entry["initrd"] = kwargs.get("initrd", "/boot/initrd.img")
            entry["kernel_params"] = kwargs.get("kernel_params", f"root=UUID={blkid_output} ro quiet")
        
        # Add entry to list
        self.os_entries.append(entry)
        
        utils.print_with_color(_("OS entry added successfully"), "green")
        return 0
    
    def generate_grub2_config(self) -> int:
        """
        Generate GRUB2 configuration file
        
        Returns:
            int: 0 on success, non-zero on failure
        """
        utils.print_with_color(_("Generating GRUB2 configuration..."), "green")
        
        # Check if boot partition is mounted
        if "boot" not in self.temp_mounts:
            utils.print_with_color(_("Error: Boot partition not mounted"), "red")
            return 1
        
        # Create GRUB2 configuration directory
        grub_dir = os.path.join(self.temp_mounts["boot"], "boot", "grub")
        os.makedirs(grub_dir, exist_ok=True)
        
        # Generate GRUB2 configuration file
        config_path = os.path.join(grub_dir, "grub.cfg")
        utils.print_with_color(_("Writing configuration to {}").format(config_path), "green" if self.verbose else None)
        
        try:
            with open(config_path, "w") as f:
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
                for i, entry in enumerate(self.os_entries):
                    f.write(f"# {entry['name']}\n")
                    
                    if entry['type'] == 'windows':
                        # Windows entry
                        f.write(f"menuentry \"{entry['name']}\" {{\n")
                        f.write("    insmod part_gpt\n")
                        f.write("    insmod ntfs\n")
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
                        
                        # Load appropriate filesystem module
                        if entry['filesystem'] == 'EXT4':
                            f.write("    insmod ext2\n")
                        elif entry['filesystem'] == 'F2FS':
                            f.write("    insmod f2fs\n")
                        elif entry['filesystem'] == 'BTRFS':
                            f.write("    insmod btrfs\n")
                        
                        f.write("    insmod search_fs_uuid\n")
                        f.write(f"    search --fs-uuid --set=root {entry['uuid']}\n")
                        
                        # Set kernel and initrd paths
                        f.write(f"    linux {entry['kernel']} {entry['kernel_params']}\n")
                        f.write(f"    initrd {entry['initrd']}\n")
                        f.write("}\n\n")
        except Exception as e:
            utils.print_with_color(_("Error: Failed to write GRUB2 configuration: {}").format(str(e)), "red")
            return 1
        
        utils.print_with_color(_("GRUB2 configuration generated successfully"), "green")
        return 0
    
    def cleanup(self) -> None:
        """Clean up temporary mounts"""
        utils.print_with_color(_("Cleaning up..."), "green")
        
        for mount_point in self.temp_mounts.values():
            utils.print_with_color(_("Unmounting {}").format(mount_point), "green" if self.verbose else None)
            subprocess.run(["umount", mount_point], stderr=subprocess.DEVNULL)
            os.rmdir(mount_point)
        
        self.temp_mounts = {}

def create_multiboot_usb(target_device: str, 
                       os_configs: List[Dict[str, Any]], 
                       shared_size_mb: int = 4096,
                       shared_filesystem: str = "EXFAT",
                       verbose: bool = False) -> int:
    """
    Create a multi-boot USB drive
    
    Args:
        target_device (str): Target device path (e.g., /dev/sdX)
        os_configs (list): List of OS configuration dictionaries
        shared_size_mb (int, optional): Size of shared data partition in MB
        shared_filesystem (str, optional): Filesystem type for shared partition
        verbose (bool, optional): Enable verbose output
        
    Returns:
        int: 0 on success, non-zero on failure
    """
    utils.print_with_color(_("Creating multi-boot USB drive..."), "green")
    
    # Create multi-boot manager
    mb_manager = MultiBootManager(target_device, verbose)
    
    try:
        # Create partition layout
        if mb_manager.create_partition_layout(
            partition_table="gpt",
            shared_size_mb=shared_size_mb,
            shared_filesystem=shared_filesystem
        ) != 0:
            return 1
        
        # Add OS partitions
        for os_config in os_configs:
            os_type = os_config.get("type", "").lower()
            size_mb = os_config.get("size_mb", 8192)
            filesystem = os_config.get("filesystem", "NTFS" if os_type == "windows" else "EXT4")
            label = os_config.get("label", os_type.upper())
            
            partition = mb_manager.add_os_partition(os_type, size_mb, filesystem, label)
            if not partition:
                return 1
            
            # Install OS to partition
            if os_type == "windows":
                # Install Windows
                iso_path = os_config.get("iso_path", "")
                wintogo = os_config.get("wintogo", False)
                
                if not iso_path:
                    utils.print_with_color(_("Error: Windows ISO path not specified"), "red")
                    return 1
                
                # Mount ISO
                iso_mount = tempfile.mkdtemp(prefix="WowUSB_iso.")
                utils.print_with_color(_("Mounting Windows ISO..."), "green" if verbose else None)
                result = subprocess.run(["mount", "-o", "loop", iso_path, iso_mount], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    utils.print_with_color(_("Error: Failed to mount Windows ISO"), "red")
                    utils.print_with_color(result.stderr, "red")
                    shutil.rmtree(iso_mount)
                    return 1
                
                # Mount target partition
                target_mount = tempfile.mkdtemp(prefix="WowUSB_target.")
                utils.print_with_color(_("Mounting target partition..."), "green" if verbose else None)
                result = subprocess.run(["mount", partition, target_mount], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    utils.print_with_color(_("Error: Failed to mount target partition"), "red")
                    utils.print_with_color(result.stderr, "red")
                    subprocess.run(["umount", iso_mount], stderr=subprocess.DEVNULL)
                    shutil.rmtree(iso_mount)
                    shutil.rmtree(target_mount)
                    return 1
                
                # Copy files
                utils.print_with_color(_("Copying Windows files..."), "green")
                result = subprocess.run(["rsync", "-a", f"{iso_mount}/", target_mount], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    utils.print_with_color(_("Error: Failed to copy Windows files"), "red")
                    utils.print_with_color(result.stderr, "red")
                    subprocess.run(["umount", iso_mount], stderr=subprocess.DEVNULL)
                    subprocess.run(["umount", target_mount], stderr=subprocess.DEVNULL)
                    shutil.rmtree(iso_mount)
                    shutil.rmtree(target_mount)
                    return 1
                
                # Clean up
                utils.print_with_color(_("Unmounting..."), "green" if verbose else None)
                subprocess.run(["umount", iso_mount], stderr=subprocess.DEVNULL)
                subprocess.run(["umount", target_mount], stderr=subprocess.DEVNULL)
                shutil.rmtree(iso_mount)
                shutil.rmtree(target_mount)
                
                # Add OS entry
                mb_manager.add_os_entry(
                    name=os_config.get("name", "Windows"),
                    os_type="windows",
                    partition=partition,
                    filesystem=filesystem,
                    wintogo=wintogo
                )
            
            elif os_type == "linux":
                # Install Linux
                iso_path = os_config.get("iso_path", "")
                
                if not iso_path:
                    utils.print_with_color(_("Error: Linux ISO path not specified"), "red")
                    return 1
                
                # Mount ISO
                iso_mount = tempfile.mkdtemp(prefix="WowUSB_iso.")
                utils.print_with_color(_("Mounting Linux ISO..."), "green" if verbose else None)
                result = subprocess.run(["mount", "-o", "loop", iso_path, iso_mount], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    utils.print_with_color(_("Error: Failed to mount Linux ISO"), "red")
                    utils.print_with_color(result.stderr, "red")
                    shutil.rmtree(iso_mount)
                    return 1
                
                # Mount target partition
                target_mount = tempfile.mkdtemp(prefix="WowUSB_target.")
                utils.print_with_color(_("Mounting target partition..."), "green" if verbose else None)
                result = subprocess.run(["mount", partition, target_mount], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    utils.print_with_color(_("Error: Failed to mount target partition"), "red")
                    utils.print_with_color(result.stderr, "red")
                    subprocess.run(["umount", iso_mount], stderr=subprocess.DEVNULL)
                    shutil.rmtree(iso_mount)
                    shutil.rmtree(target_mount)
                    return 1
                
                # Copy files
                utils.print_with_color(_("Copying Linux files..."), "green")
                result = subprocess.run(["rsync", "-a", f"{iso_mount}/", target_mount], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    utils.print_with_color(_("Error: Failed to copy Linux files"), "red")
                    utils.print_with_color(result.stderr, "red")
                    subprocess.run(["umount", iso_mount], stderr=subprocess.DEVNULL)
                    subprocess.run(["umount", target_mount], stderr=subprocess.DEVNULL)
                    shutil.rmtree(iso_mount)
                    shutil.rmtree(target_mount)
                    return 1
                
                # Detect kernel and initrd
                kernel_path = "/boot/vmlinuz"
                initrd_path = "/boot/initrd.img"
                
                # Ubuntu/Debian
                if os.path.exists(os.path.join(target_mount, "casper")):
                    kernel_files = [f for f in os.listdir(os.path.join(target_mount, "casper")) 
                                  if f.startswith("vmlinuz")]
                    initrd_files = [f for f in os.listdir(os.path.join(target_mount, "casper")) 
                                   if f.startswith("initrd")]
                    
                    if kernel_files:
                        kernel_path = f"/casper/{kernel_files[0]}"
                    if initrd_files:
                        initrd_path = f"/casper/{initrd_files[0]}"
                
                # Fedora
                elif os.path.exists(os.path.join(target_mount, "isolinux")):
                    kernel_files = [f for f in os.listdir(os.path.join(target_mount, "isolinux")) 
                                  if f.startswith("vmlinuz")]
                    initrd_files = [f for f in os.listdir(os.path.join(target_mount, "isolinux")) 
                                   if f.startswith("initrd")]
                    
                    if kernel_files:
                        kernel_path = f"/isolinux/{kernel_files[0]}"
                    if initrd_files:
                        initrd_path = f"/isolinux/{initrd_files[0]}"
                
                # Clean up
                utils.print_with_color(_("Unmounting..."), "green" if verbose else None)
                subprocess.run(["umount", iso_mount], stderr=subprocess.DEVNULL)
                subprocess.run(["umount", target_mount], stderr=subprocess.DEVNULL)
                shutil.rmtree(iso_mount)
                shutil.rmtree(target_mount)
                
                # Add OS entry
                mb_manager.add_os_entry(
                    name=os_config.get("name", "Linux"),
                    os_type="linux",
                    partition=partition,
                    filesystem=filesystem,
                    kernel=kernel_path,
                    initrd=initrd_path,
                    kernel_params=os_config.get("kernel_params", "ro quiet")
                )
        
        # Install GRUB2 bootloader
        if mb_manager.install_grub2_bootloader() != 0:
            return 1
        
        # Generate GRUB2 configuration
        if mb_manager.generate_grub2_config() != 0:
            return 1
        
        utils.print_with_color(_("Multi-boot USB drive created successfully"), "green")
        return 0
    
    finally:
        # Clean up
        mb_manager.cleanup()

def main():
    """Main function"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description=_("Create a multi-boot USB drive"))
    parser.add_argument("--target", "-t", required=True, help=_("Target device (e.g., /dev/sdX)"))
    parser.add_argument("--add-windows", "-w", action="append", nargs=3, metavar=("ISO", "SIZE_GB", "FILESYSTEM"),
                      help=_("Add Windows (ISO path, size in GB, filesystem)"))
    parser.add_argument("--add-linux", "-l", action="append", nargs=3, metavar=("ISO", "SIZE_GB", "FILESYSTEM"),
                      help=_("Add Linux (ISO path, size in GB, filesystem)"))
    parser.add_argument("--shared-size", "-s", type=int, default=4, help=_("Shared partition size in GB"))
    parser.add_argument("--shared-filesystem", "-f", default="EXFAT", help=_("Shared partition filesystem"))
    parser.add_argument("--verbose", "-v", action="store_true", help=_("Enable verbose output"))
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.add_windows and not args.add_linux:
        utils.print_with_color(_("Error: At least one OS must be specified"), "red")
        return 1
    
    # Prepare OS configurations
    os_configs = []
    
    if args.add_windows:
        for i, (iso_path, size_gb, filesystem) in enumerate(args.add_windows):
            os_configs.append({
                "type": "windows",
                "name": f"Windows {i+1}",
                "iso_path": iso_path,
                "size_mb": int(float(size_gb) * 1024),
                "filesystem": filesystem.upper(),
                "wintogo": False
            })
    
    if args.add_linux:
        for i, (iso_path, size_gb, filesystem) in enumerate(args.add_linux):
            os_configs.append({
                "type": "linux",
                "name": f"Linux {i+1}",
                "iso_path": iso_path,
                "size_mb": int(float(size_gb) * 1024),
                "filesystem": filesystem.upper()
            })
    
    # Create multi-boot USB drive
    return create_multiboot_usb(
        target_device=args.target,
        os_configs=os_configs,
        shared_size_mb=args.shared_size * 1024,
        shared_filesystem=args.shared_filesystem.upper(),
        verbose=args.verbose
    )

if __name__ == "__main__":
    sys.exit(main())
