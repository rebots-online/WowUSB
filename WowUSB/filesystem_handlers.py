
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Filesystem handler modules for WowUSB to support multiple filesystem types
including FAT32, NTFS, exFAT, F2FS, and BTRFS.

This module provides a common interface for different filesystem operations
and implementations for each supported filesystem type.
"""

import os
import subprocess
import shutil
import re
import tempfile
from abc import ABC, abstractmethod
import WowUSB.utils as utils
import WowUSB.miscellaneous as miscellaneous

_ = miscellaneous.i18n

class FilesystemHandler(ABC):
    """Abstract base class defining interface for filesystem handlers"""
    
    @classmethod
    @abstractmethod
    def name(cls):
        """Return the name of the filesystem"""
        pass
        
    @classmethod
    @abstractmethod
    def supports_file_size_greater_than_4gb(cls):
        """
        Check if the filesystem supports files larger than 4GB
        
        Returns:
            bool: True if filesystem supports files > 4GB, False otherwise
        """
        pass
        
    @classmethod
    @abstractmethod
    def parted_fs_type(cls):
        """
        Return the filesystem type string to use with parted mkpart command
        
        Returns:
            str: Filesystem type string for parted
        """
        pass
        
    @classmethod
    @abstractmethod
    def format_partition(cls, partition, label):
        """
        Format the partition with this filesystem type
        
        Args:
            partition (str): Partition device path (e.g., /dev/sdX1)
            label (str): Filesystem label to apply
            
        Returns:
            int: 0 on success, non-zero on failure
        """
        pass
        
    @classmethod
    @abstractmethod
    def check_dependencies(cls):
        """
        Check if required dependencies for this filesystem are installed
        
        Returns:
            tuple: (is_available, missing_dependencies)
                is_available (bool): True if all dependencies are available
                missing_dependencies (list): List of missing dependency names
        """
        pass
        
    @classmethod
    def needs_uefi_support_partition(cls):
        """
        Check if this filesystem requires a separate UEFI support partition
        
        Returns:
            bool: True if UEFI support partition is needed, False otherwise
        """
        return False

class FatFilesystemHandler(FilesystemHandler):
    """Handler for FAT/FAT32 filesystem operations"""
    
    @classmethod
    def name(cls):
        return "FAT32"
        
    @classmethod
    def supports_file_size_greater_than_4gb(cls):
        return False
        
    @classmethod
    def parted_fs_type(cls):
        return "fat32"
        
    @classmethod
    def format_partition(cls, partition, label):
        utils.check_kill_signal()
        
        utils.print_with_color(_("Creating FAT/FAT32 filesystem..."), "green")
        
        # Check for command_mkdosfs
        command_mkdosfs = utils.check_command("mkdosfs")
        if not command_mkdosfs:
            utils.print_with_color(_("Error: mkdosfs command not found"), "red")
            return 1
            
        # Format the first partition as FAT32 filesystem
        if subprocess.run([command_mkdosfs,
                          "-F", "32",
                          "-n", label,
                          "-v",
                          partition]).returncode != 0:
            utils.print_with_color(_("Error: Unable to create FAT32 filesystem"), "red")
            return 1
            
        return 0
        
    @classmethod
    def check_dependencies(cls):
        missing = []
        
        # Check for mkdosfs
        if not utils.check_command("mkdosfs"):
            missing.append("dosfstools")
            
        return (len(missing) == 0, missing)

class NtfsFilesystemHandler(FilesystemHandler):
    """Handler for NTFS filesystem operations"""
    
    @classmethod
    def name(cls):
        return "NTFS"
        
    @classmethod
    def supports_file_size_greater_than_4gb(cls):
        return True
        
    @classmethod
    def parted_fs_type(cls):
        return "ntfs"
        
    @classmethod
    def format_partition(cls, partition, label):
        utils.check_kill_signal()
        
        utils.print_with_color(_("Creating NTFS filesystem..."), "green")
        
        # Check for mkntfs command
        command_mkntfs = utils.check_command("mkntfs")
        if not command_mkntfs:
            utils.print_with_color(_("Error: mkntfs command not found"), "red")
            return 1
            
        # Format the partition as NTFS with optimized parameters
        format_cmd = [
            command_mkntfs,
            "-f",  # Fast format
            "-L", label,
            "-v"   # Verbose output
        ]
        
        # Add optimization parameters
        try:
            # Get device type (HDD, SSD, USB Flash)
            device_base = partition.rstrip('0123456789')
            with open(f"/sys/block/{os.path.basename(device_base)}/queue/rotational", 'r') as f:
                is_rotational = int(f.read().strip())
            
            # Add device-specific optimizations
            if not is_rotational:
                # For SSDs and flash drives
                format_cmd.extend([
                    "-c", "4096",  # 4K cluster size for SSDs
                    "-a", "4096"   # 4K alignment for better performance
                ])
            else:
                # For HDDs
                format_cmd.extend([
                    "-c", "16384"  # 16K cluster size for HDDs
                ])
        except (IOError, OSError):
            # Fallback to default options if we can't determine device type
            pass
        
        # Execute the format command
        utils.print_with_color(_("Running: {0}").format(" ".join(format_cmd)), "green" if utils.verbose else None)
        result = subprocess.run(format_cmd + [partition], capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Unable to create NTFS filesystem:"), "red")
            utils.print_with_color(result.stderr, "red")
            return 1
            
        # Validate the newly created filesystem
        if not cls.validate_filesystem(partition):
            return 1
            
        return 0
        
    @classmethod
    def validate_filesystem(cls, partition):
        """
        Validate the NTFS filesystem after creation
        
        This method performs comprehensive validation of the newly created
        NTFS filesystem to ensure it's properly formatted and can handle
        large files.

        Args:
            partition (str): Partition device path (e.g., /dev/sdX1)
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        utils.check_kill_signal()
        
        utils.print_with_color(_("Validating NTFS filesystem..."), "green")
        
        # Find available filesystem check tool
        ntfsck_cmd = utils.check_command("ntfsfix") or utils.check_command("ntfsck")
        if not ntfsck_cmd:
            utils.print_with_color(_("Warning: NTFS filesystem check tools not found, skipping validation"), "yellow")
            return True
            
        # Run basic filesystem check
        utils.print_with_color(_("Performing basic filesystem check..."), "green" if utils.verbose else None)
        
        check_cmd = [ntfsck_cmd]
        if ntfsck_cmd.endswith("ntfsfix"):
            check_cmd.append("-n")  # No write mode for ntfsfix
        
        result = subprocess.run(check_cmd + [partition], capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Filesystem validation failed:"), "red")
            utils.print_with_color(result.stderr, "red")
            return False
            
        # Create a temporary mount point for additional validation
        with tempfile.TemporaryDirectory() as temp_mount:
            try:
                # Mount the filesystem
                utils.print_with_color(_("Mounting filesystem for validation..."), "green" if utils.verbose else None)
                if subprocess.run(["mount", "-t", "ntfs-3g", partition, temp_mount]).returncode != 0:
                    utils.print_with_color(_("Warning: Unable to mount filesystem for validation"), "yellow")
                    return True  # Continue despite warning
                
                # Test large file write capability
                try:
                    utils.print_with_color(_("Testing large file support..."), "green" if utils.verbose else None)
                    large_file_path = os.path.join(temp_mount, "large_file_test")
                    
                    # Create a sparse file of 5GB to test >4GB support
                    with open(large_file_path, 'wb') as f:
                        f.seek(5 * 1024 * 1024 * 1024 - 1)  # 5GB - 1 byte
                        f.write(b'\x00')  # Write a single byte at the end
                    
                    # Verify file size
                    file_size = os.path.getsize(large_file_path)
                    if file_size < 4 * 1024 * 1024 * 1024:
                        utils.print_with_color(
                            _("Warning: Large file test failed. File size: {0}").format(
                                utils.convert_to_human_readable_format(file_size)
                            ), 
                            "yellow"
                        )
                    else:
                        utils.print_with_color(
                            _("Large file test passed. File size: {0}").format(
                                utils.convert_to_human_readable_format(file_size)
                            ), 
                            "green" if utils.verbose else None
                        )
                    
                    # Clean up test file
                    os.unlink(large_file_path)
                    
                except (IOError, OSError) as e:
                    utils.print_with_color(_("Warning: Large file test failed: {0}").format(str(e)), "yellow")
                
                # Unmount the filesystem
                utils.print_with_color(_("Unmounting test filesystem..."), "green" if utils.verbose else None)
                if subprocess.run(["umount", temp_mount]).returncode != 0:
                    utils.print_with_color(_("Warning: Unable to unmount test filesystem"), "yellow")
                    return False
                
            except Exception as e:
                utils.print_with_color(_("Warning: Validation error: {0}").format(str(e)), "yellow")
                # Attempt to unmount the filesystem if it was mounted
                try:
                    subprocess.run(["umount", temp_mount], stderr=subprocess.DEVNULL)
                except:
                    pass  # Ignore errors during cleanup
                return False
                
        utils.print_with_color(_("NTFS filesystem validation completed successfully"), "green")
        return True
        
    @classmethod
    def check_dependencies(cls):
        missing = []
        
        # Check for mkntfs
        if not utils.check_command("mkntfs"):
            missing.append("ntfs-3g")
            
        return (len(missing) == 0, missing)
        
    @classmethod
    def needs_uefi_support_partition(cls):
        """NTFS requires a separate UEFI support partition for UEFI booting"""
        return True
        
    @classmethod
    def get_uefi_bootloader_file(cls):
        """
        Get the appropriate UEFI bootloader file for NTFS.
        
        Returns:
            tuple: (url, filename) where:
                url (str): URL to download the bootloader image
                filename (str): Local filename to save as
        """
        return (
            "https://github.com/pbatard/rufus/raw/master/res/uefi/uefi-ntfs.img",
            "uefi-ntfs.img"
        )

class ExfatFilesystemHandler(FilesystemHandler):
    """Handler for exFAT filesystem operations"""
    
    @classmethod
    def name(cls):
        return "exFAT"
        
    @classmethod
    def supports_file_size_greater_than_4gb(cls):
        return True
        
    @classmethod
    def parted_fs_type(cls):
        # parted doesn't directly support exfat
        # but it can be created after partition creation
        return "fat32"
        
    @classmethod
    def format_partition(cls, partition, label):
        utils.check_kill_signal()
        
        # Recommend optimal settings based on device type
        try:
            # Get device type (HDD, SSD, USB Flash)
            device_base = partition.rstrip('0123456789')
            with open(f"/sys/block/{os.path.basename(device_base)}/queue/rotational", 'r') as f:
                is_rotational = int(f.read().strip())
            
            # Default options for modern SSDs and flash drives
            format_opts = [
                "--sector-size=4096",  # Modern default sector size
                "--volume-label", label,
                "--volume-serial", hex(int.from_bytes(os.urandom(4), 'big'))[2:].upper()
            ]
            
            # Add device-specific optimizations
            if not is_rotational:
                # For SSDs and flash drives
                format_opts.append("--cluster-size=128K")  # Reduce write amplification
                format_opts.append("--alignment=1M")       # Align with flash erase blocks
                
                # Check for USB flash drive vs SSD
                try:
                    with open(f"/sys/block/{os.path.basename(device_base)}/removable", 'r') as f:
                        is_removable = int(f.read().strip())
                    
                    # Additional optimizations for USB flash drives
                    if is_removable:
                        # USB flash drives benefit from these settings
                        format_opts.append("--quick-format")   # Faster formatting for removable media
                        format_opts.append("--sectormap=all")  # Better wear leveling for flash drives
                except (IOError, OSError):
                    # If we can't determine if it's removable, assume it's not
                    pass
            else:
                # For HDDs
                format_opts.append("--cluster-size=32K")   # Better for general HDD use
        except (IOError, OSError):
            # Fallback to basic options if we can't determine device type
            format_opts = [
                "--volume-label", label,
                "--cluster-size=128K"  # Good general-purpose size
            ]
        
        utils.print_with_color(_("Creating exFAT filesystem..."), "green")
        

        # Check for mkexfatfs command (from exfat-utils) or mkfs.exfat (from exfatprogs)
        command_mkexfatfs = utils.check_command("mkexfatfs")
        command_mkfs_exfat = utils.check_command("mkfs.exfat")
        
        # Initialize command_mkexfat to None
        command_mkexfat = None
        
        # Explicitly check each command and assign the path
        if command_mkexfatfs is not None:
            command_mkexfat = command_mkexfatfs
        elif command_mkfs_exfat is not None:
            command_mkexfat = command_mkfs_exfat
        else:
            utils.print_with_color(_("Error: mkexfatfs/mkfs.exfat command not found"), "red")
            return 1
        
        # Format command with optimized options
        cmd = [command_mkexfat] + format_opts + [partition]


        
        try:
            utils.print_with_color(_("Running: {0}").format(" ".join(cmd)), "green" if utils.verbose else None)
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                utils.print_with_color(_("Error: Unable to create exFAT filesystem:"), "red")
                utils.print_with_color(result.stderr, "red")
                return 1
        except subprocess.SubprocessError as e:
            utils.print_with_color(_("Error: Formatting failed: {0}").format(str(e)), "red")
            return 1
            
        # Validate the newly created filesystem
        if not cls.validate_filesystem(partition):
            return 1
            
        return 0
    
    @classmethod
    def needs_uefi_support_partition(cls):
        """exFAT requires a separate UEFI support partition for UEFI booting"""
        return True
    
    @classmethod
    def validate_filesystem(cls, partition):
        """
        Validate the exFAT filesystem after creation
        
        This method performs comprehensive validation of the newly created
        exFAT filesystem to ensure it's properly formatted and can handle
        large files.

        Args:
            partition (str): Partition device path (e.g., /dev/sdX1)
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        utils.check_kill_signal()
        
        utils.print_with_color(_("Validating exFAT filesystem..."), "green")
        
        # Find available filesystem check tool
        fsck_cmd = utils.check_command("fsck.exfat") or utils.check_command("exfatfsck") or utils.check_command("chkexfat")
        if not fsck_cmd:
            utils.print_with_color(_("Warning: exFAT filesystem check tools not found, skipping validation"), "yellow")
            return True
            
        # Run basic filesystem check
        utils.print_with_color(_("Performing basic filesystem check..."), "green" if utils.verbose else None)
        result = subprocess.run([fsck_cmd, "-n", partition], capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Filesystem validation failed:"), "red")
            utils.print_with_color(result.stderr, "red")
            return False
            
        # Create a temporary mount point for additional validation
        with tempfile.TemporaryDirectory() as temp_mount:
            try:
                # Mount the filesystem
                utils.print_with_color(_("Mounting filesystem for validation..."), "green" if utils.verbose else None)

                if subprocess.run(["mount", "-t", "exfat", partition, temp_mount]).returncode != 0:
                    utils.print_with_color(_("Warning: Unable to mount filesystem for validation"), "yellow")
                    return True  # Continue despite warning

                # Verify the mount point exists and is writable
                if not os.path.exists(temp_mount) or not os.access(temp_mount, os.W_OK):
                    utils.print_with_color(
                        _("Warning: Mount point does not exist or is not writable: {0}").format(temp_mount),
                        "yellow"
                    )
                    return True  # Continue despite warning

                # Test large file write capability
                try:
                    utils.print_with_color(_("Testing large file support..."), "green" if utils.verbose else None)
                    large_file_path = os.path.join(temp_mount, "large_file_test")
                    
                    # Create a sparse file of 5GB to test >4GB support
                    with open(large_file_path, 'wb') as f:
                        f.seek(5 * 1024 * 1024 * 1024 - 1)  # 5GB - 1 byte
                        f.write(b'\x00')  # Write a single byte at the end
                    
                    # Verify file size
                    file_size = os.path.getsize(large_file_path)
                    if file_size < 4 * 1024 * 1024 * 1024:
                        utils.print_with_color(
                            _("Warning: Large file test failed. File size: {0}").format(
                                utils.convert_to_human_readable_format(file_size)
                            ), 
                            "yellow"
                        )
                    else:
                        utils.print_with_color(
                            _("Large file test passed. File size: {0}").format(
                                utils.convert_to_human_readable_format(file_size)
                            ), 
                            "green" if utils.verbose else None
                        )
                    
                    # Clean up test file
                    os.unlink(large_file_path)
                    
                except (IOError, OSError) as e:
                    utils.print_with_color(_("Warning: Large file test failed: {0}").format(str(e)), "yellow")
                
                # Unmount the filesystem
                utils.print_with_color(_("Unmounting filesystem for validation..."), "green" if utils.verbose else None)
                if subprocess.run(["umount", temp_mount]).returncode != 0:
                    utils.print_with_color(_("Warning: Unable to unmount test filesystem"), "yellow")
                    return False
                
            except Exception as e:
                utils.print_with_color(_("Warning: Validation error: {0}").format(str(e)), "yellow")
                # Attempt to unmount the filesystem if it was mounted
                try:
                    subprocess.run(["umount", temp_mount], stderr=subprocess.DEVNULL)
                except:
                    pass  # Ignore errors during cleanup
                return False
                
        utils.print_with_color(_("exFAT filesystem validation completed successfully"), "green")
        return True
    
    @classmethod
    def get_uefi_bootloader_file(cls):
        """
        Get the appropriate UEFI bootloader file for exFAT.
        For now, we use UEFI:NTFS as it can handle exFAT with proper drivers.
        
        Returns:
            tuple: (url, filename) where:
                url (str): URL to download the bootloader image
                filename (str): Local filename to save as
        """
        return (
            "https://github.com/pbatard/rufus/raw/master/res/uefi/uefi-ntfs.img",
            "uefi-ntfs.img"
        )
    
    @classmethod
    def create_uefi_support_partition(cls, device):
        """
        Create a UEFI support partition for exFAT boot support
        
        Args:
            device (str): Device path (e.g., /dev/sdX)
            
        Returns:
            bool: True on success, False on failure
        """
        utils.check_kill_signal()
        
        utils.print_with_color(_("Creating UEFI:exFAT support partition..."), "green")
        
        # UEFI boot partition needs to be FAT12/16/32
        subprocess.run([
            "parted",
            "--align", "none",  # Small partition, alignment not critical
            "--script",
            device,
            "mkpart",
            "primary",
            "fat16",  # FAT16 for compatibility
            "--", "-2048s", "-1s"  # Last 1MB for boot support
        ])
        
        return True        
    
    @classmethod
    def check_dependencies(cls):
        """
        Check for required exFAT filesystem tools and their versions
        
        This method checks for both exfatprogs and exfat-utils packages, as different
        distributions may provide one or the other. It also checks tool versions to
        ensure required features are available.
        
        Returns:
            tuple: (is_available, missing_dependencies)
                is_available (bool): True if required tools are available
                missing_dependencies (list): List of missing tools or version requirements
        """
        missing = []
        version_info = {}
        
        # Define required tools and their minimum versions
        REQUIRED_TOOLS = {
            'mkexfatfs': '1.3.0',  # exfat-utils
            'mkfs.exfat': '1.1.0',  # exfatprogs
            'fsck.exfat': '1.1.0',  # For validation
            'exfatlabel': '1.3.0'   # For label management
        }
        
        # Check each required tool
        found_formatter = False
        for tool, min_version in REQUIRED_TOOLS.items():
            if utils.check_command(tool):
                # Get tool version
                try:
                    version_output = subprocess.run(
                        [tool, '--version'],
                        capture_output=True,
                        text=True
                    ).stdout
                    
                    # Extract version number using regex
                    version_match = re.search(r'(\d+\.\d+\.\d+)', version_output)
                    if version_match:
                        version = version_match.group(1)
                        version_info[tool] = version
                        
                        # Compare versions
                        if cls._compare_versions(version, min_version) < 0:
                            missing.append(f"{tool} (found {version}, need {min_version})")
                        elif tool in ['mkexfatfs', 'mkfs.exfat']:
                            found_formatter = True
                            
                except (subprocess.SubprocessError, OSError):
                    missing.append(f"{tool} (version check failed)")
            elif tool not in ['mkexfatfs', 'mkfs.exfat'] or not found_formatter:
                # Only add formatting tools to missing if neither is found
                missing.append(tool)
        
        if missing:
            # Add distribution-specific package information
            package_info = {
                'Debian/Ubuntu': 'exfatprogs',
                'Fedora': 'exfatprogs',
                'openSUSE': 'exfatprogs',
                'Arch Linux': 'exfatprogs',
                'Alternative': 'exfat-utils (legacy)'
            }
            missing.append("\nInstall using your distribution's package manager:")
            for distro, pkg in package_info.items():
                missing.append(f"  {distro}: {pkg}")
                
        return (len(missing) == 0, missing)
    
    @staticmethod
    def _compare_versions(ver1, ver2):
        """Compare two version strings"""
        v1_parts = [int(x) for x in ver1.split('.')]
        v2_parts = [int(x) for x in ver2.split('.')]
        return (v1_parts > v2_parts) - (v1_parts < v2_parts)

class F2fsFilesystemHandler(FilesystemHandler):
    """Handler for F2FS (Flash-Friendly File System) operations"""
    
    @classmethod
    def name(cls):
        return "F2FS"
        
    @classmethod
    def supports_file_size_greater_than_4gb(cls):
        return True
        
    @classmethod
    def parted_fs_type(cls):
        # parted doesn't directly support f2fs
        # but we can create the filesystem after partition creation
        return "ext4"
        
    @classmethod
    def format_partition(cls, partition, label):
        """
        Format the partition with F2FS filesystem
        
        Args:
            partition (str): Partition device path (e.g., /dev/sdX1)
            label (str): Filesystem label to apply
            
        Returns:
            int: 0 on success, non-zero on failure
        """
        utils.check_kill_signal()
        
        utils.print_with_color(_("Creating F2FS filesystem..."), "green")
        
        # Check for mkfs.f2fs command
        command_mkf2fs = utils.check_command("mkfs.f2fs")
        if not command_mkf2fs:
            utils.print_with_color(_("Error: mkfs.f2fs command not found"), "red")
            return 1
        
        # Determine optimal parameters based on device type
        format_opts = ["-f"]  # Force overwrite
        
        try:
            # Get device type (HDD, SSD, USB Flash)
            device_base = partition.rstrip('0123456789')
            with open(f"/sys/block/{os.path.basename(device_base)}/queue/rotational", 'r') as f:
                is_rotational = int(f.read().strip())
        
            # Add device-specific optimizations
            if not is_rotational:
                # For SSDs and flash drives
                format_opts.extend([
                    "-O", "extra_attr,inode_checksum,sb_checksum",  # Enable checksums for reliability
                    "-w", "4096",  # 4K sector size for modern flash
                    "-m", "5"      # 5% over-provisioning
                ])
                
                # Check if it's a removable device (likely USB flash)
                try:
                    with open(f"/sys/block/{os.path.basename(device_base)}/removable", 'r') as f:
                        is_removable = int(f.read().strip())
                    
                    if is_removable:
                        # USB flash drives benefit from higher over-provisioning
                        format_opts.extend([
                            "-m", "10",  # 10% over-provisioning for better longevity
                            "-t", "1"    # 1 segment per section for better GC
                        ])
                except (IOError, OSError):
                    pass
            else:
                # For HDDs
                format_opts.extend([
                    "-O", "extra_attr,inode_checksum,sb_checksum",  # Enable checksums for reliability
                    "-w", "4096",  # 4K sector size
                    "-m", "2"      # 2% over-provisioning is enough for HDDs
                ])
        except (IOError, OSError):
            # Fallback to basic options if we can't determine device type
            format_opts.extend([
                "-O", "extra_attr,inode_checksum,sb_checksum",  # Enable checksums for reliability
                "-w", "4096",  # 4K sector size
                "-m", "5"      # 5% over-provisioning
            ])
        
        # Add label if provided
        if label:
            format_opts.extend(["-l", label])
        
        # Format the partition
        cmd = [command_mkf2fs] + format_opts + [partition]
        utils.print_with_color(_("Running: {0}").format(" ".join(cmd)), "green" if utils.verbose else None)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Unable to create F2FS filesystem:"), "red")
            utils.print_with_color(result.stderr, "red")
            return 1
        
        # Validate the filesystem
        if not cls.validate_filesystem(partition):
            return 1
            
        return 0