#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Linux installation utilities for WowUSB-DS9.
Handles installing a basic Linux system to the F2FS payload partition
using debootstrap (for Debian/Ubuntu) or pacstrap (for Arch).
"""

import os
import subprocess
import shutil
import WowUSB.utils as utils
from WowUSB.miscellaneous import i18n as _

# Define a default Ubuntu release if not specified
DEFAULT_UBUNTU_RELEASE = "focal" # Ubuntu 20.04 LTS
DEFAULT_DEBIAN_RELEASE = "bullseye" # Debian 11

def check_linux_installer_dependencies(distro_type):
    """Checks for debootstrap or pacstrap."""
    missing_deps = []
    if distro_type.lower() in ["ubuntu", "debian"]:
        if not utils.check_command("debootstrap"):
            missing_deps.append("debootstrap")
    elif distro_type.lower() == "arch":
        if not utils.check_command("pacstrap"):
            missing_deps.append("arch-install-scripts (provides pacstrap)")
    else:
        missing_deps.append(f"Unsupported distro_type for installer: {distro_type}")
    return missing_deps

def generate_fstab(rootfs_mount_point, payload_uuid, payload_fs_type="f2fs"):
    """
    Generates a basic /etc/fstab file within the chroot.
    """
    fstab_path = os.path.join(rootfs_mount_point, "etc", "fstab")
    utils.print_with_color(_("Generating fstab at {0}...").format(fstab_path), "blue")

    # Basic fstab entries
    fstab_content = f"""\
# /etc/fstab: static file system information.
#
# Use 'blkid' to print the universally unique identifier for a
# device; this may be used with UUID= as a more robust way to name devices
# that works even if disks are added and removed. See fstab(5).
#
# <file system> <mount point>   <type>  <options>       <dump>  <pass>
UUID={payload_uuid}  /               {payload_fs_type}   defaults,discard,noatime,compress_algorithm=zstd:1    0 1
# Example for ESP (if needed to be mounted by the installed Linux, usually handled by GRUB from main USB boot)
# UUID=<ESP_UUID>  /boot/efi       vfat    umask=0077      0 1

# Swap (if a swap partition/file was created, not handled by this basic script)
# /swapfile       none            swap    sw              0 0

