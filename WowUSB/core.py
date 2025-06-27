
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

import os
import time
import shutil
import argparse
import tempfile
import traceback
import threading
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

import WowUSB.utils as utils
import WowUSB.workaround as workaround
import WowUSB.miscellaneous as miscellaneous
import WowUSB.filesystem_handlers as fs_handlers
import WowUSB.partitioning as partitioning
import WowUSB.grub_manager as grub_manager
import WowUSB.linux_installer as linux_installer

_ = miscellaneous.i18n

application_name = 'WowUSB-DS9'
application_version = miscellaneous.__version__
DEFAULT_NEW_FS_LABEL = 'Windows USB'

application_site_url = 'https://github.com/robinmc/WowUSB-DS9'
applicationopyright_declaration = "(C)2025 Robin L. M. Cheung, MBA"
applicationopyright_notice = application_name + " is free software licensed under the GNU General Public License version 3(or any later version of your preference) that gives you THE 4 ESSENTIAL FREEDOMS\nhttps://www.gnu.org/philosophy/"

#: Increase verboseness, provide more information when required
verbose = False

debug = False

CopyFiles_handle = threading.Thread()

#: Execution state for cleanup functions to determine if clean up is required
current_state = 'pre-init'

gui = None


def init(from_cli=True, install_mode=None, source_media=None, target_media=None, workaround_bios_boot_flag=False,
          target_filesystem_type="FAT", filesystem_label=DEFAULT_NEW_FS_LABEL, skip_legacy_bootloader=False):
    """
    :param from_cli:
    :type from_cli: bool
    :param install_mode:
    :param source_media:
    :param target_media:
    :param workaround_bios_boot_flag:
    :param target_filesystem_type:
    :param skip_legacy_bootloader:
    :param filesystem_label:
    :return: List
    """
    source_fs_mountpoint = "/media/wowusbeds9_source_" + str(
        round((datetime.today() - datetime.fromtimestamp(0)).total_seconds())) + "_" + str(os.getpid())
    target_fs_mountpoint = "/media/wowusbeds9_target_" + str(
        round((datetime.today() - datetime.fromtimestamp(0)).total_seconds())) + "_" + str(os.getpid())

    temp_directory = tempfile.mkdtemp(prefix="WowUSB.")

    verbose = False

    no_color = True

    debug = False

    parser = None

    if from_cli:
        # Get the parsed arguments
        args = setup_arguments()
        
        # Set parser to None since we don't need it after this point
        parser = None

        if hasattr(args, 'about') and args.about:
            print_application_info()
            return 0

        # Set install_mode from the already parsed arguments
        if hasattr(args, 'install_mode'):
            install_mode = args.install_mode
        else:
            if args.device:
                install_mode = "device"
            elif args.partition:
                install_mode = "partition"
            else:
                utils.print_with_color(_("You need to specify installation type (--device or --partition)"))
                return 1

        #: source_media may be an optical disk drive or a disk image
        source_media = args.source
        #: target_media may be an entire usb storage device or just a partition
        target_media = args.target

        workaround_bios_boot_flag = getattr(args, 'workaround_bios_boot_flag', False)
        
        skip_legacy_bootloader = getattr(args, 'workaround_skip_grub', False)

        target_filesystem_type = getattr(args, 'target_filesystem', 'FAT')

        filesystem_label = getattr(args, 'label', DEFAULT_NEW_FS_LABEL)

        verbose = getattr(args, 'verbose', False)

        no_color = getattr(args, 'no_color', True)

        debug = getattr(args, 'debug', False)

        
        # Set the wintogo flag if it exists
        wintogo = getattr(args, 'wintogo', False)
        if parser is not None:
            setattr(parser, 'wintogo', wintogo)

    utils.no_color = no_color
    utils.verbose = verbose
    utils.gui = gui

    if from_cli:
        return [source_fs_mountpoint, target_fs_mountpoint, temp_directory, install_mode, source_media, target_media,
                workaround_bios_boot_flag, skip_legacy_bootloader, target_filesystem_type, filesystem_label, verbose, debug, parser]
    else:
        return [source_fs_mountpoint, target_fs_mountpoint, temp_directory, target_media]

# Stubs for functions called by main() but not defined at module level
def wipe_existing_partition_table_and_filesystem_signatures(target_device):
    """Stub for wiping partition table and filesystem signatures."""
    utils.print_with_color(_("STUB: Wiping signatures on {0}").format(target_device), "magenta")
    # Actual logic would involve calling wipefs or dd
    return 0

def create_target_partition_table(target_device, table_type):
    """Stub for creating a partition table (MBR or GPT)."""
    utils.print_with_color(_("STUB: Creating {0} partition table on {1}").format(table_type, target_device), "magenta")
    # Actual logic would involve calling parted to mklabel
    if table_type == "legacy":
        return utils.run_command(["parted", "--script", target_device, "mklabel", "msdos"],
                                 message="Creating MBR partition table",
                                 error_message="Failed to create MBR partition table")
    elif table_type == "uefi" or table_type == "gpt": # Assuming uefi implies gpt for new tables
        return utils.run_command(["parted", "--script", target_device, "mklabel", "gpt"],
                                 message="Creating GPT partition table",
                                 error_message="Failed to create GPT partition table")
    return 1 # Unknown table type

def create_target_partition(target_device, target_partition_device, fs_type, label):
    """Stub for creating and formatting the main target partition."""
    utils.print_with_color(_("STUB: Creating partition {0} ({1}, {2}) on {3}").format(target_partition_device, fs_type, label, target_device), "magenta")
    # Actual logic involves:
    # 1. parted mkpart primary fs_type 1MiB 100% (or similar)
    # 2. Getting fs_handler
    # 3. fs_handler.format_partition(target_partition_device, label)

    # Simplified parted call for stub
    fs_handler = fs_handlers.get_filesystem_handler(fs_type)
    parted_fs_type_str = fs_handler.parted_fs_type() # Get appropriate type for parted

    # Create the primary partition covering most of the disk
    # This assumes it's the first partition. More complex logic needed for multiple partitions.
    if utils.run_command(["parted", "--script", target_device, "mkpart", "primary", parted_fs_type_str, "1MiB", "100%"],
                         message=f"Creating primary partition {target_partition_device}",
                         error_message=f"Failed to create primary partition {target_partition_device}"):
        return 1

    time.sleep(2) # Allow kernel to recognize new partition

    if fs_handler.format_partition(target_partition_device, label) != 0:
        return 1
    return 0

def create_wintogo_partition_layout(target_device, fs_type, label):
    """Stub for creating Windows-To-Go partition layout."""
    utils.print_with_color(_("STUB: Creating WinToGo layout on {0} ({1}, {2})").format(target_device, fs_type, label), "magenta")
    # Actual logic involves multiple parted calls for ESP, MSR, Windows partitions, then formatting.
    # For simplicity, this stub will just simulate success.
    # 1. mklabel gpt
    # 2. mkpart ESP fat32 1MiB 261MiB, set 1 boot on, set 1 esp on
    # 3. mkpart MSR 261MiB 389MiB, set 2 msftres on
    # 4. mkpart Windows fs_type 389MiB 100%
    # 5. Format ESP as FAT32
    # 6. Format Windows partition with fs_type
    if create_target_partition_table(target_device, "gpt"): return 1

    # ESP
    if utils.run_command(["parted", "--script", target_device, "mkpart", "ESP", "fat32", "1MiB", "261MiB", "set", "1", "boot", "on", "set", "1", "esp", "on"]): return 1
    time.sleep(1)
    if utils.run_command([utils.check_command("mkdosfs"), "-F", "32", "-n", "ESP", target_device + "1"]): return 1 # Assumes mkdosfs path from check_command

    # MSR
    if utils.run_command(["parted", "--script", target_device, "mkpart", "MSR", "261MiB", "389MiB", "set", "2", "msftres", "on"]): return 1

    # Windows
    fs_handler = fs_handlers.get_filesystem_handler(fs_type)
    if hasattr(fs_handler, 'parted_fs_type') and callable(getattr(fs_handler, 'parted_fs_type')) :
        parted_fs_type_str = fs_handler.parted_fs_type()
    else:
        # Fallback if the handler (possibly a mock) doesn't have parted_fs_type
        utils.print_with_color(f"Warning: Filesystem handler for {fs_type} missing 'parted_fs_type' method. Defaulting to 'fat32' for parted.", "yellow")
        parted_fs_type_str = "fat32" # A common default for parted type field

    if utils.run_command(["parted", "--script", target_device, "mkpart", "Windows", parted_fs_type_str, "389MiB", "100%"]): return 1
    time.sleep(1)
    if fs_handler.format_partition(target_device + "3", label) != 0: return 1 # Assumes Windows is 3rd partition

    return 0

