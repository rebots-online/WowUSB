#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Bootloader handling module for WowUSB-DS9.
This module provides functions for managing bootloaders for different filesystem types.
"""

import os
import hashlib
import urllib.request
import urllib.error
import tempfile
import shutil
import subprocess

import WowUSB.utils as utils
import WowUSB.miscellaneous as miscellaneous
from WowUSB.data.bootloaders import get_bootloader_path

_ = miscellaneous.i18n

# Bootloader information with URLs and SHA256 checksums for verification
BOOTLOADER_INFO = {
    "uefi-ntfs.img": {
        "url": "https://github.com/pbatard/rufus/raw/master/res/uefi/uefi-ntfs.img",
        "sha256": "70a0b56c3fe1aba5a14de87e13b7b947f205b4e1cb61ca1e7e95a78f89a9c315",
        "description": "UEFI:NTFS bootloader for NTFS/exFAT support"
    }
}

def verify_bootloader(bootloader_path, expected_sha256=None):
    """
    Verify the integrity of a bootloader file using SHA256 checksum
    
    Args:
        bootloader_path (str): Path to the bootloader file
        expected_sha256 (str, optional): Expected SHA256 checksum
            If None, the checksum from BOOTLOADER_INFO will be used
            
    Returns:
        bool: True if verification passes, False otherwise
    """
    if not os.path.exists(bootloader_path):
        return False
        
    # Get filename from path
    filename = os.path.basename(bootloader_path)
    
    # Get expected checksum
    if expected_sha256 is None:
        if filename not in BOOTLOADER_INFO:
            return False
        expected_sha256 = BOOTLOADER_INFO[filename]["sha256"]
    
    # Calculate SHA256 checksum
    sha256_hash = hashlib.sha256()
    with open(bootloader_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    actual_sha256 = sha256_hash.hexdigest()
    
    # Compare checksums
    return actual_sha256 == expected_sha256

def download_bootloader(filename, target_path):
    """
    Download a bootloader file from the internet
    
    Args:
        filename (str): Bootloader filename
        target_path (str): Path to save the downloaded file
        
    Returns:
        bool: True if download succeeds, False otherwise
    """
    if filename not in BOOTLOADER_INFO:
        utils.print_with_color(_("Error: Unknown bootloader: {0}").format(filename), "red")
        return False
        
    url = BOOTLOADER_INFO[filename]["url"]
    
    utils.print_with_color(_("Downloading {0} bootloader...").format(filename), "green")
    
    try:
        # Download to a temporary file first
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            
        urllib.request.urlretrieve(url, temp_path)
        
        # Verify the downloaded file
        if not verify_bootloader(temp_path, BOOTLOADER_INFO[filename]["sha256"]):
            utils.print_with_color(_("Error: Downloaded bootloader verification failed"), "red")
            os.unlink(temp_path)
            return False
            
        # Move to target path
        shutil.move(temp_path, target_path)
        return True
        
    except (urllib.error.ContentTooShortError, urllib.error.HTTPError, urllib.error.URLError) as e:
        utils.print_with_color(_("Error: Failed to download bootloader: {0}").format(str(e)), "red")
        return False
    except Exception as e:
        utils.print_with_color(_("Error: Unexpected error during bootloader download: {0}").format(str(e)), "red")
        return False

def get_bootloader(filename, download_dir=None):
    """
    Get a bootloader file, using bundled version if available,
    or downloading if necessary
    
    Args:
        filename (str): Bootloader filename
        download_dir (str, optional): Directory to save downloaded bootloader
            If None, a temporary directory will be used
            
    Returns:
        str: Path to the bootloader file, or None if not available
    """
    # Try to use bundled bootloader first
    bundled_path = get_bootloader_path(filename)
    
    if os.path.exists(bundled_path) and verify_bootloader(bundled_path):
        utils.print_with_color(_("Using bundled {0} bootloader").format(filename), "green")
        return bundled_path
        
    # If bundled bootloader is not available or corrupted, download it
    utils.print_with_color(
        _("Bundled bootloader not found or corrupted, attempting to download..."), 
        "yellow"
    )
    
    # Create temporary directory if download_dir is not provided
    if download_dir is None:
        download_dir = tempfile.mkdtemp(prefix="WowUSB.")
        
    # Download bootloader
    target_path = os.path.join(download_dir, filename)
    if download_bootloader(filename, target_path):
        return target_path
        
    return None

def install_uefi_bootloader(fs_handler, target_partition, download_dir):
    """
    Install UEFI bootloader for a filesystem that requires it
    
    Args:
        fs_handler: Filesystem handler instance
        target_partition (str): Target partition device path (e.g., /dev/sdX2)
        download_dir (str): Directory for temporary downloads
        
    Returns:
        bool: True if installation succeeds, False otherwise
    """
    utils.check_kill_signal()
    
    # Get bootloader filename from filesystem handler
    bootloader_filename = os.path.basename(fs_handler.get_uefi_bootloader_file()[1])
    
    # Get bootloader file (bundled or downloaded)
    bootloader_path = get_bootloader(bootloader_filename, download_dir)
    
    if not bootloader_path:
        utils.print_with_color(
            _("Warning: Unable to get UEFI bootloader. Target device might not be bootable if UEFI firmware doesn't support filesystem."),
            "yellow"
        )
        return False
        
    # Install bootloader to partition
    utils.print_with_color(_("Installing UEFI bootloader to {0}...").format(target_partition), "green")
    
    try:
        # Use dd to write bootloader image to partition
        result = subprocess.run(
            ["dd", "if=" + bootloader_path, "of=" + target_partition, "bs=1M"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            utils.print_with_color(_("Error: Failed to install bootloader: {0}").format(result.stderr), "red")
            return False
            
        return True
        
    except subprocess.SubprocessError as e:
        utils.print_with_color(_("Error: Bootloader installation failed: {0}").format(str(e)), "red")
        return False
