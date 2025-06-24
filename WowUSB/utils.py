
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

import os
import pathlib
import re
import shutil
import subprocess
import sys
from xml.dom.minidom import parseString

import WowUSB.miscellaneous as miscellaneous

_ = miscellaneous.i18n

#: Disable message coloring when set to True, set by --no-color
no_color = False

# External tools
try:
    import termcolor
except ImportError:
    print("Module termcolor is not installed, text coloring disabled")
    no_color = True

gui = None
verbose = False


def check_command(command_name):
    """
    Check if a command is available in the system PATH
    
    Args:
        command_name (str): Name of the command to check
        
    Returns:
        str: Path to the command if found, None otherwise
    """
    return shutil.which(command_name)


def print_with_color(text, color=""):
    """
    Print function
    This function takes into account no_color flag
    Also if used by gui, sends information to it, rather than putting it into standard output

    :param text: Text to be printed
    :param color: Color of the text
    """
    if gui is not None:
        gui.state = text
        if color == "red":
            gui.error = text
            sys.exit()
    else:
        if no_color or color == "":
            sys.stdout.write(text + "\n")
        else:
            termcolor.cprint(text, color)


def check_runtime_dependencies(application_name):
    """
    :param application_name:
    :return:
    """
    result = "success"

    system_commands = ["mount", "umount", "wipefs", "lsblk", "blockdev", "df", "parted", "7z"]
    for command in system_commands:
        if shutil.which(command) is None:
            print_with_color(
                _("Error: {0} requires {1} command in the executable search path, but it is not found.").format(
                    application_name, command),
                "red")
            result = "failed"

    fat = ["mkdosfs", "mkfs.msdos", "mkfs.vfat", "mkfs.fat"]
    for command in fat:
        if shutil.which(command) is not None:
            fat = command
            break

    if isinstance(fat, list):
        print_with_color(_("Error: mkdosfs/mkfs.msdos/mkfs.vfat/mkfs.fat command not found!"), "red")
        print_with_color(_("Error: Please make sure that dosfstools is properly installed!"), "red")
        result = "failed"

    ntfs = "mkntfs"
    if shutil.which("mkntfs") is None:
        print_with_color(_("Error: mkntfs command not found!"), "red")
        print_with_color(_("Error: Please make sure that ntfs-3g is properly installed!"), "red")
        result = "failed"

    grub = ["grub-install", "grub2-install"]
    for command in grub:
        if shutil.which(command) is not None:
            grub = command
            break

    if isinstance(grub, list):
        print_with_color(_("Error: grub-install or grub2-install command not found!"), "red")
        print_with_color(_("Error: Please make sure that GNU GRUB is properly installed!"), "red")
        result = "failed"

    if result != "success":
        raise RuntimeError("Dependencies are not met")
    else:
        return [fat, ntfs, grub]


def check_fat32_filesize_limitation(source_fs_mountpoint):
    """
    Check if source filesystem has files that exceed FAT32's 4GiB single file size limitation.
    
    :param source_fs_mountpoint: Source filesystem's mountpoint to check
    :return: 1 if limitation is hit and an alternative filesystem is needed, 0 if FAT32 can be used
    """
    FAT32_MAX_SIZE = (2 ** 32) - 1  # Max fat32 file size (4GB - 1 byte)
    
    if verbose:
        print_with_color(_("Checking for files larger than 4GB..."))
    
    for dirpath, dirnames, filenames in os.walk(source_fs_mountpoint):
        for file in filenames:
            path = os.path.join(dirpath, file)
            try:
                if os.path.getsize(path) > FAT32_MAX_SIZE:
                    print_with_color(
                        _(
                            "Warning: File {0} in source image has exceed the FAT32 Filesystem 4GiB Single File Size Limitation, a different filesystem will be used.").format(
                            path),
                        "yellow")
                    print_with_color(
                        _(
                            "Refer: https://github.com/rebots-online/WowUSB/wiki/Limitations#fat32-filesystem-4gib-single-file-size-limitation for more info."),
                        "yellow")
                    return 1
            except OSError:
                # Skip files we can't access
                continue
                
    return 0