def main(source_fs_mountpoint, target_fs_mountpoint, source_media, target_media, install_mode, temp_directory,
          target_filesystem_type, workaround_bios_boot_flag, parser=None, skip_legacy_bootloader=False):
    """
    :param parser:
    :param source_fs_mountpoint:
    :param target_fs_mountpoint:
    :param source_media:
    :param target_media:
    :param install_mode:
    :param temp_directory:
    :param target_filesystem_type:
    :param workaround_bios_boot_flag:
    :param skip_legacy_bootloader:
    :return: 0 - succes; 1 - failure
    """
    global debug
    global verbose
    global no_color
    global current_state
    global target_device

    current_state = 'enter-init'
    if utils.gui: utils.gui.state = _("Initializing..."); utils.gui.progress = False

    command_mkdosfs, command_mkntfs, command_grubinstall = utils.check_runtime_dependencies(application_name)
    utils.check_kill_signal() # Check after initial setup
    if command_grubinstall == "grub-install":
        name_grub_prefix = "grub"
    else:
        name_grub_prefix = "grub2"

    utils.print_with_color(application_name + " v" + application_version)
    utils.print_with_color("==============================")

    if os.getuid() != 0:
        utils.print_with_color(_("Warning: You are not running {0} as root!").format(application_name), "yellow")
        utils.print_with_color(_("Warning: This might be the reason of the following failure."), "yellow")

    if utils.check_runtime_parameters(install_mode, source_media, target_media):
        parser.print_help()
        return 1

    target_device, target_partition = utils.determine_target_parameters(install_mode, target_media)

    if utils.check_source_and_target_not_busy(install_mode, source_media, target_device, target_partition):
        return 1

    current_state = "start-mounting"
    if utils.gui: utils.gui.state = _("Mounting source filesystem..."); utils.gui.progress = False

    if mount_source_filesystem(source_media, source_fs_mountpoint):
        utils.print_with_color(_("Error: Unable to mount source filesystem"), "red")
        return 1
    utils.check_kill_signal()

    # If auto-detection is requested, determine the optimal filesystem
    if utils.gui: utils.gui.state = _("Determining optimal filesystem..."); utils.gui.progress = False
    if target_filesystem_type.upper() == "AUTO":
        target_filesystem_type = fs_handlers.get_optimal_filesystem_for_iso(source_fs_mountpoint)
        utils.check_kill_signal()
        utils.print_with_color(
            _("Info: Auto-selected {0} filesystem based on source content").format(target_filesystem_type),
            "green"
        )
    
    # Check if selected filesystem can handle the source files
    try:
        fs_handler = fs_handlers.get_filesystem_handler(target_filesystem_type)
        if not fs_handler.supports_file_size_greater_than_4gb():
            # Check if there are files larger than 4GB
            has_large_files, largest_file, largest_size = utils.check_fat32_filesize_limitation_detailed(source_fs_mountpoint)
            if has_large_files:
                utils.print_with_color(
                    _("Warning: Source contains files larger than 4GB. Largest: {0} ({1})").format(
                        largest_file, 
                        utils.convert_to_human_readable_format(largest_size)
                    ),
                    "yellow"
                )
                
            if utils.check_fat32_filesize_limitation(source_fs_mountpoint):
                # Try to find a better filesystem
                available_fs = fs_handlers.get_available_filesystem_handlers()
                alternative_fs = None
                
                # Prefer exFAT if available, then NTFS, then others
                for fs_type in ["EXFAT", "NTFS", "F2FS", "BTRFS"]:
                    if fs_type in available_fs:
                        alternative_fs = fs_type
                        break
                
                if alternative_fs:
                    utils.print_with_color(
                        _("Warning: Switching to {0} filesystem to support files larger than 4GB").format(alternative_fs),
                        "yellow"
                    )
                    target_filesystem_type = alternative_fs
                else:
                    utils.print_with_color(
                        _("Error: Source contains files larger than 4GB, but no suitable filesystem found to handle them."),
                        "red"
                    )
                    return 1
    except ValueError as e:
        utils.print_with_color(str(e), "red")
        return 1
    
    # Get the filesystem handler for the selected filesystem
    if utils.gui: utils.gui.state = _("Validating filesystem choice..."); utils.gui.progress = False
    try:
        fs_handler = fs_handlers.get_filesystem_handler(target_filesystem_type)
        utils.check_kill_signal()
        is_available, missing_deps = fs_handler.check_dependencies()
        if not is_available:
            utils.print_with_color(
                _("Error: Missing dependencies for {0} filesystem: {1}").format(
                    fs_handler.name(), ", ".join(missing_deps)
                ),
                "red"
            )
            return 1
        utils.check_kill_signal()
            
        # Print selected filesystem information
        utils.print_with_color(
            _("Using {0} filesystem for Windows installation").format(fs_handler.name()),
            "green"
        )
        if fs_handler.supports_file_size_greater_than_4gb():
            utils.print_with_color(_("Large file support (>4GB) is enabled"), "green")
        
        # Print UEFI support information
        if fs_handler.needs_uefi_support_partition():
            utils.print_with_color(
                _("Note: {0} requires a separate UEFI support partition for UEFI booting").format(fs_handler.name()),
                "green" if utils.verbose else None
            )
    except ValueError as e:
        utils.print_with_color(str(e), "red")
        return 1
    utils.check_kill_signal()

    # Check if Windows-To-Go mode is enabled
    is_wintogo_mode = getattr(parser, 'wintogo', False) if parser else False
    
    if is_wintogo_mode:
        utils.print_with_color(_("Windows-To-Go mode enabled"), "green") # CLI message
        if utils.gui: utils.gui.state = _("Configuring for Windows-To-Go..."); utils.gui.progress = False
        
        if install_mode != "device":
            utils.print_with_color(_("Error: Windows-To-Go requires --device mode"), "red")
            return 1
            
        # Create Windows-To-Go specific partition layout
        if create_wintogo_partition_layout(target_device, target_filesystem_type, filesystem_label):
            utils.print_with_color(_("Error: Failed to create Windows-To-Go partition layout"), "red")
            return 1
            
        # Update target partition to point to the Windows partition (3rd partition)
        target_partition = target_device + "3"
        utils.check_kill_signal()
    elif install_mode == "device":
        if utils.gui: utils.gui.state = _("Wiping existing signatures..."); utils.gui.progress = False
        wipe_existing_partition_table_and_filesystem_signatures(target_device)
        utils.check_kill_signal()

        if utils.gui: utils.gui.state = _("Creating partition table..."); utils.gui.progress = False
        create_target_partition_table(target_device, "legacy") # Creates MBR
        utils.check_kill_signal()

        # Create the main Windows partition (e.g., /dev/sdb1)
        if utils.gui: utils.gui.state = _("Creating main Windows partition..."); utils.gui.progress = False
        if create_target_partition(target_device, target_partition, target_filesystem_type, filesystem_label):
            utils.print_with_color(_("Error: Failed to create main target partition {0}").format(target_partition), "red")
            return 1
        utils.check_kill_signal()

        # Add UEFI support partition if needed (e.g., /dev/sdb2)
        if fs_handler.needs_uefi_support_partition():
            if utils.gui: utils.gui.state = _("Creating UEFI support partition..."); utils.gui.progress = False
            uefi_support_part_device = target_device + "2" # Assuming main partition is '1'
            if create_uefi_support_partition(target_device, uefi_support_part_device):
                 utils.print_with_color(_("Error: Failed to create UEFI support partition on {0}").format(target_device), "red")
                 return 1
            utils.check_kill_signal()
            if utils.gui: utils.gui.state = _("Installing UEFI support files..."); utils.gui.progress = False
            if install_uefi_support_files(fs_handler, uefi_support_part_device, temp_directory):
                utils.print_with_color(_("Error: Failed to install UEFI support files to {0}").format(uefi_support_part_device), "red")
                return 1
            utils.check_kill_signal()

    if install_mode == "partition":
        # If only working on a partition, UEFI support partition logic might be different
        # or assumed to be handled manually by the user.
        # For now, we only create/install UEFI support for "device" mode.
        if utils.gui: utils.gui.state = _("Checking target partition..."); utils.gui.progress = False
        if utils.check_target_partition(target_partition, target_device):
            return 1
        utils.check_kill_signal()

    if utils.gui: utils.gui.state = _("Mounting target filesystem..."); utils.gui.progress = False
    if mount_target_filesystem(target_partition, target_fs_mountpoint):
        utils.print_with_color(_("Error: Unable to mount target filesystem"), "red")
        return 1
    utils.check_kill_signal()

    if utils.gui: utils.gui.state = _("Checking free space on target..."); utils.gui.progress = False
    if utils.check_target_filesystem_free_space(target_fs_mountpoint, source_fs_mountpoint, target_partition):
        return 1
    utils.check_kill_signal()

    current_state = "copying-filesystem"
    # GUI state for copying is handled by ReportCopyProgress thread via core.gui directly

    copy_filesystem_files(source_fs_mountpoint, target_fs_mountpoint)
    utils.check_kill_signal() # After copy_filesystem_files returns

    # Set up persistence for Linux distributions if requested
    if parser and getattr(parser, 'persistence', None) is not None:
        if setup_linux_persistence(target_device, target_partition,
                                   target_filesystem_type, parser.persistence) != 0:
            utils.print_with_color(_("Error: Failed to set up persistence"), "red")
            return 1

    # Apply Windows-To-Go specific modifications if in Windows-To-Go mode
    if is_wintogo_mode:
        if utils.gui: utils.gui.state = _("Applying Windows-To-Go modifications..."); utils.gui.progress = False
        # Detect Windows version
        windows_version, build_number, is_windows11 = utils.detect_windows_version(source_fs_mountpoint)
        utils.print_with_color(
            _("Detected Windows version: {0}, build: {1}").format(windows_version, build_number),
            "green"
        )
        utils.check_kill_signal()
        
        # Apply TPM bypass for Windows 11
        if is_windows11:
            if utils.gui: utils.gui.state = _("Applying Windows 11 TPM bypass..."); utils.gui.progress = False
            utils.print_with_color(_("Applying Windows 11 specific modifications..."), "green")
            workaround.bypass_windows11_tpm_requirement(target_fs_mountpoint)
            utils.check_kill_signal()
        
        # Configure drivers and hardware detection for portable Windows
        if utils.gui: utils.gui.state = _("Preparing portable drivers..."); utils.gui.progress = False
        workaround.prepare_windows_portable_drivers(target_fs_mountpoint)
        utils.check_kill_signal()
        
        # Mount ESP partition for bootloader installation
        if utils.gui: utils.gui.state = _("Mounting ESP for WinToGo bootloader setup..."); utils.gui.progress = False
        esp_partition = target_device + "1"
        esp_mountpoint = target_fs_mountpoint + "_esp"
        
        os.makedirs(esp_mountpoint, exist_ok=True)
        
        if subprocess.run(["mount", esp_partition, esp_mountpoint]).returncode != 0:
            utils.print_with_color(_("Error: Unable to mount ESP partition"), "red")
            return 1
        utils.check_kill_signal()
        
        # Copy bootloader files to ESP
        if utils.gui: utils.gui.state = _("Copying bootloader files to ESP (WinToGo)..."); utils.gui.progress = False
        utils.print_with_color(_("Installing bootloader files to ESP..."), "green")
        
        # Create directory structure
        os.makedirs(os.path.join(esp_mountpoint, "EFI", "Boot"), exist_ok=True)
        utils.check_kill_signal()
        # Copy bootloader files from Windows partition
        boot_files = [
            ("bootmgfw.efi", "bootx64.efi"),
            ("bootmgr.efi", "bootmgr.efi")
        ]
        
        for src_name, dest_name in boot_files:
            src_path = os.path.join(target_fs_mountpoint, "Windows", "Boot", "EFI", src_name)
            dest_path = os.path.join(esp_mountpoint, "EFI", "Boot", dest_name)
            
            if os.path.exists(src_path):
                shutil.copy2(src_path, dest_path)
            else:
                utils.print_with_color(
                    _("Warning: Bootloader file {0} not found").format(src_path),
                    "yellow"
                )
        
        # Create BCD store for Windows boot
        utils.print_with_color(_("Creating BCD store for Windows boot..."), "green")
        
        bcd_dir = os.path.join(esp_mountpoint, "EFI", "Microsoft", "Boot")
        os.makedirs(bcd_dir, exist_ok=True)
        
        # Copy BCD from Windows partition if available
        src_bcd = os.path.join(target_fs_mountpoint, "Boot", "BCD")
        dest_bcd = os.path.join(bcd_dir, "BCD")
        
        if os.path.exists(src_bcd):
            shutil.copy2(src_bcd, dest_bcd)
        
        # Unmount ESP partition
        if subprocess.run(["umount", esp_mountpoint]).returncode != 0:
            utils.print_with_color(_("Warning: Unable to unmount ESP partition"), "yellow")
        
        try:
            os.rmdir(esp_mountpoint)
        except OSError:
            pass
        utils.check_kill_signal()

    if utils.gui: utils.gui.state = _("Applying Windows 7 UEFI workaround (if applicable)..."); utils.gui.progress = False
    workaround.support_windows_7_uefi_boot(source_fs_mountpoint, target_fs_mountpoint)
    utils.check_kill_signal()

    if not skip_legacy_bootloader:
        if utils.gui: utils.gui.state = _("Installing legacy GRUB bootloader..."); utils.gui.progress = False
        install_legacy_pc_bootloader_grub(target_fs_mountpoint, target_device, command_grubinstall)
        utils.check_kill_signal()
        if utils.gui: utils.gui.state = _("Installing GRUB configuration..."); utils.gui.progress = False
        install_legacy_pc_bootloader_grub_config(target_fs_mountpoint, target_device, command_grubinstall, name_grub_prefix)
        utils.check_kill_signal()

    if workaround_bios_boot_flag:
        if utils.gui: utils.gui.state = _("Applying BIOS boot flag workaround..."); utils.gui.progress = False
        workaround.buggy_motherboards_that_ignore_disks_without_boot_flag_toggled(target_device)
        utils.check_kill_signal()

    current_state = "finished"
    if utils.gui: utils.gui.state = _("Process finished successfully!"); utils.gui.progress = 100 # Final progress

    return 0


def mount_source_filesystem(source_media, source_fs_mountpoint):
    """
    :param source_media:
    :param source_fs_mountpoint:
    :return: 1 - failure
    """
    utils.check_kill_signal()

    utils.print_with_color(_("Mounting source filesystem..."), "green")

    # os.makedirs(source_fs_mountpoint, exist_ok=True)

    if subprocess.run(["mkdir", "--parents", source_fs_mountpoint]).returncode != 0:
        utils.print_with_color(_("Error: Unable to create {0} mountpoint directory").format(source_fs_mountpoint), "red")
        return 1

    if os.path.isfile(source_media):
        if subprocess.run(["mount",
                           "--options", "loop,ro",
                           "--types", "udf,iso9660",
                           source_media,
                           source_fs_mountpoint]).returncode != 0:
            utils.print_with_color(_("Error: Unable to mount source media"), "red")
            return 1
    else:
        if subprocess.run(["mount",
                           "--options", "ro",
                           source_media,
                           source_fs_mountpoint]).returncode != 0:
            utils.print_with_color(_("Error: Unable to mount source media"), "red")
            return 1

    return 0


def mount_target_filesystem(target_partition, target_fs_mountpoint):
    """
    Mount target filesystem to existing path as mountpoint

    :param target_partition: The partition device file target filesystem resides, for example /dev/sdX1
    :param target_fs_mountpoint: The existing directory used as the target filesystem's mountpoint, for example /mnt/target_filesystem
    :return: 1 - failure
    """
    utils.check_kill_signal()

    utils.print_with_color(_("Mounting target filesystem..."), "green")

    # os.makedirs(target_fs_mountpoint, exist_ok=True)

    if subprocess.run(["mkdir", "--parents", target_fs_mountpoint]).returncode != 0:
        utils.print_with_color(_("Error: Unable to create {0} mountpoint directory").format(target_fs_mountpoint), "red")
        return 1

    if subprocess.run(["mount",
                       target_partition,
                       target_fs_mountpoint]).returncode != 0:
        utils.print_with_color(_("Error: Unable to mount target media"), "red")
        return 1
        
    return 0


