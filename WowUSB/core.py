
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

    command_mkdosfs, command_mkntfs, command_grubinstall = utils.check_runtime_dependencies(application_name)
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

    if mount_source_filesystem(source_media, source_fs_mountpoint):
        utils.print_with_color(_("Error: Unable to mount source filesystem"), "red")
        return 1

    # If auto-detection is requested, determine the optimal filesystem
    if target_filesystem_type.upper() == "AUTO":
        target_filesystem_type = fs_handlers.get_optimal_filesystem_for_iso(source_fs_mountpoint)
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
    try:
        fs_handler = fs_handlers.get_filesystem_handler(target_filesystem_type)
        is_available, missing_deps = fs_handler.check_dependencies()
        if not is_available:
            utils.print_with_color(
                _("Error: Missing dependencies for {0} filesystem: {1}").format(
                    fs_handler.name(), ", ".join(missing_deps)
                ),
                "red"
            )
            return 1
            
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

    # Check if Windows-To-Go mode is enabled
    is_wintogo_mode = getattr(parser, 'wintogo', False) if parser else False
    
    if is_wintogo_mode:
        utils.print_with_color(_("Windows-To-Go mode enabled"), "green")
        
        if install_mode != "device":
            utils.print_with_color(_("Error: Windows-To-Go requires --device mode"), "red")
            return 1
            
        # Create Windows-To-Go specific partition layout
        if create_wintogo_partition_layout(target_device, target_filesystem_type, filesystem_label):
            utils.print_with_color(_("Error: Failed to create Windows-To-Go partition layout"), "red")
            return 1
            
        # Update target partition to point to the Windows partition (3rd partition)
        target_partition = target_device + "3"
    elif install_mode == "device":
        wipe_existing_partition_table_and_filesystem_signatures(target_device)
        create_target_partition_table(target_device, "legacy")
        create_target_partition(target_device, target_partition, target_filesystem_type, filesystem_label)

        # Add UEFI support partition if needed
        if fs_handler.needs_uefi_support_partition():
            create_uefi_ntfs_support_partition(target_device)
            install_uefi_support_partition(fs_handler, target_device + "2", temp_directory)

    if install_mode == "partition":
        if utils.check_target_partition(target_partition, target_device):
            return 1

    if mount_target_filesystem(target_partition, target_fs_mountpoint):
        utils.print_with_color(_("Error: Unable to mount target filesystem"), "red")
        return 1

    if utils.check_target_filesystem_free_space(target_fs_mountpoint, source_fs_mountpoint, target_partition):
        return 1

    current_state = "copying-filesystem"

    copy_filesystem_files(source_fs_mountpoint, target_fs_mountpoint)

    # Set up persistence for Linux distributions if requested
    if parser and getattr(parser, 'persistence', None) is not None:
        if setup_linux_persistence(target_device, target_partition,
                                   target_filesystem_type, parser.persistence) != 0:
            utils.print_with_color(_("Error: Failed to set up persistence"), "red")
            return 1

    # Apply Windows-To-Go specific modifications if in Windows-To-Go mode
    if is_wintogo_mode:
        # Detect Windows version
        windows_version, build_number, is_windows11 = utils.detect_windows_version(source_fs_mountpoint)
        utils.print_with_color(
            _("Detected Windows version: {0}, build: {1}").format(windows_version, build_number),
            "green"
        )
        
        # Apply TPM bypass for Windows 11
        if is_windows11:
            utils.print_with_color(_("Applying Windows 11 specific modifications..."), "green")
            workaround.bypass_windows11_tpm_requirement(target_fs_mountpoint)
        
        # Configure drivers and hardware detection for portable Windows
        workaround.prepare_windows_portable_drivers(target_fs_mountpoint)
        
        # Mount ESP partition for bootloader installation
        esp_partition = target_device + "1"
        esp_mountpoint = target_fs_mountpoint + "_esp"
        
        os.makedirs(esp_mountpoint, exist_ok=True)
        
        if subprocess.run(["mount", esp_partition, esp_mountpoint]).returncode != 0:
            utils.print_with_color(_("Error: Unable to mount ESP partition"), "red")
            return 1
        
        # Copy bootloader files to ESP
        utils.print_with_color(_("Installing bootloader files to ESP..."), "green")
        
        # Create directory structure
        os.makedirs(os.path.join(esp_mountpoint, "EFI", "Boot"), exist_ok=True)
        
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

    workaround.support_windows_7_uefi_boot(source_fs_mountpoint, target_fs_mountpoint)
    if not skip_legacy_bootloader:
        install_legacy_pc_bootloader_grub(target_fs_mountpoint, target_device, command_grubinstall)
        install_legacy_pc_bootloader_grub_config(target_fs_mountpoint, target_device, command_grubinstall, name_grub_prefix)

    if workaround_bios_boot_flag:
        workaround.buggy_motherboards_that_ignore_disks_without_boot_flag_toggled(target_device)

    current_state = "finished"

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
    parser.add_argument("--multiboot", "-m", action="store_true",
                        help=_("Multi-boot mode: Create a multi-boot USB drive"))
    
    # OS options
    parser.add_argument("--add-os", "-a", action="append", nargs=4,
                        metavar=("TYPE", "ISO", "SIZE_GB", "FILESYSTEM"),
                        help=_("Add OS (type, ISO path, size in GB, filesystem)"))
    
    # Shared partition options
    parser.add_argument("--shared-size", "-s", type=int, default=4,
                        help=_("Shared partition size in GB"))
    parser.add_argument("--shared-filesystem", "-f", default="EXFAT",
                        help=_("Shared partition filesystem"))

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
        utils.print_with_color(_("Multi-boot mode selected"), "green")
        
        # Import multiboot module
        try:
            import WowUSB.multiboot as multiboot
        except ImportError:
            utils.print_with_color(_("Error: Multi-boot module not found"), "red")
            return 1
        
        # Check target device
        if not args.target:
            utils.print_with_color(_("Error: Target device not specified"), "red")
            return 1
        
        # Check if target device exists
        if not os.path.exists(args.target):
            utils.print_with_color(_("Error: Target device not found: {}").format(args.target), "red")
            return 1
        
        # Check if target device is a block device
        if not utils.is_block_device(args.target):
            utils.print_with_color(_("Error: Target is not a block device: {}").format(args.target), "red")
            return 1
        
        # Check if target device is mounted
        if utils.is_mounted(args.target):
            utils.print_with_color(_("Error: Target device is mounted: {}").format(args.target), "red")
            return 1
        
        # Prepare OS configurations
        os_configs = []
        
        for os_type, iso_path, size_gb, filesystem in args.add_os:
            # Check if ISO exists
            if not os.path.exists(iso_path):
                utils.print_with_color(_("Error: ISO file not found: {}").format(iso_path), "red")
                return 1
            
            # Check if ISO is readable
            if not os.access(iso_path, os.R_OK):
                utils.print_with_color(_("Error: ISO file is not readable: {}").format(iso_path), "red")
                return 1
            
            # Add OS configuration
            os_configs.append({
                "type": os_type.lower(),
                "name": os_type.capitalize(),
                "iso_path": iso_path,
                "size_mb": int(float(size_gb) * 1024),
                "filesystem": filesystem.upper()
            })
        
        # Create multi-boot USB drive
        return multiboot.create_multiboot_usb(
            target_device=args.target,
            os_configs=os_configs,
            shared_size_mb=args.shared_size * 1024,
            shared_filesystem=args.shared_filesystem.upper(),
            verbose=args.verbose
        )
    
    # Handle device and partition modes (existing code)
        if not args.add_os:
            parser.error(_("At least one OS must be specified with --add-os"))
        if args.wintogo:
            parser.error(_("Windows-To-Go is not compatible with multi-boot mode"))
        if args.persistence is not None:
            parser.error(_("Persistence is not compatible with multi-boot mode"))
    
    return args

# setup_arguments docstring is already preserved by the decorator


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