# Tmpfs for /tmp
tmpfs           /tmp            tmpfs   defaults,nosuid,nodev        0 0
"""
    try:
        with open(fstab_path, "w") as f:
            f.write(fstab_content)
        utils.print_with_color(_("Successfully generated {0}.").format(fstab_path), "green")
    except IOError as e:
        utils.print_with_color(_("Error writing fstab file {0}: {1}").format(fstab_path, e), "red")
        return False
    return True


def run_in_chroot(rootfs_mount_point, command_list, error_message=None):
    """
    Runs a command within the chroot environment.
    Manages mounting/unmounting of /proc, /sys, /dev.
    """
    mount_points = {
        "proc": os.path.join(rootfs_mount_point, "proc"),
        "sys": os.path.join(rootfs_mount_point, "sys"),
        "dev": os.path.join(rootfs_mount_point, "dev"),
        "dev_pts": os.path.join(rootfs_mount_point, "dev", "pts"),
    }

    mounted_successfully = []

    try:
        # Mount necessary pseudo-filesystems
        utils.print_with_color(_("Binding pseudo-filesystems for chroot..."), "blue")
        for name, path in mount_points.items():
            os.makedirs(path, exist_ok=True)
            source = name if name != "dev_pts" else "devpts" # "proc", "sys", "dev", "devpts"
            options = None
            if source == "devpts": # devpts needs specific options
                options = "gid=5,mode=620"

            cmd = ["mount", "--bind" if source != "devpts" else "-t", source, path]
            if options and source == "devpts": # For mount -t devpts devpts /target/dev/pts -o gid=5,mode=620
                cmd = ["mount", "-t", "devpts", "devpts", path, "-o", options]
            elif source == "devpts": # Fallback if options method is tricky
                 cmd = ["mount", "-t", "devpts", "devpts", path]


            if utils.run_command(cmd,
                                 message=_("Mounting {0} to {1}").format(source, path),
                                 error_message=_("Failed to mount {0} for chroot.").format(source)):
                # If one fails, unmount those already mounted and return
                raise Exception(f"Failed to mount {source}")
            mounted_successfully.append(path)

        # Construct the chroot command
        chroot_cmd = ["chroot", rootfs_mount_point] + command_list
        utils.print_with_color(_("Running in chroot: {0}").format(" ".join(command_list)), "blue")

        # Execute the command in chroot
        # We need to handle LANG/LC_ALL for commands inside chroot to avoid locale errors
        env = os.environ.copy()
        env["LANG"] = "C.UTF-8"
        env["LC_ALL"] = "C.UTF-8"

        process = subprocess.Popen(chroot_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            if error_message:
                utils.print_with_color(error_message, "red")
            utils.print_with_color(_("Chroot command failed. Return code: {0}").format(process.returncode), "red")
            if stdout: utils.print_with_color(f"Stdout:\n{stdout}", "yellow")
            if stderr: utils.print_with_color(f"Stderr:\n{stderr}", "red")
            return False
        else:
            if stdout and utils.verbose: utils.print_with_color(f"Chroot Stdout:\n{stdout}", "green")
            if stderr and utils.verbose: utils.print_with_color(f"Chroot Stderr:\n{stderr}", "yellow")
            utils.print_with_color(_("Chroot command successful: {0}").format(" ".join(command_list)), "green")
            return True

    except Exception as e:
        utils.print_with_color(_("Exception during chroot operation: {0}").format(e), "red")
        return False
    finally:
        # Unmount pseudo-filesystems in reverse order of mounting
        utils.print_with_color(_("Unbinding pseudo-filesystems..."), "blue")
        for path in reversed(mounted_successfully):
            # Retry unmount a few times as it can sometimes fail if busy
            for attempt in range(3):
                if utils.run_command(["umount", "-l", path], # -l for lazy unmount
                                     message=_("Unmounting {0} (attempt {1})").format(path, attempt + 1),
                                     suppress_errors=(attempt < 2)): # Suppress error for first 2 attempts
                    break
                time.sleep(1)
            else: # If loop completes without break
                 utils.print_with_color(_("Failed to unmount {0} after multiple attempts.").format(path), "red")


def install_linux_to_f2fs(target_payload_partition, payload_uuid, distro_type, rootfs_mount_point,
                          distro_release=None, http_proxy=None):
    """
    Installs a basic Linux system to the F2FS payload partition.

    Args:
        target_payload_partition (str): Device path of the F2FS partition (e.g., /dev/sdX4).
        payload_uuid (str): PARTUUID of the payload partition.
        distro_type (str): 'ubuntu', 'debian', or 'arch'.
        rootfs_mount_point (str): Temporary mount point for the rootfs.
        distro_release (str, optional): Specific release for Debian/Ubuntu (e.g., 'focal', 'bullseye').
        http_proxy (str, optional): HTTP proxy for debootstrap/pacstrap.

    Returns:
        bool: True on success, False on failure.
    """
    utils.print_with_color(
        _("Starting Linux ({0}) installation to {1} (mounted at {2})")
        .format(distro_type, target_payload_partition, rootfs_mount_point), "blue"
    )

    deps = check_linux_installer_dependencies(distro_type)
    if deps:
        utils.print_with_color(_("Error: Missing Linux installer dependencies: {0}").format(", ".join(deps)), "red")
        return False

    # Ensure payload partition is mounted at rootfs_mount_point
    # This should be done by the caller, but we can double check or attempt mount.
    if not os.path.ismount(rootfs_mount_point):
        utils.print_with_color(_("Mounting {0} to {1}...").format(target_payload_partition, rootfs_mount_point), "blue")
        os.makedirs(rootfs_mount_point, exist_ok=True)
        if utils.run_command(["mount", target_payload_partition, rootfs_mount_point],
                             error_message=_("Failed to mount payload partition {0}.").format(target_payload_partition)):
            return False

    env = os.environ.copy()
    if http_proxy:
        env["http_proxy"] = http_proxy
        env["https_proxy"] = http_proxy

    success = False
    if distro_type.lower() in ["ubuntu", "debian"]:
        release = distro_release or (DEFAULT_UBUNTU_RELEASE if distro_type.lower() == "ubuntu" else DEFAULT_DEBIAN_RELEASE)
        # Mirror URL might need to be configurable or detected
        mirror = f"http://deb.debian.org/debian" if distro_type.lower() == "debian" else f"http://archive.ubuntu.com/ubuntu/"

        cmd_debootstrap = [
            "debootstrap",
            "--arch=amd64",
            #"--variant=minbase", # For a smaller system
            release,
            rootfs_mount_point,
            mirror
        ]
        utils.print_with_color(_("Running debootstrap for {0} {1}...").format(distro_type, release), "blue")
        if utils.run_command(cmd_debootstrap, env=env, error_message=_("Debootstrap failed.")):
            success = True
        else:
            return False # Debootstrap failed

    elif distro_type.lower() == "arch":
        # Pacstrap needs a list of packages. 'base' is minimal. 'base-devel' for building.
        # 'linux' for kernel, 'linux-firmware' for hardware support.
        # 'f2fs-tools' for F2FS support within the installed system.
        # 'grub' to configure GRUB from within chroot.
        # 'networkmanager' or similar for networking.
        packages_to_install = ["base", "linux", "linux-firmware", "f2fs-tools", "grub", "networkmanager", "sudo", "vim", "man-db"]
        cmd_pacstrap = [
            "pacstrap", "-c", "-K", # -K to init pacman keyring, -c to use host cache if available
            rootfs_mount_point
        ] + packages_to_install

        utils.print_with_color(_("Running pacstrap... This may take a while."), "blue")
        # Pacstrap can be very verbose, capture output if not in utils.verbose mode
        if utils.run_command(cmd_pacstrap, env=env, error_message=_("Pacstrap failed.")):
            success = True
        else:
            return False # Pacstrap failed
    else:
        utils.print_with_color(_("Unsupported distribution for full install: {0}").format(distro_type), "red")
        return False

    # --- Post-installation configuration ---
    if success:
        utils.print_with_color(_("Base system installed. Performing post-installation configuration..."), "blue")

        if not generate_fstab(rootfs_mount_point, payload_uuid, payload_fs_type="f2fs"): # Assuming F2FS for payload
            return False # Failed to generate fstab

        # Basic hostname and hosts file
        with open(os.path.join(rootfs_mount_point, "etc", "hostname"), "w") as f: f.write("wowusb-linux\n")
        with open(os.path.join(rootfs_mount_point, "etc", "hosts"), "w") as f:
            f.write("127.0.0.1 localhost\n")
            f.write("127.0.1.1 wowusb-linux\n") # For systems that use this convention
            f.write("::1       localhost ip6-localhost ip6-loopback\n")
            f.write("ff02::1   ip6-allnodes\n")
            f.write("ff02::2   ip6-allrouters\n")

        # Configure locales (basic example: en_US.UTF-8)
        if distro_type.lower() in ["ubuntu", "debian"]:
            run_in_chroot(rootfs_mount_point, ["apt-get", "update"])
            run_in_chroot(rootfs_mount_point, ["apt-get", "install", "-y", "locales", "sudo", "grub-pc", "grub-efi-amd64", "network-manager"]) # ensure grub and sudo
            with open(os.path.join(rootfs_mount_point, "etc", "locale.gen"), "a") as f: f.write("en_US.UTF-8 UTF-8\n")
            run_in_chroot(rootfs_mount_point, ["locale-gen"])
            run_in_chroot(rootfs_mount_point, ["update-locale", "LANG=en_US.UTF-8"])
        elif distro_type.lower() == "arch":
            with open(os.path.join(rootfs_mount_point, "etc", "locale.gen"), "a") as f: f.write("en_US.UTF-8 UTF-8\n") # Append, don't overwrite
            run_in_chroot(rootfs_mount_point, ["locale-gen"])
            with open(os.path.join(rootfs_mount_point, "etc", "locale.conf"), "w") as f: f.write("LANG=en_US.UTF-8\n")


        # Set root password (e.g., "root" - change this for security)
        # passwd command needs to be run interactively or with --stdin.
        # Example: echo "root:newpassword" | chpasswd
        utils.print_with_color(_("Setting root password to 'root' (CHANGE THIS LATER!)..."), "yellow")
        if not run_in_chroot(rootfs_mount_point, ["/bin/bash", "-c", "echo 'root:root' | chpasswd"]):
             utils.print_with_color(_("Failed to set root password."), "red")
             # Not returning false, as it's not critical for first boot if user can login via console

        # Add a user (e.g., "wowuser" with password "wowuser")
        utils.print_with_color(_("Adding user 'wowuser' with password 'wowuser' (CHANGE THIS LATER!)..."), "yellow")
        if not run_in_chroot(rootfs_mount_point,["useradd", "-m", "-G", "wheel,adm,sudo", "-s", "/bin/bash", "wowuser"]): # wheel for Arch, adm/sudo for Debian/Ubuntu
             utils.print_with_color(_("Failed to add user 'wowuser'."), "red")
        if not run_in_chroot(rootfs_mount_point, ["/bin/bash", "-c", "echo 'wowuser:wowuser' | chpasswd"]):
             utils.print_with_color(_("Failed to set password for 'wowuser'."), "red")


        # Install and configure GRUB within the chroot
        # This GRUB install is for the installed Linux to be able to update its own GRUB if needed,
        # not for the main USB GRUB, which is handled by grub_manager.py
        # However, running grub-install from chroot might be complex if it needs to target the USB MBR/ESP.
        # For now, we ensure GRUB packages are there. The main GRUB should boot this system.
        # If we want this installed Linux to manage its own boot (e.g. if copied to internal drive later),
        # then a full grub-install + update-grub in chroot would be needed.
        utils.print_with_color(_("Ensuring GRUB is configured within the installed system..."), "blue")
        if distro_type.lower() in ["ubuntu", "debian"]:
            # update-grub should generate a config based on the chrooted system
            if not run_in_chroot(rootfs_mount_point, ["update-grub"]):
                utils.print_with_color(_("update-grub failed in chroot."), "yellow")
        elif distro_type.lower() == "arch":
            # Arch uses grub-mkconfig
            # Need to specify bootloader-id for ESP install
            # grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=ARCH_GRUB --recheck
            # grub-install --target=i386-pc --recheck /dev/sdX (targetting the installed system's disk, not USB here)
            # For now, just generate the config:
            grub_cfg_path_chroot = "/boot/grub/grub.cfg" # Path inside chroot
            if not run_in_chroot(rootfs_mount_point, ["grub-mkconfig", "-o", grub_cfg_path_chroot]):
                 utils.print_with_color(_("grub-mkconfig failed in chroot for Arch."), "yellow")

        # Enable NetworkManager
        utils.print_with_color(_("Enabling NetworkManager..."), "blue")
        if os.path.exists(os.path.join(rootfs_mount_point, "usr", "bin", "systemctl")):
            run_in_chroot(rootfs_mount_point, ["systemctl", "enable", "NetworkManager.service"])
        else: # SysVinit systems (less common for new installs)
            utils.print_with_color(_("systemctl not found, skipping NetworkManager enable (manual setup may be needed)."), "yellow")


        utils.print_with_color(_("Linux ({0}) installation and basic configuration complete.").format(distro_type), "green")
        success = True

    # Unmount payload partition (caller should handle this)
    # utils.run_command(["umount", rootfs_mount_point], suppress_errors=True)

    return success


if __name__ == '__main__':
    # Example Usage (for testing purposes, requires root)
    # BE VERY CAREFUL - THIS WILL MODIFY THE TARGET PARTITION
    if os.geteuid() != 0:
        print("This script needs to be run as root for debootstrap/pacstrap and mounting.")
    else:
        # --- Setup a loop device for testing ---
        # sudo losetup -f # Find free loop device, e.g., /dev/loop20
        # sudo dd if=/dev/zero of=f2fs_test.img bs=1G count=5
        # sudo losetup /dev/loop20 f2fs_test.img
        # sudo mkfs.f2fs /dev/loop20
        # PAYLOAD_PART = "/dev/loop20"
        # PAYLOAD_UUID = subprocess.check_output(["blkid", "-s", "UUID", "-o", "value", PAYLOAD_PART]).decode().strip()
        # --- End loop device setup ---

        # Replace with your actual F2FS partition and its UUID
        # PAYLOAD_PART = "/dev/sdX4" # DANGEROUS: Use a test device or loopback
        # PAYLOAD_UUID = "YOUR-F2FS-PARTITION-UUID" # Get from blkid

        # Example: find a loop device and use it
        try:
            loop_device_img = "f2fs_linux_install_test.img"
            loop_setup_dev = None

            if not os.path.exists(loop_device_img):
                print(f"Creating dummy image {loop_device_img} (5GB)...")
                utils.run_command(["dd", "if=/dev/zero", f"of={loop_device_img}", "bs=1G", "count=5", "status=progress"])

            loop_device_find_proc = subprocess.run(["losetup", "--find", "--show", loop_device_img], capture_output=True, text=True, check=True)
            PAYLOAD_PART = loop_device_find_proc.stdout.strip()
            loop_setup_dev = PAYLOAD_PART # Keep track to clean up
            print(f"Using loop device: {PAYLOAD_PART} for image {loop_device_img}")

            print(f"Formatting {PAYLOAD_PART} as F2FS...")
            if not fs_handlers.F2fsFilesystemHandler.format_partition(PAYLOAD_PART, "LINUXF2FS"):
                raise Exception(f"Failed to format {PAYLOAD_PART}")

            time.sleep(1) # Let kernel catch up
            PAYLOAD_UUID_proc = subprocess.run(["blkid", "-s", "UUID", "-o", "value", PAYLOAD_PART], capture_output=True, text=True, check=True)
            PAYLOAD_UUID = PAYLOAD_UUID_proc.stdout.strip()
            if not PAYLOAD_UUID:
                PAYLOAD_PARTUUID_proc = subprocess.run(["blkid", "-s", "PARTUUID", "-o", "value", PAYLOAD_PART], capture_output=True, text=True, check=True)
                PAYLOAD_UUID = PAYLOAD_PARTUUID_proc.stdout.strip() # Use PARTUUID if UUID is not available (e.g. whole device loop)


            if not PAYLOAD_UUID:
                raise Exception(f"Could not get UUID/PARTUUID for {PAYLOAD_PART}")

            print(f"Target partition: {PAYLOAD_PART}, UUID/PARTUUID: {PAYLOAD_UUID}")

            MOUNT_POINT = "/mnt/test_linux_install"
            os.makedirs(MOUNT_POINT, exist_ok=True)

            # Choose distro: 'ubuntu' or 'arch' or 'debian'
            # DISTRO = "ubuntu"
            DISTRO = "arch"
            # DISTRO = "debian"

            # HTTP_PROXY = "http://your-proxy-server:port" # Optional
            HTTP_PROXY = None

            confirm = input(f"Install {DISTRO} to {PAYLOAD_PART} (mounted at {MOUNT_POINT})? (yes/no): ")
            if confirm.lower() == 'yes':
                install_success = install_linux_to_f2fs(
                    PAYLOAD_PART, PAYLOAD_UUID, DISTRO, MOUNT_POINT, http_proxy=HTTP_PROXY
                )
                if install_success:
                    print(f"{DISTRO} installation successful to {PAYLOAD_PART}.")
                    print(f"To inspect: sudo mount {PAYLOAD_PART} {MOUNT_POINT} (if not already mounted by script)")
                    print(f"Then explore {MOUNT_POINT}")
                    print(f"To chroot manually: for m in proc sys dev dev/pts; do sudo mount --bind /$m {MOUNT_POINT}/$m; done; sudo chroot {MOUNT_POINT}")
                else:
                    print(f"{DISTRO} installation failed.")

            # Unmount if mounted by script or for cleanup
            if os.path.ismount(MOUNT_POINT):
                print(f"Unmounting {MOUNT_POINT}...")
                utils.run_command(["umount", "-R", MOUNT_POINT], suppress_errors=True) # Recursive for any chroot mounts
                # shutil.rmtree(MOUNT_POINT) # only if created by this script and empty

        except Exception as e:
            print(f"An error occurred during testing: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if loop_setup_dev and os.path.exists(loop_setup_dev): # Check if loop_setup_dev was assigned
                print(f"Detaching loop device {loop_setup_dev}...")
                utils.run_command(["losetup", "-d", loop_setup_dev], suppress_errors=True)
            # if os.path.exists(loop_device_img):
            #     print(f"You can delete the test image: {loop_device_img}")
            if os.path.exists(MOUNT_POINT) and not os.listdir(MOUNT_POINT): # Remove if empty
                 shutil.rmtree(MOUNT_POINT, ignore_errors=True)