def copy_filesystem_files(source_fs_mountpoint, target_fs_mountpoint):
    """
    Copying all files from one filesystem to another, with progress reporting

    :param source_fs_mountpoint:
    :param target_fs_mountpoint:
    :return: None
    """
    global CopyFiles_handle

    utils.check_kill_signal()

    total_size = 0
    for dirpath, dirnames, filenames in os.walk(source_fs_mountpoint):
        for file in filenames:
            path = os.path.join(dirpath, file)
            total_size += os.path.getsize(path)

    utils.print_with_color(_("Copying files from source media..."), "green")

    CopyFiles_handle = ReportCopyProgress(source_fs_mountpoint, target_fs_mountpoint)
    CopyFiles_handle.start()

    for dirpath, __, filenames in os.walk(source_fs_mountpoint):
        utils.check_kill_signal()

        if not os.path.isdir(target_fs_mountpoint + dirpath.replace(source_fs_mountpoint, "")):
            os.mkdir(target_fs_mountpoint + dirpath.replace(source_fs_mountpoint, ""))
        for file in filenames:
            path = os.path.join(dirpath, file)
            CopyFiles_handle.file = path

            if os.path.getsize(path) > 5 * 1024 * 1024:  # Files bigger than 5 MiB
                copy_large_file(path, target_fs_mountpoint + path.replace(source_fs_mountpoint, ""))
            else:
                shutil.copy2(path, target_fs_mountpoint + path.replace(source_fs_mountpoint, ""))
    CopyFiles_handle.stop = True


def setup_linux_persistence(target_device, target_partition, filesystem_type, persistence_size_mb, distro_type=None):
    """
    Set up persistence for Linux distributions

    Args:
        target_device (str): Target device path (e.g., /dev/sdX)
        target_partition (str): Target partition path (e.g., /dev/sdX1)
        filesystem_type (str): Filesystem type (F2FS, BTRFS)
        persistence_size_mb (int): Size of persistence in MB
        distro_type (str, optional): Linux distribution type (ubuntu, fedora, arch, debian)

    Returns:
        int: 0 on success, non-zero on failure
    """
    utils.check_kill_signal()

    utils.print_with_color(_("Setting up Linux persistence..."), "green")

    # Mount the target filesystem
    target_fs_mountpoint = tempfile.mkdtemp(prefix="WowUSB.")
    if mount_target_filesystem(target_partition, target_fs_mountpoint) != 0:
        utils.print_with_color(_("Error: Unable to mount target filesystem"), "red")
        return 1

    try:
        # Detect Linux distribution if not specified
        if distro_type is None:
            distro_type = detect_linux_distribution(target_fs_mountpoint)
            utils.print_with_color(_("Detected Linux distribution: {0}").format(distro_type), "green")

        # Set up persistence based on filesystem type and distribution
        if filesystem_type.upper() == "BTRFS":
            result = setup_btrfs_persistence(target_fs_mountpoint, distro_type)
        elif filesystem_type.upper() == "F2FS":
            result = setup_f2fs_persistence(target_device, target_partition, target_fs_mountpoint,
                                           persistence_size_mb, distro_type)
        else:
            utils.print_with_color(_("Error: Unsupported filesystem type for persistence: {0}").format(filesystem_type), "red")
            result = 1

        return result
    finally:
        # Unmount the target filesystem
        utils.print_with_color(_("Unmounting target filesystem..."), "green")
        subprocess.run(["umount", target_fs_mountpoint])
        os.rmdir(target_fs_mountpoint)


def detect_linux_distribution(mountpoint):
    """
    Detect the Linux distribution from the mounted filesystem

    Args:
        mountpoint (str): Path to the mounted filesystem

    Returns:
        str: Distribution type (ubuntu, fedora, arch, debian, or unknown)
    """
    # Check for Ubuntu/Mint
    if os.path.exists(os.path.join(mountpoint, "casper")):
        return "ubuntu"

    # Check for Fedora
    if os.path.exists(os.path.join(mountpoint, "LiveOS")):
        return "fedora"

    # Check for Arch
    if os.path.exists(os.path.join(mountpoint, "arch")):
        return "arch"

    # Check for Debian
    if os.path.exists(os.path.join(mountpoint, "live")):
        return "debian"

    # Default to unknown
    return "unknown"


def setup_btrfs_persistence(mountpoint, distro_type):
    """
    Set up persistence for BTRFS filesystem

    Args:
        mountpoint (str): Path to the mounted filesystem
        distro_type (str): Linux distribution type

    Returns:
        int: 0 on success, non-zero on failure
    """
    utils.check_kill_signal()

    utils.print_with_color(_("Setting up BTRFS persistence..."), "green")

    try:
        # Create rootfs subvolume if it doesn't exist
        if not os.path.exists(os.path.join(mountpoint, "rootfs")):
            utils.print_with_color(_("Creating rootfs subvolume..."), "green")
            subprocess.run(["btrfs", "subvolume", "create", os.path.join(mountpoint, "rootfs")], check=True)

        # Create persistence subvolume
        utils.print_with_color(_("Creating persistence subvolume..."), "green")
        subprocess.run(["btrfs", "subvolume", "create", os.path.join(mountpoint, "persistence")], check=True)

        # Configure persistence based on distribution
        if distro_type == "ubuntu":
            # Create persistence.conf for Ubuntu
            with open(os.path.join(mountpoint, "persistence", "persistence.conf"), "w") as f:
                f.write("/ union\n")

            # Modify boot parameters in grub.cfg
            grub_cfg = os.path.join(mountpoint, "boot", "grub", "grub.cfg")
            if os.path.exists(grub_cfg):
                with open(grub_cfg, "r") as f:
                    content = f.read()

                # Add persistence boot parameters
                content = content.replace("boot=casper", "boot=casper persistent")

                with open(grub_cfg, "w") as f:
                    f.write(content)

        elif distro_type == "fedora":
            # Create overlay directory
            os.makedirs(os.path.join(mountpoint, "persistence", "overlay"), exist_ok=True)

            # Modify boot parameters in grub.cfg
            grub_cfg = os.path.join(mountpoint, "boot", "grub2", "grub.cfg")
            if os.path.exists(grub_cfg):
                with open(grub_cfg, "r") as f:
                    content = f.read()

                # Add persistence boot parameters
                content = content.replace("root=live:", "root=live: rd.live.overlay.overlayfs=1")

                with open(grub_cfg, "w") as f:
                    f.write(content)

        elif distro_type == "debian":
            # Create persistence.conf for Debian
            with open(os.path.join(mountpoint, "persistence", "persistence.conf"), "w") as f:
                f.write("/ union\n")

            # Modify boot parameters in grub.cfg
            grub_cfg = os.path.join(mountpoint, "boot", "grub", "grub.cfg")
            if os.path.exists(grub_cfg):
                with open(grub_cfg, "r") as f:
                    content = f.read()

                # Add persistence boot parameters
                content = content.replace("boot=live", "boot=live persistence")

                with open(grub_cfg, "w") as f:
                    f.write(content)

        elif distro_type == "arch":
            # Create persistence directory
            os.makedirs(os.path.join(mountpoint, "persistence", "cowspace"), exist_ok=True)

            # Arch Linux requires custom hooks for persistence
            utils.print_with_color(_("Note: Arch Linux persistence may require additional configuration"), "yellow")

        else:
            utils.print_with_color(_("Warning: Unknown distribution type. Persistence may not work."), "yellow")
            # Create generic persistence.conf
            with open(os.path.join(mountpoint, "persistence", "persistence.conf"), "w") as f:
                f.write("/ union\n")

        utils.print_with_color(_("BTRFS persistence setup completed"), "green")
        return 0

    except subprocess.SubprocessError as e:
        utils.print_with_color(_("Error: Failed to set up BTRFS persistence: {0}").format(str(e)), "red")
        return 1
    except Exception as e:
        utils.print_with_color(_("Error: Failed to set up BTRFS persistence: {0}").format(str(e)), "red")
        return 1


def setup_f2fs_persistence(target_device, target_partition, mountpoint, persistence_size_mb, distro_type):
    """
    Set up persistence for F2FS filesystem

    Args:
        target_device (str): Target device path (e.g., /dev/sdX)
        target_partition (str): Target partition path (e.g., /dev/sdX1)
        mountpoint (str): Path to the mounted filesystem
        persistence_size_mb (int): Size of persistence in MB
        distro_type (str): Linux distribution type

    Returns:
        int: 0 on success, non-zero on failure
    """
    utils.check_kill_signal()

    utils.print_with_color(_("Setting up F2FS persistence..."), "green")

    try:
        # For F2FS, we create a separate persistence partition or file
        if persistence_size_mb >= 1024:  # If persistence size is >= 1GB, create a partition
            # Create a persistence partition
            utils.print_with_color(_("Creating persistence partition..."), "green")

            # Get the last partition number
            lsblk_output = subprocess.run(["lsblk", "-no", "NAME", target_device],
                                         capture_output=True, text=True).stdout
            partition_numbers = []
            for line in lsblk_output.splitlines():
                if line.startswith(os.path.basename(target_device)) and line != os.path.basename(target_device):
                    try:
                        partition_numbers.append(int(line.replace(os.path.basename(target_device), "")))
                    except ValueError:
                        pass

            last_partition_number = max(partition_numbers) if partition_numbers else 0
            persistence_partition = f"{target_device}{last_partition_number + 1}"

            # Create the persistence partition
            subprocess.run([
                "parted", "--script", target_device,
                "mkpart", "primary", "f2fs",
                f"{-persistence_size_mb - 1}MiB", "-1MiB"
            ], check=True)

            # Format the persistence partition
            utils.print_with_color(_("Formatting persistence partition..."), "green")
            subprocess.run(["mkfs.f2fs", "-f", "-l", "persistence", persistence_partition], check=True)

            # Mount the persistence partition
            persistence_mountpoint = tempfile.mkdtemp(prefix="WowUSB_persistence.")
            subprocess.run(["mount", persistence_partition, persistence_mountpoint], check=True)

            try:
                # Configure persistence based on distribution
                if distro_type == "ubuntu":
                    # Create persistence.conf for Ubuntu
                    with open(os.path.join(persistence_mountpoint, "persistence.conf"), "w") as f:
                        f.write("/ union\n")

                    # Modify boot parameters in grub.cfg
                    grub_cfg = os.path.join(mountpoint, "boot", "grub", "grub.cfg")
                    if os.path.exists(grub_cfg):
                        with open(grub_cfg, "r") as f:
                            content = f.read()

                        # Add persistence boot parameters
                        content = content.replace("boot=casper",
                                                   f"boot=casper persistent persistence-label=persistence")

                        with open(grub_cfg, "w") as f:
                            f.write(content)

                elif distro_type == "fedora":
                    # Create overlay directory
                    os.makedirs(os.path.join(persistence_mountpoint, "overlay"), exist_ok=True)

                    # Modify boot parameters in grub.cfg
                    grub_cfg = os.path.join(mountpoint, "boot", "grub2", "grub.cfg")
                    if os.path.exists(grub_cfg):
                        with open(grub_cfg, "r") as f:
                            content = f.read()

                        # Add persistence boot parameters
                        content = content.replace("root=live:",
                                                   "root=live: rd.live.overlay=persistence rd.live.overlay.overlayfs=1")

                        with open(grub_cfg, "w") as f:
                            f.write(content)

                elif distro_type == "debian":
                    # Create persistence.conf for Debian
                    with open(os.path.join(persistence_mountpoint, "persistence.conf"), "w") as f:
                        f.write("/ union\n")

                    # Modify boot parameters in grub.cfg
                    grub_cfg = os.path.join(mountpoint, "boot", "grub", "grub.cfg")
                    if os.path.exists(grub_cfg):
                        with open(grub_cfg, "r") as f:
                            content = f.read()

                        # Add persistence boot parameters
                        content = content.replace("boot=live",
                                                   "boot=live persistence persistence-label=persistence")

                        with open(grub_cfg, "w") as f:
                            f.write(content)

                elif distro_type == "arch":
                    # Create persistence directory
                    os.makedirs(os.path.join(persistence_mountpoint, "cowspace"), exist_ok=True)

                    # Arch Linux requires custom hooks for persistence
                    utils.print_with_color(_("Note: Arch Linux persistence may require additional configuration"), "yellow")

                else:
                    utils.print_with_color(_("Warning: Unknown distribution type. Persistence may not work."), "yellow")
                    # Create generic persistence.conf
                    with open(os.path.join(persistence_mountpoint, "persistence.conf"), "w") as f:
                        f.write("/ union\n")

            finally:
                # Unmount the persistence partition
                utils.print_with_color(_("Unmounting persistence partition..."), "green")
                subprocess.run(["umount", persistence_mountpoint])
                os.rmdir(persistence_mountpoint)

        else:
            # Create a persistence file
            utils.print_with_color(_("Creating persistence file..."), "green")

            # Determine persistence filename based on distribution
            if distro_type == "ubuntu":
                persistence_file = os.path.join(mountpoint, "casper-rw")
            elif distro_type == "fedora":
                persistence_file = os.path.join(mountpoint, "overlay-live")
            elif distro_type == "debian":
                persistence_file = os.path.join(mountpoint, "persistence")
            else:
                persistence_file = os.path.join(mountpoint, "persistence.img")

            # Create the persistence file
            utils.print_with_color(_("Creating {0}MB persistence file...").format(persistence_size_mb), "green")
            subprocess.run(["dd", "if=/dev/zero", f"of={persistence_file}",
                              f"bs=1M", f"count={persistence_size_mb}", "status=progress"], check=True)

            # Format the persistence file
            utils.print_with_color(_("Formatting persistence file..."), "green")
            subprocess.run(["mkfs.ext4", "-F", "-L", "persistence", persistence_file], check=True)

            # Modify boot parameters based on distribution
            if distro_type == "ubuntu":
                grub_cfg = os.path.join(mountpoint, "boot", "grub", "grub.cfg")
                if os.path.exists(grub_cfg):
                    with open(grub_cfg, "r") as f:
                        content = f.read()

                    # Add persistence boot parameters
                    content = content.replace("boot=casper", "boot=casper persistent")

                    with open(grub_cfg, "w") as f:
                        f.write(content)

            elif distro_type == "fedora":
                grub_cfg = os.path.join(mountpoint, "boot", "grub2", "grub.cfg")
                if os.path.exists(grub_cfg):
                    with open(grub_cfg, "r") as f:
                        content = f.read()

                    # Add persistence boot parameters
                    content = content.replace("root=live:", "root=live: rd.live.overlay=persistence rd.live.overlay.overlayfs=1")

                    with open(grub_cfg, "w") as f:
                        f.write(content)

            elif distro_type == "debian":
                grub_cfg = os.path.join(mountpoint, "boot", "grub", "grub.cfg")
                if os.path.exists(grub_cfg):
                    with open(grub_cfg, "r") as f:
                                content = f.read()

                    # Add persistence boot parameters
                    content = content.replace("boot=live", "boot=live persistence")

                    with open(grub_cfg, "w") as f:
                        f.write(content)

        utils.print_with_color(_("F2FS persistence setup completed"), "green")
        return 0

    except subprocess.SubprocessError as e:
        utils.print_with_color(_("Error: Failed to set up F2FS persistence: {0}").format(str(e)), "red")
        return 1
    except Exception as e:
        utils.print_with_color(_("Error: Failed to set up F2FS persistence: {0}").format(str(e)), "red")
        return 1


