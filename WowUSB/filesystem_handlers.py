
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

    @classmethod
    def validate_filesystem(cls, partition):
        """
        Default validator for filesystems that don't have a specific one.
        Can be overridden by subclasses.
        """
        utils.print_with_color(_("No specific validator for {0} filesystem. Assuming OK.").format(cls.name()), "yellow")
        return True

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
        
        command_mkdosfs = utils.check_command("mkdosfs")
        if not command_mkdosfs:
            utils.print_with_color(_("Error: mkdosfs command not found"), "red")
            return 1
            
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
        command_mkntfs = utils.check_command("mkntfs")
        if not command_mkntfs:
            utils.print_with_color(_("Error: mkntfs command not found"), "red")
            return 1
            
        format_cmd = [command_mkntfs, "-f", "-L", label, "-v"]
        try:
            device_base = partition.rstrip('0123456789')
            with open(f"/sys/block/{os.path.basename(device_base)}/queue/rotational", 'r') as f:
                is_rotational = int(f.read().strip())
            if not is_rotational:
                format_cmd.extend(["-c", "4096", "-a", "4096"])
            else:
                format_cmd.extend(["-c", "16384"])
        except (IOError, OSError):
            pass
        
        utils.print_with_color(_("Running: {0}").format(" ".join(format_cmd + [partition])), "green" if utils.verbose else None)
        result = subprocess.run(format_cmd + [partition], capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Unable to create NTFS filesystem:"), "red")
            utils.print_with_color(result.stderr, "red")
            return 1
            
        if not cls.validate_filesystem(partition):
            return 1
        return 0
        
    @classmethod
    def validate_filesystem(cls, partition):
        utils.check_kill_signal()
        utils.print_with_color(_("Validating NTFS filesystem..."), "green")
        ntfsck_cmd = utils.check_command("ntfsfix") or utils.check_command("ntfsck")
        if not ntfsck_cmd:
            utils.print_with_color(_("Warning: NTFS filesystem check tools not found, skipping validation"), "yellow")
            return True
            
        check_cmd = [ntfsck_cmd]
        if ntfsck_cmd.endswith("ntfsfix"):
            check_cmd.append("-n")
        
        result = subprocess.run(check_cmd + [partition], capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Filesystem validation failed:"), "red")
            utils.print_with_color(result.stderr, "red")
            return False
            
        with tempfile.TemporaryDirectory() as temp_mount:
            try:
                if subprocess.run(["mount", "-t", "ntfs-3g", partition, temp_mount]).returncode != 0:
                    utils.print_with_color(_("Warning: Unable to mount filesystem for validation"), "yellow")
                    return True
                
                large_file_path = os.path.join(temp_mount, "large_file_test")
                with open(large_file_path, 'wb') as f:
                    f.seek(5 * 1024 * 1024 * 1024 - 1)
                    f.write(b'\x00')

                file_size = os.path.getsize(large_file_path)
                if file_size < 4 * 1024 * 1024 * 1024:
                    utils.print_with_color(_("Warning: Large file test failed. File size: {0}").format(utils.convert_to_human_readable_format(file_size)), "yellow")
                os.unlink(large_file_path)
                
                if subprocess.run(["umount", temp_mount]).returncode != 0:
                    utils.print_with_color(_("Warning: Unable to unmount test filesystem"), "yellow")
                    return False
            except Exception as e:
                utils.print_with_color(_("Warning: Validation error: {0}").format(str(e)), "yellow")
                try:
                    subprocess.run(["umount", temp_mount], stderr=subprocess.DEVNULL, check=False)
                except: pass
                return False
                
        utils.print_with_color(_("NTFS filesystem validation completed successfully"), "green")
        return True
        
    @classmethod
    def check_dependencies(cls):
        missing = []
        if not utils.check_command("mkntfs"):
            missing.append("ntfs-3g")
        return (len(missing) == 0, missing)
        
    @classmethod
    def needs_uefi_support_partition(cls):
        return True
        
    @classmethod
    def get_uefi_bootloader_file(cls):
        return ("https://github.com/pbatard/rufus/raw/master/res/uefi/uefi-ntfs.img", "uefi-ntfs.img")

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
        return "fat32"
        
    @classmethod
    def format_partition(cls, partition, label):
        utils.check_kill_signal()
        format_opts = ["--volume-label", label, "--cluster-size=128K"]
        try:
            device_base = partition.rstrip('0123456789')
            with open(f"/sys/block/{os.path.basename(device_base)}/queue/rotational", 'r') as f:
                is_rotational = int(f.read().strip())
            
            format_opts = ["--sector-size=4096", "--volume-label", label, "--volume-serial", hex(int.from_bytes(os.urandom(4), 'big'))[2:].upper()]
            if not is_rotational:
                format_opts.extend(["--cluster-size=128K", "--alignment=1M"])
                try:
                    with open(f"/sys/block/{os.path.basename(device_base)}/removable", 'r') as f:
                        if int(f.read().strip()):
                            format_opts.extend(["--quick-format", "--sectormap=all"])
                except (IOError, OSError): pass
            else:
                format_opts.append("--cluster-size=32K")
        except (IOError, OSError): pass
        
        utils.print_with_color(_("Creating exFAT filesystem..."), "green")
        command_mkexfat = utils.check_command("mkexfatfs") or utils.check_command("mkfs.exfat")
        if not command_mkexfat:
            utils.print_with_color(_("Error: mkexfatfs/mkfs.exfat command not found"), "red")
            return 1
        
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
            
        if not cls.validate_filesystem(partition):
            return 1
        return 0
    
    @classmethod
    def needs_uefi_support_partition(cls):
        return True
    
    @classmethod
    def validate_filesystem(cls, partition):
        utils.check_kill_signal()
        utils.print_with_color(_("Validating exFAT filesystem..."), "green")
        fsck_cmd = utils.check_command("fsck.exfat") or utils.check_command("exfatfsck") or utils.check_command("chkexfat")
        if not fsck_cmd:
            utils.print_with_color(_("Warning: exFAT filesystem check tools not found, skipping validation"), "yellow")
            return True
            
        result = subprocess.run([fsck_cmd, "-n", partition], capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Filesystem validation failed:"), "red")
            utils.print_with_color(result.stderr, "red")
            return False
            
        with tempfile.TemporaryDirectory() as temp_mount:
            try:
                if subprocess.run(["mount", "-t", "exfat", partition, temp_mount]).returncode != 0:
                    utils.print_with_color(_("Warning: Unable to mount filesystem for validation"), "yellow")
                    return True
                if not os.path.exists(temp_mount) or not os.access(temp_mount, os.W_OK):
                    utils.print_with_color(_("Warning: Mount point does not exist or is not writable: {0}").format(temp_mount), "yellow")
                    return True

                large_file_path = os.path.join(temp_mount, "large_file_test")
                with open(large_file_path, 'wb') as f:
                    f.seek(5 * 1024 * 1024 * 1024 - 1)
                    f.write(b'\x00')

                file_size = os.path.getsize(large_file_path)
                if file_size < 4 * 1024 * 1024 * 1024:
                    utils.print_with_color(_("Warning: Large file test failed. File size: {0}").format(utils.convert_to_human_readable_format(file_size)),"yellow")
                os.unlink(large_file_path)
                
                if subprocess.run(["umount", temp_mount]).returncode != 0:
                    utils.print_with_color(_("Warning: Unable to unmount test filesystem"), "yellow")
                    return False
            except Exception as e:
                utils.print_with_color(_("Warning: Validation error: {0}").format(str(e)), "yellow")
                try:
                    subprocess.run(["umount", temp_mount], stderr=subprocess.DEVNULL, check=False)
                except: pass
                return False
                
        utils.print_with_color(_("exFAT filesystem validation completed successfully"), "green")
        return True
    
    @classmethod
    def get_uefi_bootloader_file(cls):
        return ("https://github.com/pbatard/rufus/raw/master/res/uefi/uefi-ntfs.img", "uefi-ntfs.img")
    
    @classmethod
    def check_dependencies(cls):
        missing = []
        REQUIRED_TOOLS = {'mkexfatfs': '1.3.0', 'mkfs.exfat': '1.1.0', 'fsck.exfat': '1.1.0', 'exfatlabel': '1.3.0'}
        found_formatter = False
        for tool, min_version in REQUIRED_TOOLS.items():
            tool_path = utils.check_command(tool)
            if tool_path:
                try:
                    version_output = subprocess.run([tool_path, '--version'], capture_output=True, text=True, check=False).stdout
                    if not version_output and tool_path.endswith('mkexfatfs'):
                         version_output = subprocess.run([tool_path], capture_output=True, text=True, check=False).stderr
                    
                    version_match = re.search(r'version\s+(\d+\.\d+\.\d+)', version_output, re.IGNORECASE) or \
                                  re.search(r'mkexfatfs\s+(\d+\.\d+\.\d+)', version_output, re.IGNORECASE)
                    if version_match:
                        version = version_match.group(1)
                        if not hasattr(utils, '_compare_versions'):
                            utils._compare_versions = lambda v1, v2: (tuple(map(int, v1.split('.'))) > tuple(map(int, v2.split('.')))) - \
                                                                    (tuple(map(int, v1.split('.'))) < tuple(map(int, v2.split('.'))))

                        if utils._compare_versions(version, min_version) < 0:
                            missing.append(f"{tool} (found {version}, need {min_version})")
                        elif tool in ['mkexfatfs', 'mkfs.exfat']:
                            found_formatter = True
                    else:
                        missing.append(f"{tool} (version not detectable or too old, need >={min_version})")
                except (subprocess.SubprocessError, OSError, AttributeError):
                    missing.append(f"{tool} (version check failed)")
            elif tool in ['mkexfatfs', 'mkfs.exfat'] and not found_formatter:
                missing.append(tool)
            elif tool not in ['mkexfatfs', 'mkfs.exfat']:
                 missing.append(tool)

        if not found_formatter and ('mkexfatfs' in missing and 'mkfs.exfat' in missing) :
             pass
        elif not found_formatter:
            if 'mkexfatfs' not in [m.split(' ')[0] for m in missing] and 'mkfs.exfat' not in [m.split(' ')[0] for m in missing]:
                 missing.append("mkexfatfs or mkfs.exfat")
        
        if missing:
            package_info = {'Debian/Ubuntu': 'exfatprogs', 'Fedora': 'exfatprogs', 'openSUSE': 'exfatprogs', 'Arch Linux': 'exfatprogs', 'Alternative': 'exfat-utils (legacy)'}
            missing_str = ", ".join(list(set(m.split(' ')[0] for m in missing)))
            missing_details = f"Missing tools: {missing_str}. Suggested packages: "
            missing_details += "; ".join([f"{distro}: {pkg}" for distro, pkg in package_info.items()])
            return (False, [missing_details])
                
        return (True, [])

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
        return "ext4"
        
    @classmethod
    def format_partition(cls, partition, label):
        utils.check_kill_signal()
        utils.print_with_color(_("Creating F2FS filesystem..."), "green")
        command_mkf2fs = utils.check_command("mkfs.f2fs")
        if not command_mkf2fs:
            utils.print_with_color(_("Error: mkfs.f2fs command not found"), "red")
            return 1
        
        format_opts = ["-f"]
        try:
            device_base = partition.rstrip('0123456789')
            with open(f"/sys/block/{os.path.basename(device_base)}/queue/rotational", 'r') as f:
                is_rotational = int(f.read().strip())
            if not is_rotational:
                format_opts.extend(["-O", "extra_attr,inode_checksum,sb_checksum", "-w", "4096", "-m", "5"])
                try:
                    with open(f"/sys/block/{os.path.basename(device_base)}/removable", 'r') as f:
                        if int(f.read().strip()):
                            format_opts.extend(["-m", "10", "-t", "1"])
                except (IOError, OSError): pass
            else:
                format_opts.extend(["-O", "extra_attr,inode_checksum,sb_checksum", "-w", "4096", "-m", "2"])
        except (IOError, OSError):
            format_opts.extend(["-O", "extra_attr,inode_checksum,sb_checksum", "-w", "4096", "-m", "5"])

        if label:
            format_opts.extend(["-l", label])
        
        cmd = [command_mkf2fs] + format_opts + [partition]
        utils.print_with_color(_("Running: {0}").format(" ".join(cmd)), "green" if utils.verbose else None)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Unable to create F2FS filesystem:"), "red")
            utils.print_with_color(result.stderr, "red")
            return 1
        
        if not cls.validate_filesystem(partition):
            return 1
        return 0

    @classmethod
    def validate_filesystem(cls, partition):
        utils.check_kill_signal()
        utils.print_with_color(_("Validating F2FS filesystem..."), "green")
        fsck_f2fs_cmd = utils.check_command("fsck.f2fs")
        if not fsck_f2fs_cmd:
            utils.print_with_color(_("Warning: fsck.f2fs command not found. Skipping F2FS validation."), "yellow")
            return True

        cmd = [fsck_f2fs_cmd, "-f", partition]
        utils.print_with_color(_("Running: {0}").format(" ".join(cmd)), "blue" if utils.verbose else None)

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: F2FS filesystem validation failed for {0}:").format(partition), "red")
            utils.print_with_color(result.stdout, "red")
            utils.print_with_color(result.stderr, "red")
            return False

        utils.print_with_color(_("F2FS filesystem validation passed for {0}.").format(partition), "green")
        return True

    @classmethod
    def check_dependencies(cls):
        missing = []
        if not utils.check_command("mkfs.f2fs"):
            missing.append("f2fs-tools (provides mkfs.f2fs)")
        if not utils.check_command("fsck.f2fs"):
            missing.append("f2fs-tools (provides fsck.f2fs)")

        if "f2fs-tools (provides mkfs.f2fs)" in missing and "f2fs-tools (provides fsck.f2fs)" in missing:
            missing = ["f2fs-tools"]
        elif "f2fs-tools (provides mkfs.f2fs)" in missing:
             missing = ["f2fs-tools (for mkfs.f2fs)"]
        elif "f2fs-tools (provides fsck.f2fs)" in missing:
             missing = ["f2fs-tools (for fsck.f2fs)"]
        return (len(missing) == 0, missing)

class BtrfsFilesystemHandler(FilesystemHandler):
    """Handler for BTRFS filesystem operations - STUB"""
    @classmethod
    def name(cls): return "BTRFS"
    @classmethod
    def supports_file_size_greater_than_4gb(cls): return True
    @classmethod
    def parted_fs_type(cls): return "btrfs"

    @classmethod
    def format_partition(cls, partition, label):
        utils.check_kill_signal()
        utils.print_with_color(_("Creating BTRFS filesystem..."), "green")
        command_mkbtrfs = utils.check_command("mkfs.btrfs")
        if not command_mkbtrfs:
            utils.print_with_color(_("Error: mkfs.btrfs command not found"), "red")
            return 1

        cmd = [command_mkbtrfs, "-f"]
        if label: cmd.extend(["-L", label])
        cmd.append(partition)

        utils.print_with_color(_("Running: {0}").format(" ".join(cmd)), "blue" if utils.verbose else None)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            utils.print_with_color(_("Error: Unable to create BTRFS filesystem:"), "red")
            utils.print_with_color(result.stdout, "red")
            utils.print_with_color(result.stderr, "red")
            return 1

        utils.print_with_color(_("BTRFS filesystem created on {0} (basic stub).").format(partition), "green")
        # Add validate_filesystem call when implemented for BTRFS if desired
        return 0

    @classmethod
    def check_dependencies(cls):
        missing = []
        if not utils.check_command("mkfs.btrfs"):
            missing.append("btrfs-progs")
        return (len(missing) == 0, missing)

# --- Registration of Handlers and Factory Function ---

FILESYSTEM_HANDLERS_MAP = {
    "FAT": FatFilesystemHandler,
    "FAT32": FatFilesystemHandler,
    "NTFS": NtfsFilesystemHandler,
    "EXFAT": ExfatFilesystemHandler,
    "F2FS": F2fsFilesystemHandler,
    "BTRFS": BtrfsFilesystemHandler,
}

def get_filesystem_handler(fs_type_str):
    fs_type_upper = fs_type_str.upper()
    handler_class = FILESYSTEM_HANDLERS_MAP.get(fs_type_upper)
    if not handler_class:
        raise ValueError(f"Unsupported filesystem type: {fs_type_str}")
    return handler_class

def get_optimal_filesystem_for_iso(source_fs_mountpoint):
    has_large_files, _, _ = utils.check_fat32_filesize_limitation_detailed(source_fs_mountpoint)
    available_handlers = get_available_filesystem_handlers()

    # Desired order of preference, especially for payload/data partition
    # F2FS -> exFAT -> NTFS -> BTRFS -> FAT32
    preferred_order_large_files = ["F2FS", "EXFAT", "NTFS", "BTRFS"]
    preferred_order_no_large_files = ["F2FS", "EXFAT", "FAT32", "NTFS", "BTRFS"] # FAT32 is good if no large files

    if has_large_files:
        for fs_pref in preferred_order_large_files:
            if fs_pref in available_handlers:
                utils.print_with_color(_("Selected {0} for large file support.").format(fs_pref), "blue")
                return fs_pref
        # Fallback if none of the preferred for large files are available but FAT32 is (though it won't work)
        if "FAT32" in available_handlers:
             utils.print_with_color(_("Warning: Large files present, but only FAT32 is available. This may lead to errors."), "yellow")
             return "FAT32"
    else: # No large files
        for fs_pref in preferred_order_no_large_files:
            if fs_pref in available_handlers:
                utils.print_with_color(_("Selected {0} (no large files detected).").format(fs_pref), "blue")
                return fs_pref

    # If no suitable filesystem is found among the preferred ones
    utils.print_with_color(_("CRITICAL: No suitable filesystem formatters found! Please install f2fs-tools, exfatprogs, ntfs-3g, btrfs-progs or dosfstools."), "red")
    # Attempt to return *any* available handler if the logic above somehow fails to select one
    # This part should ideally not be reached if preferred lists are comprehensive
    if available_handlers:
        fallback_fs = available_handlers[0]
        utils.print_with_color(_("Warning: Falling back to the first available filesystem: {0}").format(fallback_fs), "yellow")
        return fallback_fs

    raise RuntimeError(_("No suitable filesystem formatters found, and no available handlers to fallback to."))

def get_available_filesystem_handlers():
    available = []
    # Ensure consistent order for checking, aligning with potential preference
    handler_keys_ordered = ["F2FS", "EXFAT", "NTFS", "BTRFS", "FAT32", "FAT"]

    processed_names = set()

    for name_key in handler_keys_ordered:
        if name_key in FILESYSTEM_HANDLERS_MAP:
            handler_class = FILESYSTEM_HANDLERS_MAP[name_key]
            handler_name = handler_class.name() # FAT32, NTFS, etc.
            if handler_name not in processed_names:
                is_avail, _ = handler_class.check_dependencies()
                if is_avail:
                    available.append(handler_name)
                processed_names.add(handler_name)
    return available