
import os
import subprocess
import time

import WowUSB.utils as utils
import WowUSB.miscellaneous as miscellaneous

_ = miscellaneous.i18n

def make_system_realize_partition_table_changed(target_device):
    """
    :param target_device:
    :return:
    """
    utils.print_with_color(_("Making system realize that partition table has changed..."))

    subprocess.run(["blockdev", "--rereadpt", target_device])
    utils.print_with_color(_("Wait 3 seconds for block device nodes to populate..."))

    time.sleep(3)


def buggy_motherboards_that_ignore_disks_without_boot_flag_toggled(target_device):
    """
    Some buggy BIOSes won't put detected device with valid MBR
    but no partitions with boot flag toggled into the boot menu,
    workaround this by setting the first partition's boot flag
    (which partition doesn't matter as GNU GRUB doesn't depend on it anyway)

    :param target_device:
    :return:
    """
    utils.print_with_color(
        _("Applying workaround for buggy motherboards that will ignore disks with no partitions with the boot flag toggled")
    )

    subprocess.run(["parted", "--script",
                    target_device,
                    "set", "1", "boot", "on"])


def support_windows_7_uefi_boot(source_fs_mountpoint, target_fs_mountpoint):
    """
    As Windows 7's installation media doesn't place the required EFI
    bootloaders in the right location, we extract them from the
    system image manually

    :TODO: Create Windows 7 checking

    :param source_fs_mountpoint:
    :param target_fs_mountpoint:
    :return:
    """

    grep = subprocess.run(["grep", "--extended-regexp", "--quiet", r"^MinServer=7[0-9]{3}\\.[0-9]",
                           source_fs_mountpoint + "/sources/cversion.ini"],
                          stdout=subprocess.PIPE).stdout.decode("utf-8").strip()
    
    if grep == "" and not os.path.isfile(source_fs_mountpoint + "/bootmgr.efi"):
        return 0

    utils.print_with_color(
        _("Source media seems to be Windows 7-based with EFI support, applying workaround to make it support UEFI booting"),
        "yellow")

    test_efi_directory = subprocess.run(["find", target_fs_mountpoint, "-ipath", target_fs_mountpoint + "/efi"],
                                        stdout=subprocess.PIPE).stdout.decode("utf-8").strip()

    if test_efi_directory == "":
        efi_directory = target_fs_mountpoint + "/efi"
        if utils.verbose:
            utils.print_with_color(_("DEBUG: Can't find efi directory, use {0}").format(efi_directory), "yellow")
    else:
        efi_directory = test_efi_directory
        if utils.verbose:
            utils.print_with_color(_("DEBUG: {0} detected.").format(efi_directory), "yellow")

    test_efi_boot_directory = subprocess.run(["find", target_fs_mountpoint, "-ipath", target_fs_mountpoint + "/boot"],
                                             stdout=subprocess.PIPE).stdout.decode("utf-8").strip()


def bypass_windows11_tpm_requirement(target_fs_mountpoint):
    """
    Bypass Windows 11 TPM, Secure Boot, and RAM requirements for Windows-To-Go

    This function creates registry modifications that disable TPM, Secure Boot,
    and RAM checks during Windows 11 setup and boot.

    :param target_fs_mountpoint: Target filesystem mountpoint
    :return: 0 - success; 1 - failure
    """
    utils.print_with_color(
        _("Applying Windows 11 TPM, Secure Boot, and RAM requirement bypass for Windows-To-Go..."),
        "green"
    )

    # Create registry files directory if it doesn't exist
    registry_dir = os.path.join(target_fs_mountpoint, "Windows", "System32", "config")
    os.makedirs(registry_dir, exist_ok=True)

    # Create registry bypass file
    bypass_reg_path = os.path.join(target_fs_mountpoint, "bypass_requirements.reg")

    with open(bypass_reg_path, "w") as reg_file:
        reg_file.write("""Windows Registry Editor Version 5.00

; Bypass TPM 2.0 requirement
[HKEY_LOCAL_MACHINE\\SYSTEM\\Setup\\LabConfig]
"BypassTPMCheck"=dword:00000001
"BypassSecureBootCheck"=dword:00000001
"BypassRAMCheck"=dword:00000001

; Disable TPM check for Windows Update
[HKEY_LOCAL_MACHINE\\SYSTEM\\Setup\\MoSetup]
"AllowUpgradesWithUnsupportedTPMOrCPU"=dword:00000001

; Disable Secure Boot and TPM for Windows 11
[HKEY_LOCAL_MACHINE\\SYSTEM\\Setup\\Upgrade\\NSI\\{17AB7DB5-26E2-4542-B68E-F5D172C7CE2A}]
"UpgradeEligibility"=dword:00000001
""")

    # Create setup completion script to apply registry modifications
    setup_script_path = os.path.join(target_fs_mountpoint, "Windows", "Setup", "Scripts")
    os.makedirs(setup_script_path, exist_ok=True)

    with open(os.path.join(setup_script_path, "SetupComplete.cmd"), "w") as script_file:
        script_file.write("""@echo off
reg import %SystemDrive%\\bypass_requirements.reg
""")

    utils.print_with_color(_("Windows 11 requirement bypass applied successfully"), "green")
    return 0