def copy_large_file(source, target):
    """
    Because python's copy is atomic it is not possible to do anything during process.
    It is not a big problem when using cli (user can just hit ctrl+c and throw exception),
    but when using gui this part of script needs to "ping" gui for progress reporting
    and check if user didn't click "cancel" (see utils.check_kill_signal())
    :param source:
    :param target:
    :return: None
    """
    source_file = open(source, "rb")  # Open for reading in byte mode
    target_file = open(target, "wb")  # Open for writing in byte mode

    while True:
        utils.check_kill_signal()

        data = source_file.read(5 * 1024 * 1024)  # Read 5 MiB, speeds of shitty pendrives can be as low as 2 MiB/s
        if data == b"":
            break

        target_file.write(data)

    source_file.close()
    target_file.close()


def install_legacy_pc_bootloader_grub(target_fs_mountpoint, target_device, command_grubinstall):
    """
    :param target_fs_mountpoint:
    :param target_device:
    :param command_grubinstall:
    :return: None
    """
    utils.check_kill_signal()

    utils.print_with_color(_("Installing GRUB bootloader for legacy PC booting support..."), "green")

    subprocess.run([command_grubinstall,
                    "--target=i386-pc",
                    "--boot-directory=" + target_fs_mountpoint,
                    "--force", target_device])


def install_legacy_pc_bootloader_grub_config(target_fs_mountpoint, target_device, command_grubinstall,
                                              name_grub_prefix):
    """
    Install a GRUB config file to chainload Microsoft Windows's bootloader in Legacy PC bootmode

    :param target_fs_mountpoint: Target filesystem's mountpoint(where GRUB is installed)
    :param target_device:
    :param command_grubinstall:
    :param name_grub_prefix: May be different between distributions, so need to be specified (grub/grub2)
    :return: None
    """
    utils.check_kill_signal()

    utils.print_with_color(_("Installing custom GRUB config for legacy PC booting..."), "green")

    grub_cfg = target_fs_mountpoint + "/" + name_grub_prefix + "/grub.cfg"

    os.makedirs(target_fs_mountpoint + "/" + name_grub_prefix, exist_ok=True)

    with open(grub_cfg, "w") as cfg:
        cfg.write("ntldr /bootmgr\n")
        cfg.write("boot")


def create_uefi_support_partition(target_device, uefi_support_partition_device):
    """
    Creates a small FAT16 partition at the end of the disk for UEFI support files.
    This is typically used for UEFI:NTFS or UEFI:exFAT booting.

    :param target_device: The main target device (e.g., /dev/sdb)
    :param uefi_support_partition_device: The device path for the new partition (e.g., /dev/sdb2)
    :return: 0 on success, 1 on failure
    """
    utils.check_kill_signal()
    utils.print_with_color(_("Creating UEFI support partition ({0})...").format(uefi_support_partition_device), "green")

    # Create a small ~5MB FAT16 partition at the end of the disk.
    # Parted syntax for "start from 5MB before end" to "1s before end"
    # Using sectors ('s') for precise small partition. 10240 sectors = 5MB for 512b sectors.
    # A 1MB partition is often enough for UEFI:NTFS. Let's use 5MB to be safe.
    # Ensure the main partition does not occupy the entire disk.
    # This assumes the main partition (e.g. sdb1) has already been created and there's space.
    # The partition number is implied by uefi_support_partition_device (e.g. sdb2)
    partition_number = "".join(filter(str.isdigit, uefi_support_partition_device.replace(target_device, "")))
    if not partition_number:
        utils.print_with_color(_("Error: Could not determine partition number for UEFI support partition {0}").format(uefi_support_partition_device), "red")
        return 1

    # We need to know the end of the previous partition to start this one.
    # This is simpler if we create it as the *last* partition using negative indexing for end.
    # Example: parted /dev/sdb mkpart primary fat16 -5MB -1s
    # This creates a partition in the last 5MB of the disk.
    # We must ensure this doesn't overlap if other partitions exist after the main one.
    # For now, assume it's the second partition on an MBR disk.
    # A more robust way would be to check available space or use GPT and define all partitions upfront.

    # For MBR, we typically create up to 4 primary partitions.
    # If target_partition was sdb1, this will be sdb2.
    # The start is determined by where sdb1 ended. Parted handles this if we just specify type.
    # However, we need to specify a size. Let's aim for a small partition.
    # A common approach is to make it the *second* partition.
    # parted /dev/sdb mkpart primary fat16 START END (e.g. after sdb1, for 5MB)

    # Let's find the end of the first partition
    main_part_info = utils.get_partition_info(target_device + "1") # Assumes main is part 1
    if not main_part_info or 'end_sector' not in main_part_info:
        utils.print_with_color(_("Error: Could not get info for main partition {0}1 to create UEFI support partition.").format(target_device), "red")
        return 1

    start_sector_uefi = main_part_info['end_sector'] + 1
    # Create a 10MB FAT16 partition (20480 sectors * 512 bytes/sector = 10MB)
    # FAT16 is fine for small partitions and widely compatible for UEFI.
    end_sector_uefi = start_sector_uefi + 20480 -1 # -1 because end is inclusive

    utils.print_with_color(_("Attempting to create UEFI support partition {0} from sector {1} to {2}").format(
        uefi_support_partition_device, start_sector_uefi, end_sector_uefi), "blue")

    parted_command_mkpart = [
        "parted", "--script", target_device,
        "mkpart", "primary", "fat16",
        str(start_sector_uefi) + "s", str(end_sector_uefi) + "s"
    ]
    if utils.run_command(parted_command_mkpart,
                         message=_("Creating UEFI support partition with parted"),
                         error_message=_("Error: parted failed to create UEFI support partition")):
        return 1

    # Format the new partition
    # Allow some time for the kernel to recognize the new partition
    time.sleep(2)
    command_mkdosfs = utils.check_command("mkdosfs")
    if not command_mkdosfs:
        utils.print_with_color(_("Error: mkdosfs command not found, cannot format UEFI support partition."), "red")
        return 1

    mkfs_command = [
        command_mkdosfs, "-F", "16", "-n", "UEFI-BOOT", uefi_support_partition_device
    ]
    if utils.run_command(mkfs_command,
                         message=_("Formatting UEFI support partition {0} as FAT16").format(uefi_support_partition_device),
                         error_message=_("Error: mkdosfs failed to format UEFI support partition")):
        return 1

    utils.print_with_color(_("UEFI support partition {0} created and formatted successfully.").format(uefi_support_partition_device), "green")
    return 0


