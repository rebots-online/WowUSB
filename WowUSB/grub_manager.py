#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
GRUB2 management utilities for WowUSB-DS9.
Handles GRUB2 installation and dynamic configuration generation.
"""

import os
import subprocess
import shutil
import WowUSB.utils as utils
from WowUSB.miscellaneous import i18n as _

# Basic template for grub.cfg using f-strings
GRUB_CFG_TEMPLATE = """\
set timeout=10
set default=0
set theme=/boot/grub/themes/wowusb/theme.txt

# Load necessary modules
insmod part_gpt
insmod part_msdos
insmod fat
insmod ntfs
insmod exfat
insmod f2fs
insmod btrfs
insmod udf
insmod iso9660
insmod chain
insmod search_fs_uuid
insmod search_label
insmod loopback
insmod linux
insmod initrd
insmod normal # for `normal` command if needed
insmod efi_uga # for graphical console in EFI
insmod efi_gop # for graphical console in EFI
insmod all_video # tries to load all available video drivers

# Graphics settings (optional, adjust as needed)
if loadfont unicode ; then
  set gfxmode=auto
  set gfxpayload=keep
  insmod gfxterm
  insmod png
  terminal_output gfxterm
fi

{windows_entry}

{linux_install_entry}

# --- Linux ISOs ---
submenu "Boot Linux ISOs from /boot/iso/" {{
{iso_entries}
}}