def check_fat32_filesize_limitation(source_path):
    """
    Check if there are files larger than 4GB in the source path

    Args:
        source_path (str): Path to check

    Returns:
        bool: True if there are files larger than 4GB, False otherwise
    """
    for dirpath, dirnames, filenames in os.walk(source_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                if os.path.getsize(file_path) > 4 * 1024 * 1024 * 1024:  # 4GB
                    return True
            except (OSError, IOError):
                pass
    return False


def check_fat32_filesize_limitation_detailed(source_path):
    """
    Check if there are files larger than 4GB in the source path and return details

    Args:
        source_path (str): Path to check

    Returns:
        tuple: (has_large_files, largest_file, largest_size)
            has_large_files (bool): True if there are files larger than 4GB
            largest_file (str): Path to the largest file (relative to source_path)
            largest_size (int): Size of the largest file in bytes
    """
    has_large_files = False
    largest_file = ""
    largest_size = 0

    for dirpath, dirnames, filenames in os.walk(source_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                file_size = os.path.getsize(file_path)

                # Track the largest file
                if file_size > largest_size:
                    largest_size = file_size
                    largest_file = os.path.relpath(file_path, source_path)

                # Check if larger than 4GB
                if file_size > 4 * 1024 * 1024 * 1024:  # 4GB
                    has_large_files = True
            except (OSError, IOError):
                pass

    return (has_large_files, largest_file, largest_size)
    

def check_runtime_parameters(install_mode, source_media, target_media):
    """
    :param install_mode:
    :param source_media:
    :param target_media:
    :return:
    """
    if not os.path.isfile(source_media) and not pathlib.Path(source_media).is_block_device():
        print_with_color(
            _("Error: Source media \"{0}\" not found or not a regular file or a block device file!").format(
                source_media),
            "red")
        return 1

    if not pathlib.Path(target_media).is_block_device():
        print_with_color(_("Error: Target media \"{0}\" is not a block device file!").format(target_media), "red")
        return 1

    if install_mode == "device" and target_media[-1].isdigit():
        print_with_color(_("Error: Target media \"{0}\" is not an entire storage device!").format(target_media), "red")
        return 1

    if install_mode == "partition" and not target_media[-1].isdigit():
        print_with_color(_("Error: Target media \"{0}\" is not an partition!").format(target_media), "red")
        return 1
    return 0


def determine_target_parameters(install_mode, target_media):
    """
    :param install_mode:
    :param target_media:
    :return:
    """
    if install_mode == "partition":
        target_partition = target_media

        while target_media[-1].isdigit():
            target_media = target_media[:-1]
        target_device = target_media
    else:
        target_device = target_media
        target_partition = target_media + str(1)

    if verbose:
        print_with_color(_("Info: Target device is {0}").format(target_device))
        print_with_color(_("Info: Target partition is {0}").format(target_partition))

    return [target_device, target_partition]


def check_is_target_device_busy(device):
    """
    Check if a device or any of its partitions are mounted
    
    Args:
        device (str): Path to the device (e.g., /dev/sdX)
        
    Returns:
        int: 0 if not busy, 1 if busy and couldn't unmount
    """
    if not device:
        return 0
        
    try:
        # Get the device name without /dev/ prefix
        dev_name = os.path.basename(device)
        if not dev_name:
            return 0
            
        # Get the mount information
        mount_output = subprocess.run("mount", capture_output=True, text=True).stdout.strip()
        
        # Find all mounted partitions for this device
        mounted_partitions = []
        for line in mount_output.split('\n'):
            if f"/{dev_name}" in line:
                mount_point = line.split(' ')[2]  # Third field is the mount point
                mounted_partitions.append(mount_point)
        
        # If any partitions are mounted, try to unmount them
        if mounted_partitions:
            print_with_color(_("Warning: The following partitions will be unmounted: {0}")
                           .format(mounted_partitions), "yellow")
            for partition in mounted_partitions:
                try:
                    subprocess.run(["umount", partition], check=True)
                except subprocess.CalledProcessError:
                    print_with_color(_("Error: Failed to unmount {0}").format(partition), "red")
                    return 1
        
        return 0
    except Exception as e:
        print_with_color(_("Error checking device status: {0}").format(str(e)), "red")
        return 1


def check_source_and_target_not_busy(install_mode, source_media, target_device, target_partition):
    """
    :param install_mode:
    :param source_media:
    :param target_device:
    :param target_partition:
    :return:
    """
    if check_is_target_device_busy(source_media):
        print_with_color(_("Error: Source media is currently mounted, unmount the partition then try again"), "red")
        return 1

    if install_mode == "partition":
        if check_is_target_device_busy(target_partition):
            print_with_color(_("Error: Target partition is currently mounted, unmount the partition then try again"),
                             "red")
            return 1
    else:
        if check_is_target_device_busy(target_device):
            print_with_color(
                _(
                    "Error: Target device is currently busy, unmount all mounted partitions in target device then try again"),
                "red")
            return 1


def check_target_partition(target_partition, target_device):
    """
    Check target partition for potential problems before mounting them for --partition creation mode as we don't know about the existing partition

    :param target_partition: The target partition to check
    :param target_device: The parent device of the target partition, this is passed in to check UEFI:NTFS filesystem's existence on check_uefi_ntfs_support_partition
    :return:
    """
    target_filesystem = subprocess.run(["lsblk",
                                        "--output", "FSTYPE",
                                        "--noheadings",
                                        target_partition], stdout=subprocess.PIPE).stdout.decode("utf-8").strip()

    if target_filesystem in ["vfat", "fat", "fat32"]:
        pass  # supported
    elif target_filesystem == "ntfs":
        check_uefi_ntfs_support_partition(target_device)
    elif target_filesystem in ["exfat", "f2fs", "btrfs"]:
        pass  # newly supported
    else:
        print_with_color(_("Error: Target filesystem not supported, currently supported filesystems: FAT, NTFS, exFAT, F2FS, and BTRFS."), "red")
        return 1

    return 0


def check_uefi_ntfs_support_partition(target_device):
    """
    Check if the UEFI:NTFS support partition exists
    Currently it depends on the fact that this partition has a label of "UEFI_NTFS"

    :param target_device: The UEFI:NTFS partition residing entier device file
    :return:
    """
    lsblk = subprocess.run(["lsblk",
                            "--output", "LABEL",
                            "--noheadings",
                            target_device], stdout=subprocess.PIPE).stdout.decode("utf-8").strip()

    if re.findall("UEFI_NTFS", lsblk) != []:
        print_with_color(
            _("Warning: Your device doesn't seems to have an UEFI:NTFS partition, "
              "UEFI booting will fail if the motherboard firmware itself doesn't support NTFS filesystem!"))
        print_with_color(
            _("Info: You may recreate disk with an UEFI:NTFS partition by using the --device creation method"))


def check_target_filesystem_free_space(target_fs_mountpoint, source_fs_mountpoint, target_partition):
    """
    :param target_fs_mountpoint:
    :param source_fs_mountpoint:
    :param target_partition:
    :return:
    """
    df = subprocess.run(["df",
                         "--block-size=1",
                         target_fs_mountpoint], stdout=subprocess.PIPE).stdout
    # free_space = int(df.strip().split()[4])

    awk = subprocess.Popen(["awk", "{print $4}"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    free_space = awk.communicate(input=df)[0]
    free_space = free_space.decode("utf-8").strip()
    free_space = re.sub("[^0-9]", "", free_space)
    free_space = int(free_space)

    needed_space = 0
    for dirpath, dirnames, filenames in os.walk(source_fs_mountpoint):
        for file in filenames:
            path = os.path.join(dirpath, file)
            needed_space += os.path.getsize(path)

    additional_space_required_for_grub_installation = 1000 * 1000 * 10  # 10MiB

    needed_space += additional_space_required_for_grub_installation

    if needed_space > free_space:
        print_with_color(_("Error: Not enough free space on target partition!"))
        print_with_color(
            _("Error: We required {0}({1} bytes) but '{2}' only has {3}({4} bytes).")
            .format(
                str(get_size(str(needed_space))),
                str(needed_space),
                target_partition,
                str(free_space),
                str(free_space)))
        return 1


def convert_to_human_readable_format(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Ti', suffix)


def get_size(path):
    total_size = 0
    for dirpath, __, filenames in os.walk(path):
        for file in filenames:
            path = os.path.join(dirpath, file)
            total_size += os.path.getsize(path)
    return total_size


def list_available_devices():
    """
    List all available storage devices and their partitions
    
    Returns:
        list: A list of dictionaries containing device information
    """
    import json
    import subprocess
    
    try:
        # Use lsblk to get device information in JSON format
        result = subprocess.run(
            ["lsblk", "-J", "-o", "NAME,MODEL,SIZE,TYPE,MOUNTPOINT,FSTYPE,LABEL"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Failed to list devices: {result.stderr}")
            
        devices_data = json.loads(result.stdout)
        
        # Filter out only disk devices (not partitions, loop devices, etc.)
        disks = [d for d in devices_data.get('blockdevices', []) 
                if d.get('type') == 'disk' and not d.get('name', '').startswith(('loop', 'sr', 'ram'))]
        
        # Process each disk to get its partitions
        for disk in disks:
            disk['device'] = f"/dev/{disk['name']}"
            disk['partitions'] = []
            
            # Get partitions for this disk
            for child in disk.get('children', []):
                if child.get('type') == 'part':
                    part_info = {
                        'name': f"/dev/{child['name']}",
                        'size': child.get('size', 'N/A'),
                        'fstype': child.get('fstype', ''),
                        'label': child.get('label', ''),
                        'mountpoint': child.get('mountpoint', '')
                    }
                    disk['partitions'].append(part_info)
        
        return disks
        
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse device information: {str(e)}")
    except Exception as e:
        raise Exception(f"Error listing devices: {str(e)}")


def check_kill_signal():
    """
    Ok, you may asking yourself, what the f**k is this, and why is it called everywhere. Let me explain
    In python you can't just stop or kill thread, it must end its execution,
    or recognize moment where you want it to stop and politely perform euthanasia on itself.
    So, here, if gui is set, we throw exception which is going to be (hopefully) catch by GUI,
    simultaneously ending whatever script was doing meantime!
    Everyone goes to home happy and user is left with wrecked pendrive (just joking, next thing called by gui is cleanup)
    """
    if gui is not None and hasattr(gui, 'kill') and gui.kill:
        # Define a specific exception for cancellation
        class OperationCancelledError(SystemExit): # Inherit from SystemExit for grace
            pass
        raise OperationCancelledError(_("Operation cancelled by user via GUI."))
    # time.sleep(0.1) # Sleeping here might make cancellation less responsive.
                      # Only sleep if truly needed for yielding, but GUI should handle its own event loop.


def update_policy_to_allow_for_running_gui_as_root(path):
    dom = parseString(
        "<?xml version=\"1.0\" ?>"
        "<!DOCTYPE policyconfig  PUBLIC '-//freedesktop//DTD polkit Policy Configuration 1.0//EN'  "
        "'http://www.freedesktop.org/software/polkit/policyconfig-1.dtd'><!-- \n"
        "DOC: https://www.freedesktop.org/software/polkit/docs/latest/polkit.8.html\n"
        "--><policyconfig>\n"
        "	<vendor>The WowUSB Project</vendor>\n"
        "	<vendor_url>https://github.com/rebots-online/WowUSB</vendor_url>\n"
        "	<icon_name>woeusbgui-icon</icon_name>\n"
        "\n"
        "	<action id=\"com.github.slacka.woeusb.run-gui-using-pkexec\">\n"
        "		<description>Run `woeusb` as SuperUser</description>\n"
        "		<description xml:lang=\"zh_TW\">以超級使用者(SuperUser)身份執行 `woeusb`</description>\n"
        "		<description xml:lang=\"pl_PL\">Uruchom `woeusb` jako root</description>\n"
        "		\n"
        "		<message>Authentication is required to run `woeusb` as SuperUser.</message>\n"
        "		<message xml:lang=\"zh_TW\">以超級使用者(SuperUser)身份執行 `woeusb` 需要通過身份驗證。</message>\n"
        "		<message xml:lang=\"pl_PL\">Wymagana jest autoryzacja do uruchomienia `woeusb` jako root</message>\n"
        "		\n"
        "		<defaults>\n"
        "			<allow_any>auth_admin</allow_any>\n"
        "			<allow_inactive>auth_admin</allow_inactive>\n"
        "			<allow_active>auth_admin_keep</allow_active>\n"
        "		</defaults>\n"
        "		\n"
        "		<annotate key=\"org.freedesktop.policykit.exec.path\">/usr/local/bin/woeusbgui</annotate>\n"
        "   		<annotate key=\"org.freedesktop.policykit.exec.allow_gui\">true</annotate>\n"
        "	</action>\n"
        "	<action id=\"com.github.slacka.woeusb.run-gui-using-pkexec-local\">\n"
        "		<description>Run `woeusb` as SuperUser</description>\n"
        "		<description xml:lang=\"zh_TW\">以超級使用者(SuperUser)身份執行 `woeusb`</description>\n"
        "		<description xml:lang=\"pl_PL\">Uruchom `woeusb` jako root</description>\n"
        "\n"
        "		<message>Authentication is required to run `woeusb` as SuperUser.</message>\n"
        "		<message xml:lang=\"zh_TW\">以超級使用者(SuperUser)身份執行 `woeusb` 需要通過身份驗證。</message>\n"
        "		<message xml:lang=\"pl_PL\">Wymagana jest autoryzacja do uruchomienia `woeusb` jako root</message>\n"
        "\n"
        "		<defaults>\n"
        "			<allow_any>auth_admin</allow_any>\n"
        "			<allow_inactive>auth_admin</allow_inactive>\n"
        "			<allow_active>auth_admin_keep</allow_active>\n"
        "		</defaults>\n"
        "\n"
        "		<annotate key=\"org.freedesktop.policykit.exec.path\">/usr/local/bin/woeusbgui</annotate>\n"
        "   		<annotate key=\"org.freedesktop.policykit.exec.allow_gui\">true</annotate>\n"
        "	</action>\n"
        "</policyconfig>"
    )
    for action in dom.getElementsByTagName('action'):
        if action.getAttribute('id') == "com.github.slacka.woeusb.run-gui-using-pkexec":
            for annotate in action.getElementsByTagName('annotate'):
                if annotate.getAttribute('key') == "org.freedesktop.policykit.exec.path":
                    annotate.childNodes[0].nodeValue = path

    with open("/usr/share/polkit-1/actions/com.github.woeusb.woeusb-ng.policy", "w") as file:
        file.write(dom.toxml())


def detect_windows_version(source_fs_mountpoint):
    """
    Detect Windows version from installation media
    
    Args:
        source_fs_mountpoint (str): Path to mounted Windows installation media
        
    Returns:
        tuple: (version, build_number, is_windows11)
            version (str): Windows version (e.g., "10", "11")
            build_number (str): Windows build number
            is_windows11 (bool): True if Windows 11, False otherwise
    """
    # Default values
    version = "unknown"
    build_number = "unknown"
    is_windows11 = False
    
    # Check for Windows 11 specific files
    win11_indicators = [
        os.path.join(source_fs_mountpoint, "sources", "appraiserres.dll"),
        os.path.join(source_fs_mountpoint, "sources", "compatresources.dll")
    ]
    
    for indicator in win11_indicators:
        if os.path.exists(indicator):
            is_windows11 = True
            version = "11"
            break
    
    # Try to get version from setup files
    setup_dll = os.path.join(source_fs_mountpoint, "sources", "setupprep.exe")
    if os.path.exists(setup_dll):
        try:
            # Extract version information using strings command
            result = subprocess.run(
                ["strings", setup_dll], 
                capture_output=True, 
                text=True
            )
            
            # Look for version patterns
            version_match = re.search(r'(Windows\s+(\d+))', result.stdout)
            build_match = re.search(r'(\d{5}\.\d+)', result.stdout)
            
            if version_match and not is_windows11:
                version = version_match.group(2)
            
            if build_match:
                build_number = build_match.group(1)
                
                # Windows 11 builds are typically 22000 or higher
                if int(build_number.split('.')[0]) >= 22000:
                    is_windows11 = True
                    version = "11"
        except (subprocess.SubprocessError, OSError, ValueError):
            pass
    
    # Check cversion.ini for older Windows versions
    cversion_path = os.path.join(source_fs_mountpoint, "sources", "cversion.ini")
    if os.path.exists(cversion_path):
        try:
            with open(cversion_path, 'r') as f:
                content = f.read()
                
                # Look for version information
                if "MinClient=7" in content:
                    version = "7"
                elif "MinClient=8" in content:
                    version = "8"
                elif "MinClient=10" in content:
                    version = "10"
                
                # Look for build number
                build_match = re.search(r'BuildNumber=(\d+)', content)
                if build_match:
                    build_number = build_match.group(1)
        except (IOError, OSError):
            pass
    
    return (version, build_number, is_windows11)

def run_command(command_list, message=None, error_message=None, suppress_errors=False, capture_output=False, text=True, check=False):
    """
    Stub for a centralized command execution function.
    Actual implementation would use subprocess.run.
    """
    if message and verbose: # Check verbose before printing non-error messages
        print_with_color(message, "blue")

    # Simulate command execution for testing purposes
    # In a real scenario, this would use subprocess.run()
    # For now, just print the command if verbose and return 0 (success)
    # or 1 if a known failing command for tests is passed.
    if verbose:
        print_with_color(f"Executing (stubbed): {' '.join(command_list)}", "magenta")

    if "fail_command_test" in command_list: # For testing error paths
        if error_message:
            print_with_color(error_message, "red")
        return 1

    # Mock common successful outcomes for tests
    if command_list[0] == "parted" and "print" in command_list:
        # Simulate parted print output for get_partition_info
        # This is a very basic mock. A real test might need more sophisticated output.
        mock_output = "BYT;\n/dev/sdX:1000MB:scsi:512:512:msdos:Mock USB Disk;\n1:1MB:501MB:500MB:fat32::boot;\n2:501MB:1000MB:499MB:fat16::;\n"
        if capture_output:
            return subprocess.CompletedProcess(command_list, 0, stdout=mock_output if text else mock_output.encode(), stderr="")
        else:
            return 0


    if capture_output:
        return subprocess.CompletedProcess(command_list, 0, stdout="" if text else b"", stderr="")
    return 0 # Assume success

def get_partition_info(partition_device):
    """
    Stub for getting partition information (e.g., end sector).
    A real implementation would use lsblk or parted.
    """
    print_with_color(f"STUB: Getting info for partition {partition_device}", "magenta") # Corrected: removed utils. prefix
    if partition_device.endswith("1"): # Assuming /dev/sdX1
        return {"end_sector": 1024000} # Example end sector for a ~500MB partition
    return None
