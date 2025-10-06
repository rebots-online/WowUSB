#!/usr/bin/env python3

import os
import re
import subprocess


def usb_drive(show_all=False):
    devices_list = []

    lsblk = subprocess.run(["lsblk",
                            "--output", "NAME",
                            "--noheadings",
                            "--nodeps"], stdout=subprocess.PIPE).stdout.decode("utf-8")

    devices = re.sub("sr[0-9]|cdrom[0-9]", "", lsblk).split()

    for device in devices:
        if is_removable_and_writable_device(device):
            if not show_all:
                continue

        # FIXME: Needs a more reliable detection mechanism instead of simply assuming it is under /dev
        block_device = "/dev/" + device

        device_capacity = subprocess.run(["lsblk",
                                          "--output", "SIZE",
                                          "--noheadings",
                                          "--nodeps",
                                          block_device], stdout=subprocess.PIPE).stdout.decode("utf-8").strip()

        device_model = subprocess.run(["lsblk",
                                       "--output", "MODEL",
                                       "--noheadings",
                                       "--nodeps",
                                       block_device], stdout=subprocess.PIPE).stdout.decode("utf-8").strip()

        if device_model != "":
            devices_list.append([block_device, block_device + "(" + device_model + ", " + device_capacity + ")"])
        else:
            devices_list.append([block_device, block_device + "(" + device_capacity + ")"])

    return devices_list


def is_removable_and_writable_device(block_device_name):
    sysfs_block_device_dir = "/sys/block/" + block_device_name

    # We consider device not removable if the removable sysfs item not exist
    if os.path.isfile(sysfs_block_device_dir + "/removable"):
        with open(sysfs_block_device_dir + "/removable") as removable:
            removable_content = removable.read()

        with open(sysfs_block_device_dir + "/ro") as ro:
            ro_content = ro.read()

        if removable_content.strip("\n") == "1" and ro_content.strip("\n") == "0":
            return 0
        else:
            return 1
    else:
        return 1


def dvd_drive():
    devices_list = []
    find = subprocess.run(["find", "/sys/block",
                           "-maxdepth", "1",
                           "-mindepth", "1"], stdout=subprocess.PIPE).stdout.decode("utf-8").split()
    devices = []
    for device in find:
        tmp = re.findall("sr[0-9]", device)

        if tmp == []:
            continue

        devices.append([device, tmp[0]])

    for device in devices:
        optical_disk_drive_devfs_path = "/dev/" + device[1]

        with open(device[0] + "/device/model", "r") as model:
            model_content = model.read().strip()

        devices_list.append([optical_disk_drive_devfs_path, optical_disk_drive_devfs_path + " - " + model_content])

    return devices_list


def list_devices():
    """List all available USB and DVD devices"""
    import sys

    try:
        usb_devices = usb_drive(show_all=True)
        dvd_devices = dvd_drive()

        print("Available devices:")
        print("-" * 60)

        if usb_devices:
            print("USB Devices:")
            for device in usb_devices:
                print(f"  {device[1]}")

        if dvd_devices:
            print("DVD/CD-ROM Devices:")
            for device in dvd_devices:
                print(f"  {device[1]}")

        if not usb_devices and not dvd_devices:
            print("No removable devices found.")

    except Exception as e:
        print(f"Error listing devices: {e}")
        sys.exit(1)


def get_device_list():
    """Get device list for GUI consumption"""
    devices = []

    try:
        usb_devices = usb_drive(show_all=True)
        for device in usb_devices:
            # Parse device info to extract model and size
            device_info = device[1]
            if "(" in device_info and ")" in device_info:
                # Extract device path, model, and size from string like "/dev/sdb(SanDisk Ultra, 14.5G)"
                device_path = device[0]
                info_part = device_info[device_info.find("(")+1:device_info.find(")")]
                if ", " in info_part:
                    model, size = info_part.split(", ", 1)
                else:
                    model = info_part
                    size = "Unknown"

                devices.append({
                    'device': device_path,
                    'size': size,
                    'model': model,
                    'type': 'usb'
                })
            else:
                # Fallback for unexpected format
                devices.append({
                    'device': device[0],
                    'size': 'Unknown',
                    'model': device[1],
                    'type': 'usb'
                })
    except Exception as e:
        print(f"Error getting device list for GUI: {e}")

    return devices