def prepare_windows_portable_drivers(target_fs_mountpoint):
    """
    Prepare Windows for portable operation by configuring drivers and hardware detection

    This function creates registry modifications that improve hardware compatibility
    when booting on different computers.

    :param target_fs_mountpoint: Target filesystem mountpoint
    :return: 0 - success; 1 - failure
    """
    utils.print_with_color(_("Configuring Windows for portable operation..."), "green")

    # Create registry file for portable operation
    portable_reg_path = os.path.join(target_fs_mountpoint, "portable_config.reg")

    with open(portable_reg_path, "w") as reg_file:
        reg_file.write("""Windows Registry Editor Version 5.00

; Enable driver database for multiple hardware profiles
[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\PnP]
"DisableCrossSessionDriverLoad"=dword:00000000

; Enable all storage controllers
[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\storahci]
"Start"=dword:00000000

[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\stornvme]
"Start"=dword:00000000

[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\storport]
"Start"=dword:00000000

; Disable fast startup (causes issues with hardware changes)
[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Power]
"HiberbootEnabled"=dword:00000000

; Configure boot options for better hardware compatibility
[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management]
"DisablePagingExecutive"=dword:00000001

; Enable all network adapters
[HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters]
"DisableDynamicUpdate"=dword:00000000
""")

    # Update setup completion script to apply portable configuration
    setup_script_path = os.path.join(target_fs_mountpoint, "Windows", "Setup", "Scripts", "SetupComplete.cmd")

    with open(setup_script_path, "a") as script_file:
        script_file.write("""
reg import %SystemDrive%\\portable_config.reg

rem Enable all network adapters
powershell -Command "Get-NetAdapter | Enable-NetAdapter -Confirm:$false"

rem Optimize for portable operation
powershell -Command "Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Power' -Name 'HibernateEnabled' -Value 0"
""")

    utils.print_with_color(_("Portable Windows configuration applied successfully"), "green")
    return 0

    if test_efi_boot_directory == "":
        efi_boot_directory = target_fs_mountpoint + "/boot"
        if utils.verbose:
            utils.print_with_color(_("DEBUG: Can't find efi/boot directory, use {0}").format(efi_boot_directory), "yellow")
    else:
        efi_boot_directory = test_efi_boot_directory
        if utils.verbose:
            utils.print_with_color(_("DEBUG: {0} detected.").format(efi_boot_directory), "yellow")

    # If there's already an EFI bootloader existed, skip the workaround
    test_efi_bootloader = subprocess.run(
        ["find", target_fs_mountpoint, "-ipath", target_fs_mountpoint + "/efi/boot/boot*.efi"],
        stdout=subprocess.PIPE).stdout.decode("utf-8").strip()

    if test_efi_bootloader != "":
        utils.print_with_color(_("INFO: Detected existing EFI bootloader, workaround skipped."))
        return 0

    os.makedirs(efi_boot_directory, exist_ok=True)

    bootloader = subprocess.run(["7z",
                                 "e",
                                 "-so",
                                 source_fs_mountpoint + "/sources/install.wim",
                                 "Windows/Boot/EFI/bootmgfw.efi"], stdout=subprocess.PIPE).stdout

    with open(efi_boot_directory + "/bootx64.efi", "wb") as target_bootloader:
        target_bootloader.write(bootloader)