# --- Utility Menu ---
submenu "Utilities" {{
    menuentry "Reboot" {{
        reboot
    }}
    menuentry "Shutdown" {{
        halt
    }}
    menuentry "UEFI Firmware Settings (UEFI only)" {{
        fwsetup
    }}
}}
"""

WINDOWS_ENTRY_TEMPLATE_UEFI = """\
menuentry "Boot Windows (UEFI)" --class windows {{
    echo "Loading Windows (UEFI)..."
    search --no-floppy --fs-uuid --set=root {windows_partition_uuid}
    chainloader /efi/microsoft/boot/bootmgfw.efi
}}
"""

WINDOWS_ENTRY_TEMPLATE_BIOS = """\
menuentry "Boot Windows (Legacy BIOS)" --class windows {{
    echo "Loading Windows (Legacy BIOS)..."
    search --no-floppy --fs-uuid --set=root {windows_partition_uuid}
    ntldr /bootmgr
}}
"""

# For dual UEFI/BIOS entry, we might need to check boot method or provide separate entries.
# For simplicity, we'll initially generate based on the primary GRUB target or offer both.
# A more advanced approach could use GRUB's detection capabilities.

LINUX_INSTALL_ENTRY_TEMPLATE = """\
menuentry "Boot Installed Linux ({linux_name})" --class gnu-linux {{
    echo "Loading Installed Linux ({linux_name})..."
    search --no-floppy --fs-uuid --set=root {linux_rootfs_uuid}
    linux /boot/vmlinuz root=UUID={linux_rootfs_uuid} ro quiet {kernel_opts}
    initrd /boot/initrd.img
}}
"""

# Define a basic set of distro configurations for loopback booting
# Kernel/initrd paths and boot options can be quite varied.
# This is a simplified starting point.
DISTRO_LOOPBACK_CONFIGS = {
    "ubuntu": {
        "kernels": ["/casper/vmlinuz", "/casper/vmlinuz.efi"],
        "initrds": ["/casper/initrd.lz", "/casper/initrd"],
        "options": "iso-scan/filename={iso_path} boot=casper quiet splash ---",
        "name_pattern": "Ubuntu"
    },
    "debian": {
        "kernels": ["/live/vmlinuz", "/install.*/vmlinuz"], # Covers live and netinstall
        "initrds": ["/live/initrd.img", "/install.*/initrd.gz"],
        "options": "findiso={iso_path} boot=live quiet splash components ---",
        "name_pattern": "Debian"
    },
    "fedora": {
        "kernels": ["/images/pxeboot/vmlinuz"],
        "initrds": ["/images/pxeboot/initrd.img"],
        "options": "iso-scan/filename={iso_path} root=live:CDLABEL={iso_label} rd.live.image quiet",
        "name_pattern": "Fedora"
    },
    "arch": { # Arch based like Manjaro, EndeavourOS often have more complex paths
        "kernels": ["/arch/boot/vmlinuz-linux", "/boot/vmlinuz-x86_64"],
        "initrds": ["/arch/boot/initramfs-linux.img", "/boot/intel_ucode.img /boot/amd_ucode.img /boot/initramfs-x86_64.img"], # Arch can have multiple initrds
        "options": "img_dev=/dev/disk/by-label/{iso_label} img_loop={iso_path} earlymodules=loop aufs_type=RAM rw quiet splash",
        "name_pattern": "Arch"
    },
    "linuxmint": {
        "kernels": ["/casper/vmlinuz"],
        "initrds": ["/casper/initrd.lz"],
        "options": "iso-scan/filename={iso_path} boot=casper quiet splash ---",
        "name_pattern": "Linux Mint"
    },
    "manjaro": {
        "kernels": ["/boot/vmlinuz-*"], # Wildcard might be needed
        "initrds": ["/boot/initramfs-*.img"],
        "options": "img_dev=/dev/disk/by-label/{iso_label} img_loop={iso_path} misobasedir=manjaro quiet splash",
        "name_pattern": "Manjaro"
    }
    # More distros can be added here
}


def check_grub_dependencies():
    """Checks for grub-install and related tools."""
    missing_deps = []
    if not utils.check_command("grub-install"):
        missing_deps.append("grub-install (from grub2-common, grub-pc, grub-efi packages usually)")
    if not utils.check_command("grub-mkimage"): # Often used by grub-install
        missing_deps.append("grub-mkimage")
    # os-prober is not strictly a dep for our manual config, but good to note if considering it.
    return missing_deps

def install_grub(target_device, efi_mount_point, boot_mount_point):
    """
    Installs GRUB2 for both UEFI and Legacy BIOS.

    Args:
        target_device (str): The main block device (e.g., /dev/sdX).
        efi_mount_point (str): Mount point for the EFI System Partition.
        boot_mount_point (str): Mount point for the /boot partition (can be the ESP or a separate one).
                                This is where GRUB's core files (/boot/grub) will reside.

    Returns:
        bool: True on success, False on failure.
    """
    utils.print_with_color(_("Installing GRUB2..."), "blue")

    deps = check_grub_dependencies()
    if deps:
        utils.print_with_color(_("Error: Missing GRUB dependencies: {0}").format(", ".join(deps)), "red")
        return False

    # Ensure mount points exist
    if not os.path.isdir(efi_mount_point):
        utils.print_with_color(_("Error: EFI mount point {0} does not exist.").format(efi_mount_point), "red")
        return False
    if not os.path.isdir(boot_mount_point):
        utils.print_with_color(_("Error: Boot mount point {0} does not exist.").format(boot_mount_point), "red")
        return False

    # Ensure /boot/grub directory exists on the boot_mount_point for grub.cfg later
    os.makedirs(os.path.join(boot_mount_point, "grub"), exist_ok=True)


    # Install GRUB for x86_64-efi
    # The --boot-directory points to where /boot/grub/* will be placed.
    # The --efi-directory points to the root of the ESP.
    cmd_efi = [
        "grub-install",
        "--target=x86_64-efi",
        f"--efi-directory={efi_mount_point}",
        f"--boot-directory={boot_mount_point}", # This means GRUB files go to boot_mount_point/grub
        "--removable",  # For better portability, installs to /EFI/BOOT/BOOTX64.EFI
        "--recheck",
        # No device needed here when --removable and efi-directory are used properly
    ]
    utils.print_with_color(_("Installing GRUB for UEFI (x86_64-efi)..."), "blue")
    if utils.run_command(cmd_efi, error_message=_("Failed to install GRUB for UEFI.")):
        # Try without target_device if it fails, some versions of grub-install might not need it with --removable
        if utils.run_command(cmd_efi[:-1] if cmd_efi[-1] == target_device else cmd_efi, error_message=_("Failed to install GRUB for UEFI (attempt 2).")):
             return False

    # Install GRUB for i386-pc (Legacy BIOS)
    # The --boot-directory points to where /boot/grub/* will be placed.
    # The target_device is where the MBR boot code will be written.
    cmd_bios = [
        "grub-install",
        "--target=i386-pc",
        f"--boot-directory={boot_mount_point}", # GRUB files go to boot_mount_point/grub
        "--recheck",
        target_device  # Install to MBR of this device
    ]
    utils.print_with_color(_("Installing GRUB for Legacy BIOS (i386-pc)..."), "blue")
    if utils.run_command(cmd_bios, error_message=_("Failed to install GRUB for Legacy BIOS.")):
        return False

    utils.print_with_color(_("GRUB2 installation completed."), "green")
    return True


def generate_grub_cfg(boot_mount_point, windows_partition_uuid, payload_partition_uuid=None, linux_install_details=None):
    """
    Generates grub.cfg content.

    Args:
        boot_mount_point (str): Mount point of the partition where /boot/grub resides.
        windows_partition_uuid (str): PARTUUID of the Windows-To-Go partition.
        payload_partition_uuid (str, optional): PARTUUID of the payload/data partition (for ISOs).
        linux_install_details (dict, optional): Details for a full Linux install.
            Expected keys: 'uuid' (rootfs PARTUUID), 'name' (e.g. "Ubuntu 22.04 F2FS"), 'kernel_opts' (additional kernel options)

    Returns:
        str: The generated grub.cfg content or None on failure.
    """
    utils.print_with_color(_("Generating grub.cfg..."), "blue")

    windows_entry_uefi = WINDOWS_ENTRY_TEMPLATE_UEFI.format(windows_partition_uuid=windows_partition_uuid)
    windows_entry_bios = WINDOWS_ENTRY_TEMPLATE_BIOS.format(windows_partition_uuid=windows_partition_uuid)

    # For now, include both Windows entries. User can choose or GRUB might pick one.
    # A more sophisticated setup could detect boot mode within GRUB itself.
    windows_entry_combined = f"{windows_entry_uefi}\n{windows_entry_bios}"


    iso_entries_str = ""
    iso_dir_path = os.path.join(boot_mount_point, "iso") # ISOs expected in /boot/iso/ on the boot partition

    if payload_partition_uuid: # If payload partition is distinct and ISOs are there
        # This part needs refinement: ISOs might be on the payload partition, not the boot partition.
        # For now, assuming ISOs are copied to a standard /boot/iso on the BOOT partition.
        # If ISOs are on payload, the grub.cfg needs to search for payload_partition_uuid first.
        # This example assumes ISOs are on the same partition as /boot/grub (boot_mount_point).
        # Let's adjust to expect ISOs in boot_mount_point/iso/
        pass # Current iso_dir_path is already set to boot_mount_point/iso

    if os.path.isdir(iso_dir_path):
        utils.print_with_color(_("Scanning for ISOs in {0}...").format(iso_dir_path), "blue")
        for filename in sorted(os.listdir(iso_dir_path)):
            if filename.lower().endswith(".iso"):
                iso_full_path = os.path.join(iso_dir_path, filename) # Path on the system generating cfg
                iso_grub_path = os.path.join("/boot/iso", filename)  # Path GRUB will use relative to its root

                # Try to get ISO label (needed for some distro configs)
                iso_label = "USB_ISO" # Default label
                try:
                    # Use isoinfo or similar to get volume ID. blkid might also work for some ISOs.
                    # For simplicity, we'll often rely on filename matching or assume a common label.
                    # result = subprocess.run(['blkid', '-s', 'LABEL', '-o', 'value', iso_full_path], capture_output=True, text=True)
                    # if result.returncode == 0 and result.stdout.strip():
                    #    iso_label = result.stdout.strip()
                    # else: # Fallback for isoinfo
                    res_iso = subprocess.run(['isoinfo', '-d', '-i', iso_full_path], capture_output=True, text=True)
                    for line in res_iso.stdout.splitlines():
                        if line.startswith("Volume Id:"):
                            iso_label = line.split(":",1)[1].strip()
                            break
                except Exception as e:
                    utils.print_with_color(_("Could not determine label for {0}: {1}").format(filename, str(e)), "yellow")

                matched_distro = False
                for distro_key, config in DISTRO_LOOPBACK_CONFIGS.items():
                    if config["name_pattern"].lower() in filename.lower():
                        utils.print_with_color(_("Found {0} ISO: {1}").format(config["name_pattern"], filename), "green")

                        kernel_path_found = None
                        for k_path_template in config["kernels"]:
                            # This check needs to be against the *mounted* ISO, not just a path string.
                            # For loopback.cfg, we assume paths are correct.
                            kernel_path_found = k_path_template # Assume it's there for now
                            break

                        initrd_path_found = None
                        for i_path_template in config["initrds"]:
                            initrd_path_found = i_path_template # Assume it's there for now
                            break

                        if kernel_path_found and initrd_path_found:
                            iso_entries_str += f"    menuentry \"Boot {filename}\" --class gnu-linux {{\n"
                            iso_entries_str += f"        set isofile=\"{iso_grub_path}\"\n"
                            # Some distros need the ISO to be on a partition GRUB can easily find by label/UUID
                            # If ISOs are on payload_partition_uuid:
                            # iso_entries_str += f"        search --no-floppy --fs-uuid --set=root_iso {payload_partition_uuid}\n"
                            # iso_entries_str += f"        loopback loop ($root_iso)$isofile\n"
                            # If ISOs are on the same partition as /boot/grub (ESP or dedicated /boot)
                            iso_entries_str +=  "        loopback loop $isofile\n" # Assumes $root is already set to boot partition
                            iso_entries_str += f"        linux (loop){kernel_path_found} {config['options'].format(iso_path=iso_grub_path, iso_label=iso_label)}\n"
                            iso_entries_str += f"        initrd (loop){initrd_path_found}\n"
                            iso_entries_str +=  "    }\n\n"
                            matched_distro = True
                            break
                if not matched_distro:
                    utils.print_with_color(_("Warning: No specific GRUB config for ISO: {0}. Skipping.").format(filename), "yellow")
    else:
        utils.print_with_color(_("ISO directory {0} not found. No ISOs will be added to GRUB menu.").format(iso_dir_path), "yellow")
        iso_entries_str = "    menuentry \"No ISOs found in /boot/iso/\" { true }\n"


    linux_install_entry_str = ""
    if linux_install_details and linux_install_details.get('uuid'):
        name = linux_install_details.get('name', 'Installed Linux')
        kernel_opts = linux_install_details.get('kernel_opts', '')
        linux_install_entry_str = LINUX_INSTALL_ENTRY_TEMPLATE.format(
            linux_name=name,
            linux_rootfs_uuid=linux_install_details['uuid'],
            kernel_opts=kernel_opts
        )

    final_cfg = GRUB_CFG_TEMPLATE.format(
        windows_entry=windows_entry_combined,
        iso_entries=iso_entries_str,
        linux_install_entry=linux_install_entry_str
    )

    grub_cfg_path = os.path.join(boot_mount_point, "grub", "grub.cfg")
    try:
        with open(grub_cfg_path, "w") as f:
            f.write(final_cfg)
        utils.print_with_color(_("grub.cfg generated successfully at {0}").format(grub_cfg_path), "green")

        # Attempt to copy a theme if it exists
        theme_source_dir = os.path.join(os.path.dirname(__file__), "data", "grub-themes", "wowusb")
        theme_target_dir = os.path.join(boot_mount_point, "grub", "themes", "wowusb")
        if os.path.isdir(theme_source_dir):
            utils.print_with_color(_("Copying GRUB theme..."), "blue")
            shutil.copytree(theme_source_dir, theme_target_dir, dirs_exist_ok=True)
        else:
            utils.print_with_color(_("GRUB theme not found at {0}, skipping.").format(theme_source_dir), "yellow")
            # Create a dummy theme.txt if one is referenced but not found to avoid GRUB errors
            if not os.path.exists(os.path.join(theme_target_dir,"theme.txt")):
                 os.makedirs(theme_target_dir, exist_ok=True)
                 with open(os.path.join(theme_target_dir,"theme.txt"), "w") as tf:
                     tf.write("# Basic theme placeholder\n")


    except IOError as e:
        utils.print_with_color(_("Error writing grub.cfg to {0}: {1}").format(grub_cfg_path, e), "red")
        return None

    return final_cfg


if __name__ == '__main__':
    # Example Usage (for testing purposes)
    # This assumes you have a layout similar to what partitioning.py creates
    # and have mounted the partitions appropriately.
    # e.g., ESP mounted at /tmp/myusb/efi, BOOT_PART mounted at /tmp/myusb/boot
    # and ISOs in /tmp/myusb/boot/iso/

    if os.geteuid() != 0:
        print("This script might need root for grub-install if you test that part.")

    # Create dummy mount points and ISOs for testing generate_grub_cfg
    test_boot_mnt = "/tmp/test_grub_boot"
    test_efi_mnt = "/tmp/test_grub_efi" # if testing install_grub
    dummy_iso_dir = os.path.join(test_boot_mnt, "iso")

    os.makedirs(dummy_iso_dir, exist_ok=True)
    os.makedirs(os.path.join(test_boot_mnt, "grub"), exist_ok=True) # for grub.cfg
    os.makedirs(test_efi_mnt, exist_ok=True) # for install_grub

    # Create dummy ISO files
    dummy_isos = ["ubuntu-22.04-desktop-amd64.iso", "fedora-workstation-live-x86_64-38.iso", "unknown_distro.iso"]
    for iso in dummy_isos:
        with open(os.path.join(dummy_iso_dir, iso), "w") as f:
            f.write("This is a dummy ISO file.")

    print(f"Created dummy ISOs in {dummy_iso_dir}")

    # Dummy UUIDs
    win_uuid = "DUMMY-WIN-UUID-0001"
    payload_uuid = "DUMMY-PAYLOAD-UUID-0002"
    linux_install = {
        "uuid": "DUMMY-LINUX-FS-UUID-0003",
        "name": "My Custom Linux",
        "kernel_opts": "elevator=noop"
    }

    print("\n--- Testing generate_grub_cfg ---")
    cfg_content = generate_grub_cfg(test_boot_mnt, win_uuid, payload_uuid, linux_install)
    if cfg_content:
        print("\nGenerated grub.cfg content:")
        # print(cfg_content) # Full content can be long
        print(f"grub.cfg written to {os.path.join(test_boot_mnt, 'grub', 'grub.cfg')}")
    else:
        print("Failed to generate grub.cfg")

    # To test install_grub, you'd need a real loop device or USB stick.
    # Example (DANGEROUS, use a loop device for safety):
    # print("\n--- Testing install_grub (requires root and a target device) ---")
    # target_dev = "/dev/loopX" # Replace with a SAFE loop device setup
    # if os.path.exists(target_dev) and input(f"Test GRUB install on {target_dev}? (yes/no): ").lower() == 'yes':
    #     if install_grub(target_dev, test_efi_mnt, test_boot_mnt):
    #         print(f"GRUB install simulated/attempted on {target_dev}")
    #     else:
    #         print(f"GRUB install failed/simulated failure on {target_dev}")

    # Cleanup dummy files and dirs
    print(f"\nCleaning up test directories: {test_boot_mnt}, {test_efi_mnt}")
    try:
        shutil.rmtree(test_boot_mnt)
        shutil.rmtree(test_efi_mnt)
    except Exception as e:
        print(f"Error during cleanup: {e}")

    print("\nNote: For full install_grub testing, manual setup of a loop device or a dedicated test USB is recommended.")
    print("The generate_grub_cfg test created a file in /tmp/test_grub_boot/grub/grub.cfg")

```