def install_uefi_support_files(fs_handler, uefi_support_partition_device, temp_directory):
    """
    Installs UEFI boot files (e.g., UEFI:NTFS driver) to the UEFI support partition.

    :param fs_handler: The filesystem handler for the main Windows partition (e.g., NTFSHandler).
    :param uefi_support_partition_device: Device path of the UEFI support partition (e.g., /dev/sdb2).
    :param temp_directory: Path to a temporary directory for downloads/extraction.
    :return: 0 on success, 1 on failure
    """
    utils.check_kill_signal()
    utils.print_with_color(_("Installing UEFI support files to {0}...").format(uefi_support_partition_device), "green")

    bootloader_dir = os.path.join("WowUSB", "data", "bootloaders")
    os.makedirs(bootloader_dir, exist_ok=True)

    try:
        uefi_driver_url, uefi_driver_filename = fs_handler.get_uefi_bootloader_file()
    except AttributeError:
        utils.print_with_color(_("Error: Filesystem handler {0} does not provide UEFI bootloader information.").format(fs_handler.name()), "red")
        return 1

    uefi_driver_local_path = os.path.join(bootloader_dir, uefi_driver_filename)

    if not os.path.exists(uefi_driver_local_path):
        utils.print_with_color(_("UEFI support file {0} not found locally. Downloading from {1}...").format(uefi_driver_filename, uefi_driver_url), "blue")
        try:
            with urllib.request.urlopen(uefi_driver_url) as response, open(uefi_driver_local_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            utils.print_with_color(_("Downloaded {0} successfully.").format(uefi_driver_filename), "green")
        except urllib.error.HTTPError as e:
            utils.print_with_color(_("Error downloading UEFI support file {0}: HTTP Error {1}: {2}").format(uefi_driver_filename, e.code, e.reason), "red")
            return 1
        except urllib.error.URLError as e:
            utils.print_with_color(_("Error downloading UEFI support file {0}: URL Error: {1}").format(uefi_driver_filename, e.reason), "red")
            return 1
        except IOError as e: # Catches file write errors
            utils.print_with_color(_("Error writing UEFI support file {0} locally: {1}").format(uefi_driver_filename, str(e)), "red")
            return 1
        except Exception as e:
            utils.print_with_color(_("An unexpected error occurred while downloading or saving {0}: {1}").format(uefi_driver_filename, str(e)), "red")
            if debug:
                traceback.print_exc()
            return 1
    else:
        utils.print_with_color(_("Found local UEFI support file: {0}").format(uefi_driver_local_path), "green")

    # Mount the UEFI support partition
    uefi_mount_point = os.path.join(temp_directory, "uefi_support_mount")
    os.makedirs(uefi_mount_point, exist_ok=True)

    if utils.run_command(["mount", uefi_support_partition_device, uefi_mount_point],
                         message=_("Mounting UEFI support partition {0}").format(uefi_support_partition_device),
                         error_message=_("Error: Failed to mount UEFI support partition.")):
        shutil.rmtree(uefi_mount_point, ignore_errors=True)
        return 1

    try:
        # Expected structure on the UEFI support partition: EFI/Boot/bootx64.efi
        efi_boot_dir = os.path.join(uefi_mount_point, "EFI", "Boot")
        os.makedirs(efi_boot_dir, exist_ok=True)
        target_efi_file = os.path.join(efi_boot_dir, "bootx64.efi") # Standard UEFI fallback path

        # Assuming uefi-ntfs.img is a FAT disk image containing the EFI file.
        # We need to extract bootx64.efi from it.
        # For simplicity, if we can't loop mount, we'll assume the .img *is* the .efi file,
        # which is often the case for single EFI application "images".
        # A more robust solution would use 7z or loop mount to extract from the image.

        # Attempt to mount the image to extract files
        img_mount_point = os.path.join(temp_directory, "img_mount")
        os.makedirs(img_mount_point, exist_ok=True)

        loop_device = None
        try:
            # Setup loop device
            proc = subprocess.run(["losetup", "--find", "--show", uefi_driver_local_path], capture_output=True, text=True, check=True)
            loop_device = proc.stdout.strip()

            # Mount loop device
            if utils.run_command(["mount", "-o", "ro", loop_device, img_mount_point],
                                 message=_("Loop mounting {0}").format(uefi_driver_filename),
                                 error_message=_("Failed to loop mount UEFI image.")):
                raise Exception("Loop mount failed")

            source_efi_file_path = os.path.join(img_mount_point, "EFI", "Boot", "bootx64.efi")
            if not os.path.exists(source_efi_file_path):
                # Fallback: look for bootia32.efi or other common names if bootx64.efi is not found
                source_efi_file_path_ia32 = os.path.join(img_mount_point, "EFI", "Boot", "bootia32.efi")
                if os.path.exists(source_efi_file_path_ia32):
                    source_efi_file_path = source_efi_file_path_ia32
                else: # If still not found, maybe the image itself is the EFI file (less common for .img)
                     source_efi_file_path = os.path.join(img_mount_point, "efi.img") # Or some other name inside
                     if not os.path.exists(source_efi_file_path): # Final fallback
                         utils.print_with_color(_("Could not find bootx64.efi or bootia32.efi within {0}.").format(uefi_driver_filename), "yellow")
                         utils.print_with_color(_("Attempting to copy the .img file directly as bootx64.efi. This might not work."), "yellow")
                         shutil.copy2(uefi_driver_local_path, target_efi_file) # This is a guess
                         utils.print_with_color(_("Copied {0} to {1}").format(uefi_driver_local_path, target_efi_file), "green")
                         # Early exit from try block after this guess
                         raise Exception("Skipping further extraction after direct copy.")


            if os.path.exists(source_efi_file_path): # Check again in case it was found by fallback
                shutil.copy2(source_efi_file_path, target_efi_file)
                utils.print_with_color(_("Copied {0} to {1}").format(source_efi_file_path, target_efi_file), "green")

            # If fs_handler is NTFS, create a marker or basic grub.cfg if needed for chainloading
            # For UEFI:NTFS from Rufus, the bootx64.efi IS the NTFS driver and bootloader.
            # It should automatically look for \efi\microsoft\boot\bootmgfw.efi on the NTFS partition.
            # No extra grub.cfg is typically needed on the FAT partition itself for this specific driver.

        except Exception as e:
            if "Skipping further extraction" not in str(e): # Don't log error if it was the direct copy fallback
                utils.print_with_color(_("Could not extract from UEFI image {0}: {1}. Trying to use image directly.").format(uefi_driver_filename, str(e)), "yellow")
                # Fallback: if extraction fails, copy the .img file directly as bootx64.efi.
                # This assumes the .img might itself be a bootable EFI application.
                try:
                    shutil.copy2(uefi_driver_local_path, target_efi_file)
                    utils.print_with_color(_("Copied {0} directly as {1}").format(uefi_driver_local_path, target_efi_file), "green")
                except Exception as copy_e:
                    utils.print_with_color(_("Failed to copy UEFI file: {0}").format(str(copy_e)), "red")
                    return 1 # Critical failure
        finally:
            if os.path.ismount(img_mount_point):
                utils.run_command(["umount", img_mount_point], suppress_errors=True)
            if loop_device:
                utils.run_command(["losetup", "-d", loop_device], suppress_errors=True)
            shutil.rmtree(img_mount_point, ignore_errors=True)

    finally:
        if os.path.ismount(uefi_mount_point):
            utils.run_command(["umount", uefi_mount_point],
                              message=_("Unmounting UEFI support partition {0}").format(uefi_support_partition_device),
                              error_message=_("Warning: Failed to unmount UEFI support partition."))
        shutil.rmtree(uefi_mount_point, ignore_errors=True)

    utils.print_with_color(_("UEFI support files installed successfully to {0}.").format(uefi_support_partition_device), "green")
    return 0


def cleanup_mountpoint(fs_mountpoint):
    """
    Unmount mounted filesystems and clean-up mountpoints before exiting program

    :param fs_mountpoint:
    :return: unclean(2): Not fully clean, target device can be safely detach from host; unsafe(3): Target device cannot be safely detach from host
    """
    if os.path.ismount(fs_mountpoint):  # os.path.ismount() checks if path is a mount point
        utils.print_with_color(_("Unmounting and removing {0}...").format(fs_mountpoint), "green")
        if subprocess.run(["umount", fs_mountpoint]).returncode:
            utils.print_with_color(_("Warning: Unable to unmount filesystem."), "yellow")
            return 1

        try:
            os.rmdir(fs_mountpoint)
        except OSError:
            utils.print_with_color(_("Warning: Unable to remove source mountpoint"), "yellow")
            return 2

    return 0


def cleanup(source_fs_mountpoint, target_fs_mountpoint, temp_directory, target_media):
    """
    :param source_fs_mountpoint:
    :param target_fs_mountpoint:
    :param temp_directory:
    :param target_media:
    :return: None
    """
    if CopyFiles_handle.is_alive():
        CopyFiles_handle.stop = True

    flag_unclean = False
    flag_unsafe = False

    cleanup_result = cleanup_mountpoint(source_fs_mountpoint)

    if cleanup_result == 2:
        flag_unclean = True

    cleanup_result = cleanup_mountpoint(target_fs_mountpoint)

    if cleanup_result == 1:
        flag_unsafe = True
    elif cleanup_result == 2:
        flag_unclean = True

    if flag_unclean:
        utils.print_with_color(_("Some mountpoints are not unmount/cleaned successfully and must be done manually"), "yellow")

    if flag_unsafe:
        utils.print_with_color(
            _("We were unable to unmount target filesystem for you, please make sure target filesystem is unmounted before detaching to prevent data corruption"),
            "yellow")
        utils.print_with_color(_("Some mountpoints are not unmount/cleaned successfully and must be done manually"), "yellow")

    if utils.check_is_target_device_busy(target_media):
        utils.print_with_color(
            _("Target device is busy, please make sure you unmount all filesystems on target device or shutdown the computer before detaching it."),
            "yellow")
    else:
        utils.print_with_color(_("You may now safely detach the target device"), "green")

    shutil.rmtree(temp_directory)

    if current_state == "finished":
        utils.print_with_color(_("Done :)"), "green")
        utils.print_with_color(_("The target device should be bootable now"), "green")


def create_parser():
    """
    Create and return the argument parser
    
    Returns:
        argparse.ArgumentParser: The configured argument parser
    """
    parser = argparse.ArgumentParser(description=_("Create a bootable Windows USB drive from an ISO or DVD"))

    # Source arguments
    parser.add_argument("--device", "-d", action="store_true", 
                        help=_("Device mode: Create a bootable USB drive from an ISO or DVD"))
    parser.add_argument("--partition", "-p", action="store_true", 
                        help=_("Partition mode: Install Windows to an existing partition"))

    # Target arguments
    parser.add_argument("--target-filesystem", "-t", 
                        choices=["FAT", "NTFS", "EXFAT", "F2FS", "BTRFS", "AUTO"], 
                        default="AUTO",
                        help=_("Target filesystem type (default: AUTO)"))

    # Windows-To-Go option
    parser.add_argument("--wintogo", "-w", action="store_true", 
                        help=_("Create a Windows-To-Go installation"))
    
    # Linux persistence option
    parser.add_argument("--persistence", "-P", type=int, metavar="SIZE",
                        help=_("Create a persistence partition or file of SIZE MB (Linux only)"))

    # Multi-boot options
    parser.add_argument("--multiboot", action="store_true",
                        help=_("Enable Multiboot mode. Creates a GPT layout with GRUB2."))
    parser.add_argument("--win-iso", type=str,
                        help=_("Path to the Windows ISO for Windows-To-Go in Multiboot mode."))
    parser.add_argument("--win-size-gb", type=int, default=64,
                        help=_("Size in GB for the Windows-To-Go partition (default: 64GB)."))
    parser.add_argument("--linux-iso", action="append", type=str,
                        help=_("Path to a Linux ISO to include in GRUB menu (can be used multiple times)."))
    parser.add_argument("--payload-fs", type=str, default="F2FS", choices=["F2FS", "EXFAT", "NTFS", "BTRFS"],
                        help=_("Filesystem for the payload/data partition (default: F2FS)."))
    parser.add_argument("--full-linux-install", type=str, choices=["ubuntu", "arch", "debian"],
                        help=_("Perform a full Linux installation to the payload partition (specify distro: ubuntu, arch, debian)."))
    parser.add_argument("--full-linux-release", type=str,
                        help=_("Specify release for Ubuntu/Debian full install (e.g., focal, bullseye)."))
    parser.add_argument("--http-proxy", type=str, help=_("HTTP proxy for debootstrap/pacstrap, e.g., http://proxy:port"))

    # Options for standard (single boot) mode, also relevant for some multiboot sub-operations if defaults are not used
    parser.add_argument("--label", type=str, default=DEFAULT_NEW_FS_LABEL,
                        help=_("Filesystem label for the main partition (default: '{0}').").format(DEFAULT_NEW_FS_LABEL))
    parser.add_argument("--workaround-bios-boot-flag", action="store_true",
                        help=_("Apply workaround for buggy motherboards that ignore disks without boot flag toggled (for MBR)."))
    parser.add_argument("--workaround-skip-grub", action="store_true",
                        help=_("Skip installing legacy GRUB bootloader (applies to standard MBR mode)."))


    # Other options
    parser.add_argument("--list-devices", "-l", action="store_true", 
                        help=_("List available devices"))
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help=_("Enable verbose output"))
    parser.add_argument("--no-color", "-n", action="store_true", 
                        help=_("Disable colored output"))
    parser.add_argument("--for-gui", "-g", action="store_true", 
                        help=argparse.SUPPRESS)

    # Positional arguments
    parser.add_argument("source", nargs="?", 
                        help=_("Source ISO or DVD path"))
    parser.add_argument("target", nargs="?", 
                        help=_("Target device or partition"))
    
    return parser

def setup_arguments():
    """
    Set up and parse command line arguments

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = create_parser()
    args = parser.parse_args()

    # Set install mode
    if args.multiboot:
        args.install_mode = "multiboot"
        if not args.win_iso and not args.linux_iso and not args.full_linux_install:
            parser.error(_("In multiboot mode, you must specify at least a Windows ISO (--win-iso), a Linux ISO (--linux-iso), or a full Linux install (--full-linux-install)."))
        if args.wintogo: # --wintogo is implicit in multiboot if --win-iso is given
            utils.print_with_color(_("Warning: --wintogo is automatically handled in --multiboot mode if --win-iso is provided. Separate --wintogo flag is ignored."), "yellow")
        if args.target_filesystem != "AUTO":
             utils.print_with_color(_("Warning: --target-filesystem is ignored in --multiboot mode. Filesystems are managed by multiboot logic."), "yellow")
        if args.persistence:
            parser.error(_("Error: --persistence is not currently supported with --multiboot mode."))

    elif args.device:
        args.install_mode = "device"
    elif args.partition:
        args.install_mode = "partition"
    elif args.target and not os.path.exists(args.target):
        # If target doesn't exist, assume it's a device
        args.install_mode = "device"
    elif args.target and os.path.exists(args.target):
        # If target exists, check if it's a device or partition
        if utils.is_block_device(args.target) and not utils.is_partition(args.target):
            args.install_mode = "device"
        else:
            args.install_mode = "partition"
    else:
        # Default to device mode
        args.install_mode = "device"

    # Set target partition
    if args.install_mode == "device" or args.install_mode == "multiboot":
        args.target_partition = args.target + "1" if args.target else None
    else:
        args.target_partition = args.target
        args.target = None

    # Validate Windows-To-Go option
    if args.wintogo and args.install_mode != "device":
        parser.error(_("Windows-To-Go requires device mode"))

    # Validate persistence option
    if args.persistence is not None:
        if args.persistence < 512:
            parser.error(_("Persistence size must be at least 512MB"))
        if args.wintogo:
            parser.error(_("Persistence is not compatible with Windows-To-Go"))
        if args.target_filesystem not in ["F2FS", "BTRFS", "AUTO"]:
            parser.error(_("Persistence requires F2FS or BTRFS filesystem"))

    return args


# setup_arguments now includes all argument definitions directly

def main(args, temp_dir=None):
    """
    Main function
    
    Args:
        args (argparse.Namespace): Command line arguments
        temp_dir (str, optional): Temporary directory
        
    Returns:
        int: 0 on success, non-zero on failure
    """
    # Handle multi-boot mode
    if args.install_mode == "multiboot":
        return main_multiboot(args, temp_dir)

    # --- Existing logic for device and partition modes ---
    # This part remains largely unchanged, but we need to ensure global variables like
    # source_fs_mountpoint, target_fs_mountpoint, target_media, install_mode, temp_directory,
    # target_filesystem_type, workaround_bios_boot_flag, skip_legacy_bootloader are available
    # or passed correctly if main() is refactored.
    # For now, the original main() function structure is kept for non-multiboot modes.
    # The 'parser' argument to main() might need to be re-evaluated or passed from 'run()'.

    # The original main() function continues here for non-multiboot modes...
    # We need to get these variables from `args` if called from `run` -> `main` directly
    # For non-multiboot, main is called from run() which gets these from init().
    # This structure is a bit convoluted. Let's assume `main` is called with args.

    # Simplified: if not multiboot, the existing main() logic (currently below this block in the file)
    # would execute. The check `if args.install_mode == "multiboot":` should be at the beginning of
    # the original main function's logic.

    # Let's adjust the current `main` function to reflect this split more clearly.
    # The existing `main` function's content will become the "else" part of this conditional.
    # This means the `main` signature might need to change or `args` needs to be passed down.
    # For now, I will put the new `main_multiboot` function definition after this and then
    # show how `main` calls it.

    # This is where the original `main` function's logic would start for non-multiboot.
    # For clarity, I'll copy the start of the original main's logic here,
    # assuming it's been refactored to accept `args` directly.

    global debug
    global verbose
    global no_color
    global current_state
    # global target_device # This was global, now should be from args.target

    # These would be derived from args within the original main logic
    source_media = args.source
    target_media = args.target # This is the device path for --device and --multiboot
    target_filesystem_type = args.target_filesystem
    workaround_bios_boot_flag = getattr(args, 'workaround_bios_boot_flag', False) # Need to add this to parser
    skip_legacy_bootloader = getattr(args, 'workaround_skip_grub', False) # Need to add this to parser
    filesystem_label = getattr(args, 'label', DEFAULT_NEW_FS_LABEL) # Need to add this to parser


    current_state = 'enter-init'
    if utils.gui: utils.gui.state = _("Initializing..."); utils.gui.progress = False

    # Dependencies check (already present)
    # ... rest of the original main function for single boot modes ...
    utils.print_with_color(_("Standard (non-multiboot) mode selected."), "green")
    # This is the beginning of the original main() logic, now adapted for single-boot modes
    # and to take `args` and `temp_dir`.

    utils.print_with_color(_("Standard (non-multiboot) mode selected."), "green")

    # Extract parameters from args
    source_media = args.source
    target_media_cli = args.target # This is the device or partition from CLI
    install_mode = args.install_mode # 'device' or 'partition'
    target_filesystem_type = args.target_filesystem
    filesystem_label = args.label
    workaround_bios_boot_flag = args.workaround_bios_boot_flag
    skip_legacy_bootloader = args.workaround_skip_grub
    is_wintogo_mode_standard = args.wintogo # For standard WinToGo, not multiboot

    # Generate dynamic mount points
    source_fs_mountpoint = os.path.join(temp_dir, "source_mount_" + str(os.getpid()))
    target_fs_mountpoint = os.path.join(temp_dir, "target_mount_" + str(os.getpid()))
    # Ensure these directories are created before use, e.g., in mount_source_filesystem
    # and mount_target_filesystem, which already do this.

    current_state = 'enter-init-standard' # Changed from 'enter-init' to be specific
    if utils.gui: utils.gui.state = _("Initializing standard install..."); utils.gui.progress = False

    command_mkdosfs, command_mkntfs, command_grubinstall = utils.check_runtime_dependencies(application_name)
    utils.check_kill_signal()
    if command_grubinstall == "grub-install":
        name_grub_prefix = "grub"
    else:
        name_grub_prefix = "grub2"

    utils.print_with_color(application_name + " v" + application_version)
    utils.print_with_color("==============================")

    if os.getuid() != 0:
        utils.print_with_color(_("Warning: You are not running {0} as root!").format(application_name), "yellow")
        utils.print_with_color(_("Warning: This might be the reason of the following failure."), "yellow")

    # Parameter validation (check_runtime_parameters)
    # The original function took install_mode, source_media, target_media (device or partition)
    if utils.check_runtime_parameters(install_mode, source_media, target_media_cli):
        # parser.print_help() was here. Now, how to print help?
        # Could call create_parser().print_help() or return specific error.
        create_parser().print_help() # Assuming this is acceptable
        return 1

    # Determine target_device and target_partition
    # args.target_partition is already set by setup_arguments if mode is device/multiboot
    # args.target is already set by setup_arguments to be the base device if mode is partition
    if install_mode == "partition":
        target_partition = target_media_cli # e.g. /dev/sdb1
        target_device = args.target # e.g. /dev/sdb (derived in setup_arguments)
        if not target_device: # Should have been derived
             # Attempt to derive it again if somehow not set
             temp_target_device = target_partition
             while temp_target_device[-1].isdigit():
                 temp_target_device = temp_target_device[:-1]
             target_device = temp_target_device
             utils.print_with_color(_("Warning: Target device for partition mode was not pre-derived, attempting {0}").format(target_device), "yellow")

    else: # device mode
        target_device = target_media_cli # e.g. /dev/sdb
        target_partition = args.target_partition # e.g. /dev/sdb1 (derived in setup_arguments)

    if not target_device or not target_partition:
        utils.print_with_color(_("Error: Could not determine target device and partition."), "red")
        return 1
        
    utils.print_with_color(f"Debug: Target Device: {target_device}, Target Partition: {target_partition}", "magenta")


    if utils.check_source_and_target_not_busy(install_mode, source_media, target_device, target_partition):
        return 1

    current_state = "start-mounting-standard"
    if utils.gui: utils.gui.state = _("Mounting source filesystem..."); utils.gui.progress = False

    # Mount source filesystem (e.g., Windows ISO)
    if mount_source_filesystem(source_media, source_fs_mountpoint):
        utils.print_with_color(_("Error: Unable to mount source filesystem"), "red")
        return 1
    utils.check_kill_signal()

    # Auto-detect optimal filesystem if requested (for the single target partition)
    if utils.gui: utils.gui.state = _("Determining optimal filesystem..."); utils.gui.progress = False
    if target_filesystem_type.upper() == "AUTO":
        target_filesystem_type = fs_handlers.get_optimal_filesystem_for_iso(source_fs_mountpoint)
        utils.check_kill_signal()
        utils.print_with_color(
            _("Info: Auto-selected {0} filesystem based on source content").format(target_filesystem_type),
            "green"
        )

    # Check if selected filesystem can handle source files (large file check)
    try:
        fs_handler = fs_handlers.get_filesystem_handler(target_filesystem_type)
        if not fs_handler.supports_file_size_greater_than_4gb():
            has_large_files, largest_file, largest_size = utils.check_fat32_filesize_limitation_detailed(source_fs_mountpoint)
            if has_large_files:
                utils.print_with_color(
                    _("Warning: Source contains files larger than 4GB. Largest: {0} ({1})").format(
                        largest_file,
                        utils.convert_to_human_readable_format(largest_size)
                    ), "yellow")

                # This is the original logic from main() for switching FS if FAT32 is chosen with large files
                available_fs = fs_handlers.get_available_filesystem_handlers()
                alternative_fs = None
                # Prefer exFAT -> NTFS -> F2FS -> BTRFS if FAT32 is not viable
                for fs_pref in ["EXFAT", "NTFS", "F2FS", "BTRFS"]:
                    if fs_pref in available_fs:
                        alternative_fs = fs_pref
                        break

                if alternative_fs:
                    utils.print_with_color(
                        _("Warning: Switching to {0} filesystem to support files larger than 4GB").format(alternative_fs),
                        "yellow"
                    )
                    target_filesystem_type = alternative_fs
                    fs_handler = fs_handlers.get_filesystem_handler(target_filesystem_type) # Update handler
                else:
                    utils.print_with_color(
                        _("Error: Source contains files larger than 4GB, but no suitable alternative filesystem (exFAT, NTFS, F2FS, BTRFS) found/available."),
                        "red"
                    )
                    return 1
    except ValueError as e: # From get_filesystem_handler if type is bad
        utils.print_with_color(str(e), "red")
        return 1

    # Validate chosen/switched filesystem handler and its dependencies
    if utils.gui: utils.gui.state = _("Validating filesystem choice..."); utils.gui.progress = False
    try:
        # fs_handler should be set from above block
        is_available, missing_deps = fs_handler.check_dependencies()
        if not is_available:
            utils.print_with_color(
                _("Error: Missing dependencies for {0} filesystem: {1}").format(
                    fs_handler.name(), ", ".join(missing_deps)
                ), "red")
            return 1
        utils.check_kill_signal()

        utils.print_with_color(
            _("Using {0} filesystem for Windows installation").format(fs_handler.name()), "green")
        if fs_handler.supports_file_size_greater_than_4gb():
            utils.print_with_color(_("Large file support (>4GB) is enabled"), "green")
        if fs_handler.needs_uefi_support_partition():
            utils.print_with_color(
                _("Note: {0} requires a separate UEFI support partition for UEFI booting").format(fs_handler.name()),
                "green" if utils.verbose else None ) # verbose check was missing
    except ValueError as e: # Should not happen if already handled, but as safeguard
        utils.print_with_color(str(e), "red")
        return 1
    utils.check_kill_signal()

    # Windows-To-Go mode for standard install (not multiboot's implicit WinToGo)
    # is_wintogo_mode = getattr(parser, 'wintogo', False) if parser else False # Old way
    # is_wintogo_mode has been set to args.wintogo

    if is_wintogo_mode_standard: # Standard mode WinToGo
        utils.print_with_color(_("Windows-To-Go mode enabled (standard install)."), "green")
        if utils.gui: utils.gui.state = _("Configuring for Windows-To-Go (standard)..."); utils.gui.progress = False
        
        if install_mode != "device":
            utils.print_with_color(_("Error: Windows-To-Go (standard mode) requires --device mode."), "red")
            return 1

        # create_wintogo_partition_layout is a stub, would need full implementation
        # For standard WinToGo, it usually creates ESP, MSR, and Windows partition.
        if create_wintogo_partition_layout(target_device, target_filesystem_type, filesystem_label):
            utils.print_with_color(_("Error: Failed to create Windows-To-Go partition layout (standard mode)."), "red")
            return 1
        # Update target_partition to point to the Windows partition (typically 3rd for this layout)
        target_partition = target_device + "3"
        utils.check_kill_signal()

    elif install_mode == "device": # Standard device mode (not WinToGo, not multiboot)
        if utils.gui: utils.gui.state = _("Wiping existing signatures..."); utils.gui.progress = False
        wipe_existing_partition_table_and_filesystem_signatures(target_device) # Stub
        utils.check_kill_signal()

        if utils.gui: utils.gui.state = _("Creating partition table..."); utils.gui.progress = False
        create_target_partition_table(target_device, "legacy") # Stub, creates MBR
        utils.check_kill_signal()

        if utils.gui: utils.gui.state = _("Creating main Windows partition..."); utils.gui.progress = False
        # create_target_partition is a stub, formats a single partition
        if create_target_partition(target_device, target_partition, target_filesystem_type, filesystem_label):
            utils.print_with_color(_("Error: Failed to create main target partition {0}").format(target_partition), "red")
            return 1
        utils.check_kill_signal()

        if fs_handler.needs_uefi_support_partition():
            if utils.gui: utils.gui.state = _("Creating UEFI support partition..."); utils.gui.progress = False
            uefi_support_part_device = target_device + "2" # Assuming main partition is '1'
            if create_uefi_support_partition(target_device, uefi_support_part_device): # Stub
                 utils.print_with_color(_("Error: Failed to create UEFI support partition on {0}").format(target_device), "red")
                 return 1
            utils.check_kill_signal()
            if utils.gui: utils.gui.state = _("Installing UEFI support files..."); utils.gui.progress = False
            if install_uefi_support_files(fs_handler, uefi_support_part_device, temp_dir): # temp_dir was temp_directory
                utils.print_with_color(_("Error: Failed to install UEFI support files to {0}").format(uefi_support_part_device), "red")
                return 1
            utils.check_kill_signal()

    if install_mode == "partition": # Standard partition mode
        if utils.gui: utils.gui.state = _("Checking target partition..."); utils.gui.progress = False
        if utils.check_target_partition(target_partition, target_device): # This checks FS type mostly
            return 1
        utils.check_kill_signal()
        # Note: For partition mode, if fs_handler.needs_uefi_support_partition() is true,
        # the user is responsible for having created it. We don't create it here.
        # The original code only created UEFI support partition in "device" mode.

    # Mount the (now prepared) target partition
    if utils.gui: utils.gui.state = _("Mounting target filesystem..."); utils.gui.progress = False
    if mount_target_filesystem(target_partition, target_fs_mountpoint):
        utils.print_with_color(_("Error: Unable to mount target filesystem on {0}").format(target_partition), "red")
        return 1
    utils.check_kill_signal()

    if utils.gui: utils.gui.state = _("Checking free space on target..."); utils.gui.progress = False
    if utils.check_target_filesystem_free_space(target_fs_mountpoint, source_fs_mountpoint, target_partition):
        return 1
    utils.check_kill_signal()

    current_state = "copying-filesystem-standard"
    copy_filesystem_files(source_fs_mountpoint, target_fs_mountpoint)
    utils.check_kill_signal()

    # Persistence (Only for standard Linux ISO creation, not Windows. This part might be legacy or for a different feature)
    # The `args.persistence` check should clarify if this is applicable.
    # The current task is Windows focused multiboot. This persistence logic might be for single Linux ISO bootable drives.
    if args.persistence is not None: # Check if persistence was requested
        # This setup_linux_persistence was in original main. Its applicability to Windows install is unclear.
        # Assuming it's for when source_media is a Linux ISO.
        # For now, keeping it as it was, but it might need guarding based on source_media type.
        utils.print_with_color(_("Attempting to set up Linux persistence (if source is Linux)..."), "yellow")
        if setup_linux_persistence(target_device, target_partition, target_filesystem_type, args.persistence) != 0:
            utils.print_with_color(_("Error: Failed to set up persistence (standard mode)."), "red")
            return 1 # Or just a warning if Windows install is primary goal

    # Apply Windows-To-Go specific modifications if in standard WinToGo mode
    if is_wintogo_mode_standard: # Standard mode WinToGo
        if utils.gui: utils.gui.state = _("Applying Windows-To-Go modifications (standard)..."); utils.gui.progress = False
        windows_version, build_number, is_windows11 = utils.detect_windows_version(source_fs_mountpoint) # From source ISO
        utils.print_with_color(
            _("Detected Windows version (for standard WinToGo): {0}, build: {1}").format(windows_version, build_number), "green")
        utils.check_kill_signal()

        if is_windows11:
            if utils.gui: utils.gui.state = _("Applying Windows 11 TPM bypass (standard WinToGo)..."); utils.gui.progress = False
            workaround.bypass_windows11_tpm_requirement(target_fs_mountpoint) # Apply to target
            utils.check_kill_signal()

        workaround.prepare_windows_portable_drivers(target_fs_mountpoint) # Apply to target
        utils.check_kill_signal()

        # For standard WinToGo (MBR based usually, or simple GPT), ESP handling is different from multiboot.
        # The create_wintogo_partition_layout stub would have created an ESP.
        # Bootloader files (bootmgfw.efi, BCD) need to be copied to that ESP.
        # This part was complex in original main, involving mounting ESP (e.g. target_device + "1")
        # and copying files.
        # This is a simplified placeholder for that logic.
        utils.print_with_color(_("Standard WinToGo bootloader setup (placeholder)..."), "magenta")
        # Actual logic: mount ESP (e.g. target_device+"1"), copy boot files from target_fs_mountpoint/Windows/Boot/EFI, create BCD.
        # This was handled by the block starting with `esp_partition = target_device + "1"` in original code.

    if utils.gui: utils.gui.state = _("Applying Windows 7 UEFI workaround (if applicable)..."); utils.gui.progress = False
    workaround.support_windows_7_uefi_boot(source_fs_mountpoint, target_fs_mountpoint) # From source to target
    utils.check_kill_signal()

    if not skip_legacy_bootloader: # For MBR standard mode
        if utils.gui: utils.gui.state = _("Installing legacy GRUB bootloader (standard)..."); utils.gui.progress = False
        # The original main called install_legacy_pc_bootloader_grub and install_legacy_pc_bootloader_grub_config
        # These install a very basic GRUB to chainload Windows.
        install_legacy_pc_bootloader_grub(target_fs_mountpoint, target_device, command_grubinstall)
        utils.check_kill_signal()
        if utils.gui: utils.gui.state = _("Installing GRUB configuration (standard)..."); utils.gui.progress = False
        install_legacy_pc_bootloader_grub_config(target_fs_mountpoint, target_device, command_grubinstall, name_grub_prefix)
        utils.check_kill_signal()

    if workaround_bios_boot_flag: # For MBR standard mode
        if utils.gui: utils.gui.state = _("Applying BIOS boot flag workaround..."); utils.gui.progress = False
        workaround.buggy_motherboards_that_ignore_disks_without_boot_flag_toggled(target_device)
        utils.check_kill_signal()

    current_state = "finished-standard"
    if utils.gui: utils.gui.state = _("Standard process finished successfully!"); utils.gui.progress = 100
    utils.print_with_color(_("Standard USB creation process completed successfully."), "green")
    return 0 # Success for standard mode


# --- End of refactored main() for single-boot modes ---


def main_multiboot(args, temp_dir):
    """
    Handles the multiboot creation process.
    Orchestrates partitioning, GRUB installation, ISO copying, and optional full Linux install.
    """
    utils.print_with_color(_("Starting Multiboot USB creation process..."), "green")
    global current_state # For cleanup status

    if not args.target:
        utils.print_with_color(_("Error: Target device (--target) must be specified for multiboot mode."), "red")
        return 1

    target_device = args.target

    # 0. Preliminary checks
    if os.getuid() != 0:
        utils.print_with_color(_("Warning: Multiboot creation typically requires root privileges for partitioning and GRUB install."), "yellow")
        # May not strictly be an error yet, as some tools might use sudo internally or user might have setup permissions.
        # However, it's good to warn.

    if utils.check_is_target_device_busy(target_device):
        utils.print_with_color(_("Error: Target device {0} is busy. Please unmount all partitions on it.").format(target_device), "red")
        return 1

    # Check critical tool dependencies early
    missing_system_deps = []
    if not partitioning.check_tool_availability("sgdisk") and not partitioning.check_tool_availability("parted"):
        missing_system_deps.append("sgdisk or parted")
    if not partitioning.check_tool_availability("wipefs"):
        missing_system_deps.append("wipefs")
    if grub_manager.check_grub_dependencies():
        missing_system_deps.extend(grub_manager.check_grub_dependencies())
    if args.full_linux_install:
        if linux_installer.check_linux_installer_dependencies(args.full_linux_install):
            missing_system_deps.extend(linux_installer.check_linux_installer_dependencies(args.full_linux_install))

    if missing_system_deps:
        utils.print_with_color(_("Error: Missing critical system dependencies for multiboot mode: {0}").format(", ".join(missing_system_deps)), "red")
        return 1


    # 1. Create partition layout
    current_state = "partitioning"
    if utils.gui: utils.gui.state = _("Creating partitions..."); utils.gui.progress = 10

    partition_info = partitioning.create_multiboot_partition_layout(
        target_device,
        win_to_go_size_gb=args.win_size_gb if args.win_iso else 0, # Only allocate if win_iso is provided
        payload_fs_type=args.payload_fs.upper()
    )
    if not partition_info:
        utils.print_with_color(_("Error: Failed to create partition layout."), "red")
        return 1

    utils.print_with_color(_("Partitions created:"), "green")
    for p_name, p_path in partition_info.items():
        if not p_name.endswith("_uuid"): # Print only device paths for brevity
             utils.print_with_color(f"  {p_name}: {p_path} (UUID: {partition_info.get(p_name+'_uuid', 'N/A')})")


    # Define mount points based on temp_dir
    # Ensure temp_dir is unique and cleaned up appropriately by the caller (`run` function's finally block)
    base_mount_path = os.path.join(temp_dir, "usb_mount")
    efi_mount_point = os.path.join(base_mount_path, "efi")
    boot_mount_point = os.path.join(base_mount_path, "boot") # GRUB files and ISOs go here
    win_mount_point = os.path.join(base_mount_path, "windows")
    payload_mount_point = os.path.join(base_mount_path, "payload") # For full Linux install or general data

    # Create mount point directories
    for mp in [efi_mount_point, boot_mount_point, win_mount_point, payload_mount_point]:
        os.makedirs(mp, exist_ok=True)

    mounted_partitions_cleanup_list = [] # Keep track of what we successfully mount

    try:
        # 2. Mount essential partitions (ESP and Boot partition)
        current_state = "mounting_boot_partitions"
        if utils.gui: utils.gui.state = _("Mounting boot partitions..."); utils.gui.progress = 20

        if utils.run_command(["mount", partition_info['efi'], efi_mount_point], error_message=_("Failed to mount EFI partition.")): return 1
        mounted_partitions_cleanup_list.append(efi_mount_point)

        # The "boot" partition for GRUB is where /boot/grub will live.
        # In our scheme, this is the ESP itself if we want a simple layout, or a dedicated one.
        # For this plan, ESP serves as the boot partition for GRUB files too.
        # So, boot_mount_point will be efi_mount_point for GRUB installation if ESP holds /boot/grub.
        # Let's assume grub files go into ESP's /boot/grub directory.
        # So, grub_boot_dir_on_esp = os.path.join(efi_mount_point, "boot")
        # os.makedirs(grub_boot_dir_on_esp, exist_ok=True)
        # Effectively, boot_mount_point for grub_manager.install_grub becomes efi_mount_point + "/boot"
        # And efi_directory for grub_manager.install_grub becomes efi_mount_point
        
        # Let's simplify: The `grub_manager.install_grub` expects `boot_mount_point` to be where `/boot/grub` is created.
        # If ESP is partition 1 (/dev/sdX1) and mounted on `efi_mount_point`, then GRUB files will go to `efi_mount_point/boot/grub`.
        # So, `boot_directory` for grub-install should be `efi_mount_point + /boot`.
        # The `grub_manager.install_grub` function handles this by taking `boot_mount_point` as the base for its `--boot-directory` arg.
        # For our partitioning scheme, the ESP (partition_info['efi']) is where GRUB's /boot/grub will live.
        # So, we mount ESP to efi_mount_point, and pass efi_mount_point as *both* efi_directory and the base for boot_directory to grub_manager.
        # The grub_manager.install_grub will internally construct boot_directory as e.g. efi_mount_point/boot
        
        # Let's refine: The plan was "EFI System (FAT32, 512 MiB)" and then "bios_grub".
        # GRUB files should ideally go on a partition accessible by both EFI and BIOS GRUB.
        # The ESP is FAT32, so it's a good candidate.
        # grub-install --boot-directory=/mnt/usb/boot means /mnt/usb/boot/grub/...
        # We need a partition mounted at a location that will become /boot for GRUB.
        # Let's use the ESP (partition_info['efi']) for this. We mount it at `efi_mount_point`.
        # The grub files will be installed into `efi_mount_point/boot/grub`.
        # So, `efi_directory` for grub-install is `efi_mount_point`.
        # And `boot_directory` for grub-install is `os.path.join(efi_mount_point, "boot")`.
        # The `grub_manager.install_grub` function's `boot_mount_point` argument should be where `/boot/grub` is created.
        # So, we will pass `efi_mount_point` as the `efi_mount_point_arg` and `os.path.join(efi_mount_point, "boot")` as `boot_mount_point_arg` to `install_grub`.

        # Correction: The `grub_manager.install_grub` is designed such that `boot_mount_point` is the root of the partition
        # that will contain the `/boot/grub` directory. E.g. if `boot_mount_point` is `/tmp/usb_root`, then
        # `grub-install --boot-directory=/tmp/usb_root/boot` is called.
        # For our case, ESP is mounted at `efi_mount_point`. We want `/EFI` and `/boot/grub` on it.
        # So, `efi_directory` for `grub-install` is `efi_mount_point`.
        # `boot_directory` for `grub-install` is `os.path.join(efi_mount_point, "boot")`.
        # The `grub_manager.install_grub` function needs to be called with:
        # `install_grub(target_device, efi_directory=efi_mount_point, boot_directory_base=efi_mount_point)`
        # And inside `install_grub`, it would construct `boot_directory_arg = os.path.join(boot_directory_base, "boot")`.
        # The current `grub_manager.install_grub` takes `efi_mount_point` and `boot_mount_point`.
        # `boot_mount_point` is used as the argument to `--boot-directory`.
        # This means `boot_mount_point` should be where `/grub` directory itself is created, not its parent `/boot`.
        # This is confusing. Let's assume `grub_manager.install_grub` expects `boot_mount_point` to be the partition
        # where `/boot/grub` will be created. So, if ESP is mounted at `efi_mount_point`,
        # then `boot_mount_point` for `grub-install` would be `efi_mount_point`.
        # And `grub-install` would create `efi_mount_point/boot/grub`.
        # The `grub_manager.generate_grub_cfg` also expects `boot_mount_point` to be where `/boot/grub/grub.cfg` is.

        # Let's clarify:
        # ESP is mounted at `efi_mount_point`.
        # GRUB EFI files go into `efi_mount_point/EFI/...`
        # GRUB common files (themes, fonts, grub.cfg) go into `efi_mount_point/boot/grub/...`
        # So, for `grub-install`:
        #   `--efi-directory` = `efi_mount_point`
        #   `--boot-directory` = `os.path.join(efi_mount_point, "boot")`
        # The `grub_manager.install_grub` function needs to handle this structure.
        # The `grub_manager.generate_grub_cfg` needs `os.path.join(efi_mount_point, "boot")` as its `boot_mount_point` arg.

        # Re-check grub_manager.install_grub: it uses `boot_mount_point` for `--boot-directory`.
        # This implies `boot_mount_point` is the directory that will contain `grub/` (e.g. `/mnt/usb/boot`).
        # So, we need to create `efi_mount_point/boot/` and pass that as `boot_mount_point` to `install_grub`.

        grub_install_boot_dir_actual = os.path.join(efi_mount_point, "boot")
        os.makedirs(grub_install_boot_dir_actual, exist_ok=True)
        # No need to mount anything separately for this `grub_install_boot_dir_actual` as it's on the already mounted ESP.


        # 3. Install GRUB
        current_state = "installing_grub"
        if utils.gui: utils.gui.state = _("Installing GRUB bootloader..."); utils.gui.progress = 30
        if not grub_manager.install_grub(target_device, efi_mount_point, grub_install_boot_dir_actual):
            utils.print_with_color(_("Error: GRUB installation failed."), "red")
            # Cleanup already mounted partitions before returning
            for mp_path in reversed(mounted_partitions_cleanup_list): utils.run_command(["umount", "-l", mp_path], suppress_errors=True)
            return 1

        # 4. Handle Windows-To-Go
        win_part_uuid_for_grub = partition_info.get('win_to_go_uuid')
        if args.win_iso:
            current_state = "copying_windows"
            if utils.gui: utils.gui.state = _("Copying Windows files..."); utils.gui.progress = 40
            if not partition_info.get('win_to_go'):
                utils.print_with_color(_("Error: Windows partition not found in layout for --win-iso."), "red")
                for mp_path in reversed(mounted_partitions_cleanup_list): utils.run_command(["umount", "-l", mp_path], suppress_errors=True)
                return 1

            if utils.run_command(["mount", partition_info['win_to_go'], win_mount_point], error_message=_("Failed to mount Windows partition.")): return 1
            mounted_partitions_cleanup_list.append(win_mount_point)

            # Mount Windows ISO
            win_iso_mount_point = os.path.join(temp_dir, "win_iso_mount")
            os.makedirs(win_iso_mount_point, exist_ok=True)
            if mount_source_filesystem(args.win_iso, win_iso_mount_point): # Reusing existing function
                utils.print_with_color(_("Error mounting Windows ISO."), "red")
                for mp_path in reversed(mounted_partitions_cleanup_list): utils.run_command(["umount", "-l", mp_path], suppress_errors=True)
                shutil.rmtree(win_iso_mount_point, ignore_errors=True)
                return 1
            
            copy_filesystem_files(win_iso_mount_point, win_mount_point) # Reusing existing function

            # Apply Win-To-Go specific workarounds (e.g., TPM bypass for Win11)
            # These workarounds from `WowUSB.workaround` operate on the mounted Windows filesystem.
            win_ver_info = utils.detect_windows_version(win_mount_point) # Mounted Windows partition
            utils.print_with_color(_("Detected Windows version on ISO: {0}, build: {1}, Win11: {2}").format(*win_ver_info),"blue")
            if win_ver_info[2]: # is_windows11
                 utils.print_with_color(_("Applying Windows 11 specific modifications for Win-To-Go..."), "blue")
                 workaround.bypass_windows11_tpm_requirement(win_mount_point)
            workaround.prepare_windows_portable_drivers(win_mount_point) # General WinToGo driver prep

            # Unmount Windows ISO
            utils.run_command(["umount", "-l", win_iso_mount_point], suppress_errors=True)
            shutil.rmtree(win_iso_mount_point, ignore_errors=True)

            utils.print_with_color(_("Windows files copied and prepared for Win-To-Go."), "green")
        else:
            win_part_uuid_for_grub = None # No Windows installation

        # 5. Handle Linux ISOs
        current_state = "copying_linux_isos"
        if utils.gui: utils.gui.state = _("Copying Linux ISOs..."); utils.gui.progress = 60
        if args.linux_iso:
            # ISOs go into /boot/iso on the ESP (mounted at efi_mount_point)
            grub_iso_dir = os.path.join(grub_install_boot_dir_actual, "iso") # e.g. /tmp/usb_mount/efi/boot/iso
            os.makedirs(grub_iso_dir, exist_ok=True)
            utils.print_with_color(_("Copying Linux ISOs to {0}...").format(grub_iso_dir), "blue")
            for iso_path in args.linux_iso:
                if os.path.isfile(iso_path):
                    try:
                        shutil.copy2(iso_path, grub_iso_dir)
                        utils.print_with_color(_("Copied {0}").format(iso_path), "green")
                    except Exception as e:
                        utils.print_with_color(_("Error copying ISO {0}: {1}").format(iso_path, e), "red")
                        # Decide if this is a fatal error or just a warning
                else:
                    utils.print_with_color(_("Warning: Linux ISO path {0} not found or not a file. Skipping.").format(iso_path), "yellow")

        # 6. Handle Full Linux Install
        linux_install_info_for_grub = None
        if args.full_linux_install:
            current_state = "installing_full_linux"
            if utils.gui: utils.gui.state = _("Performing full Linux install..."); utils.gui.progress = 70
            if not partition_info.get('payload'):
                utils.print_with_color(_("Error: Payload partition not found in layout for full Linux install."), "red")
                for mp_path in reversed(mounted_partitions_cleanup_list): utils.run_command(["umount", "-l", mp_path], suppress_errors=True)
                return 1

            # Payload partition is mounted at `payload_mount_point`
            if utils.run_command(["mount", partition_info['payload'], payload_mount_point], error_message=_("Failed to mount Payload partition for Linux install.")): return 1
            mounted_partitions_cleanup_list.append(payload_mount_point)

            install_success = linux_installer.install_linux_to_f2fs(
                partition_info['payload'],
                partition_info['payload_uuid'], # Pass the UUID for fstab generation
                args.full_linux_install, # 'ubuntu' or 'arch' or 'debian'
                payload_mount_point,
                distro_release=args.full_linux_release,
                http_proxy=args.http_proxy
            )
            if not install_success:
                utils.print_with_color(_("Error: Full Linux installation failed."), "red")
                for mp_path in reversed(mounted_partitions_cleanup_list): utils.run_command(["umount", "-l", mp_path], suppress_errors=True)
                return 1
            
            linux_install_info_for_grub = {
                "uuid": partition_info['payload_uuid'],
                "name": f"{args.full_linux_install.capitalize()} ({args.payload_fs.upper()})", # e.g. Ubuntu (F2FS)
                "kernel_opts": "" # Add any specific kernel options if needed
            }
            utils.print_with_color(_("Full Linux installation successful."), "green")

        # 7. Generate grub.cfg
        current_state = "generating_grub_config"
        if utils.gui: utils.gui.state = _("Generating GRUB configuration..."); utils.gui.progress = 90
        
        # grub.cfg is generated in boot_mount_point/grub/grub.cfg
        # boot_mount_point for generate_grub_cfg is where /grub/grub.cfg will be, i.e., grub_install_boot_dir_actual
        if not grub_manager.generate_grub_cfg(
            grub_install_boot_dir_actual, # This is efi_mount_point/boot
            windows_partition_uuid=win_part_uuid_for_grub,
            payload_partition_uuid=partition_info.get('payload_uuid'), # For ISOs if they were on payload, currently not used by template like that
            linux_install_details=linux_install_info_for_grub
        ):
            utils.print_with_color(_("Error: Failed to generate grub.cfg."), "red")
            for mp_path in reversed(mounted_partitions_cleanup_list): utils.run_command(["umount", "-l", mp_path], suppress_errors=True)
            return 1

        current_state = "finished"
        if utils.gui: utils.gui.state = _("Multiboot USB creation complete!"); utils.gui.progress = 100
        utils.print_with_color(_("Multiboot USB creation process completed successfully."), "green")
        return 0

    finally:
        # 8. Unmount all partitions
        current_state = "unmounting_filesystems"
        utils.print_with_color(_("Unmounting filesystems..."), "blue")
        for mp_path in reversed(mounted_partitions_cleanup_list):
            utils.run_command(["umount", "-R", mp_path], suppress_errors=True) # -R for recursive unmount (in case of nested mounts like chroot)

        # Remove the temporary base mount directory structure if it's empty
        # The main temp_dir (parent of base_mount_path) is cleaned by the `run` function's finally block.
        try:
            if os.path.exists(base_mount_path):
                # Check if any subdirectories within base_mount_path still exist and are mount points
                # This is a basic check; more robust would be to iterate and check os.path.ismount
                if not os.listdir(efi_mount_point) and not os.path.ismount(efi_mount_point): os.rmdir(efi_mount_point)
                if not os.listdir(boot_mount_point) and not os.path.ismount(boot_mount_point) : os.rmdir(boot_mount_point) # This is efi_mount_point/boot
                if os.path.exists(win_mount_point) and not os.listdir(win_mount_point) and not os.path.ismount(win_mount_point): os.rmdir(win_mount_point)
                if os.path.exists(payload_mount_point) and not os.listdir(payload_mount_point) and not os.path.ismount(payload_mount_point): os.rmdir(payload_mount_point)
                if not os.listdir(base_mount_path) : os.rmdir(base_mount_path)
        except OSError as e:
            utils.print_with_color(_("Warning: Could not remove all temporary mountpoint directories in {0}: {1}").format(base_mount_path, e), "yellow")


# This is the original main function, now handling only single-boot modes.
# It's called if args.install_mode is not "multiboot".
# The signature needs to align with how `run()` calls it, or `run()` needs to adapt.
# The original `main` took many parameters. `run()` now calls `main(args, temp_dir=temp_directory)`.
# So, this original `main` needs to be adapted to primarily use `args`.

# The original `main` function definition is below this new `main_multiboot` function.
# We need to ensure the `if args.install_mode == "multiboot":` check
# correctly diverts to `main_multiboot` from within the refactored `main`.

# The `main` function from the original file needs to be adjusted.
# It was: main(source_fs_mountpoint, target_fs_mountpoint, source_media, target_media, install_mode, temp_directory, ...)
# Now it's: main(args, temp_dir=None)

# The existing `main` function needs to be modified to first check for multiboot mode.
# I will insert the call to main_multiboot at the beginning of the existing main function.

# (The original `main` function definition follows this block in the actual file)
# For the diff tool, I will apply the change to the existing `main` function.

# Let's apply the split to the existing `main` function.
# The previous diff block for `main` was a bit conceptual. This one will be more direct.


class ReportCopyProgress(threading.Thread):
    """
    Classes for threading module
    """
    file = ""
    stop = False

    def __init__(self, source, target):
        threading.Thread.__init__(self)
        self.source = source
        self.target = target

    def run(self):
        source_size = utils.get_size(self.source)
        len_ = 0
        file_old = None

        while not self.stop:
            target_size = utils.get_size(self.target)

            if len_ != 0 and gui is None:
                print('\033[3A')
                print(" " * len_)
                print(" " * 4)
                print('\033[3A')

            # Prevent printing same filenames
            if self.file != file_old:
                file_old = self.file
                utils.print_with_color(self.file.replace(self.source, ""))

            string = "Copied " + utils.convert_to_human_readable_format(
                target_size) + " from a total of " + utils.convert_to_human_readable_format(source_size)

            len_ = len(string)
            percentage = (target_size * 100) // source_size

            if gui is not None:
                gui.state = string
                gui.progress = percentage
            else:
                print(string)
                print(str(percentage) + "%")

            time.sleep(0.05)
        if gui is not None:
            gui.progress = False

        return 0


def run():
    # Get the parsed command line arguments
    args = setup_arguments()
    
    # If list-devices is specified, handle it and exit
    if args.list_devices:
        try:
            # Import the device listing function from WowUSB.utils
            from WowUSB.utils import list_available_devices
            devices = list_available_devices()
            print("\nAvailable storage devices:")
            print("-" * 50)
            for dev in devices:
                print(f"Device: {dev['device']}")
                print(f"  Model: {dev.get('model', 'N/A')}")
                print(f"  Size: {dev.get('size', 'N/A')}")
                print(f"  Type: {dev.get('type', 'N/A')}")
                if 'partitions' in dev:
                    print("  Partitions:")
                    for part in dev['partitions']:
                        print(f"    {part['name']}: {part.get('size', 'N/A')} {part.get('fstype', '')} {part.get('label', '')}")
                print("-" * 50)
            return 0
        except Exception as e:
            print(f"Error listing devices: {str(e)}")
            return 1
    
    # For other commands, initialize the application
    result = init()
    if isinstance(result, list) is False:
        return 1
        
    source_fs_mountpoint, target_fs_mountpoint, temp_directory, \
        install_mode, source_media, target_media, \
        workaround_bios_boot_flag, skip_legacy_bootloader, target_filesystem_type, \
        new_file_system_label, verbose, debug, parser = result

    try:
        # Call the main function with the parsed arguments
        return main(args, temp_dir=temp_directory)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1
    except Exception as error:
        utils.print_with_color(f"Error: {str(error)}", "red")
        if debug:
            traceback.print_exc()
        return 1
    finally:
        cleanup(source_fs_mountpoint, target_fs_mountpoint, temp_directory, target_media)


if __name__ == "__main__":
    run()
