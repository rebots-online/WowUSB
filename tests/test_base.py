#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Base test class for WowUSB-DS9 tests.
This module provides common functionality for all test modules.
"""

import os
import sys
import unittest
import tempfile
import subprocess
import shutil
from unittest.mock import patch, MagicMock

# Add parent directory to path for importing WowUSB modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import WowUSB.core as core
import WowUSB.utils as utils
import WowUSB.workaround as workaround
import WowUSB.filesystem_handlers as fs_handlers

class WowUSBTestCase(unittest.TestCase):
    """Base test case for WowUSB-DS9 tests"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp(prefix="WowUSB_test.")
        self.source_dir = os.path.join(self.temp_dir, "source")
        self.target_dir = os.path.join(self.temp_dir, "target")
        
        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.target_dir, exist_ok=True)
        
        # Mock command execution
        self.command_patcher = patch('subprocess.run')
        self.mock_run = self.command_patcher.start()
        
        # Configure mock to return success by default
        self.mock_run.return_value.returncode = 0
        self.mock_run.return_value.stdout = b""
        self.mock_run.return_value.stderr = b""
        
        # Mock check_command to always return the command
        self.check_command_patcher = patch('WowUSB.utils.check_command', 
                                          return_value=True)
        self.mock_check_command = self.check_command_patcher.start()
    
    def tearDown(self):
        """Clean up test environment"""
        # Stop patchers
        self.command_patcher.stop()
        self.check_command_patcher.stop()
        
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def create_mock_windows_iso(self, version="10", has_large_files=False):
        """
        Create a mock Windows ISO structure
        
        Args:
            version (str): Windows version ("7", "8", "10", "11")
            has_large_files (bool): Whether to include large files
            
        Returns:
            str: Path to the mock ISO directory
        """
        # Create basic Windows directory structure
        sources_dir = os.path.join(self.source_dir, "sources")
        boot_dir = os.path.join(self.source_dir, "boot")
        efi_dir = os.path.join(self.source_dir, "efi", "boot")
        
        os.makedirs(sources_dir, exist_ok=True)
        os.makedirs(boot_dir, exist_ok=True)
        os.makedirs(efi_dir, exist_ok=True)
        
        # Create boot files
        with open(os.path.join(boot_dir, "bootmgr"), "w") as f:
            f.write("Mock bootmgr file")
            
        with open(os.path.join(efi_dir, "bootx64.efi"), "w") as f:
            f.write("Mock EFI boot file")
        
        # Create version-specific files
        if version in ["10", "11"]:
            # Create cversion.ini for Windows 10/11
            with open(os.path.join(sources_dir, "cversion.ini"), "w") as f:
                build = "19041" if version == "10" else "22000"
                f.write(f"""
[HostBuild]
MinClient=10.0
BuildNumber={build}
""")
                
            # Create Windows 11 specific file
            if version == "11":
                with open(os.path.join(sources_dir, "appraiserres.dll"), "w") as f:
                    f.write("Mock Windows 11 file")
        
        elif version == "8":
            # Create cversion.ini for Windows 8
            with open(os.path.join(sources_dir, "cversion.ini"), "w") as f:
                f.write("""
[HostBuild]
MinClient=6.2
BuildNumber=9200
""")
        
        elif version == "7":
            # Create cversion.ini for Windows 7
            with open(os.path.join(sources_dir, "cversion.ini"), "w") as f:
                f.write("""
[HostBuild]
MinClient=6.1
BuildNumber=7601
""")
        
        # Create install.wim file
        with open(os.path.join(sources_dir, "install.wim"), "w") as f:
            f.write("Mock Windows installation image")
        
        # Create large file if needed
        if has_large_files:
            large_file_path = os.path.join(sources_dir, "large_file.dat")
            
            # Create a sparse file of 5GB
            with open(large_file_path, 'wb') as f:
                f.seek(5 * 1024 * 1024 * 1024 - 1)  # 5GB - 1 byte
                f.write(b'\x00')  # Write a single byte at the end
        
        return self.source_dir
    
    def create_mock_device(self, device_type="usb"):
        """
        Create a mock device for testing
        
        Args:
            device_type (str): Device type ("usb", "hdd", "ssd")
            
        Returns:
            str: Path to the mock device
        """
        # Create a mock device path
        if device_type == "usb":
            return "/dev/sdX"
        elif device_type == "hdd":
            return "/dev/sdY"
        elif device_type == "ssd":
            return "/dev/nvme0n1"
        else:
            return "/dev/sdZ"
    
    def mock_filesystem_detection(self, has_large_files=False):
        """
        Mock filesystem detection
        
        Args:
            has_large_files (bool): Whether to simulate large files
            
        Returns:
            None
        """
        # Mock check_fat32_filesize_limitation
        self.fat32_check_patcher = patch('WowUSB.utils.check_fat32_filesize_limitation',
                                        return_value=has_large_files)
        self.mock_fat32_check = self.fat32_check_patcher.start()
        
        # Mock check_fat32_filesize_limitation_detailed
        self.fat32_check_detailed_patcher = patch('WowUSB.utils.check_fat32_filesize_limitation_detailed',
                                                return_value=(has_large_files, "large_file.dat", 5 * 1024 * 1024 * 1024))
        self.mock_fat32_check_detailed = self.fat32_check_detailed_patcher.start()
        
        # Add cleanup
        self.addCleanup(self.fat32_check_patcher.stop)
        self.addCleanup(self.fat32_check_detailed_patcher.stop)
    
    def mock_mount_operations(self):
        """
        Mock mount and unmount operations
        
        Returns:
            None
        """
        # Mock mount_source_filesystem
        self.mount_source_patcher = patch('WowUSB.core.mount_source_filesystem',
                                         return_value=0)
        self.mock_mount_source = self.mount_source_patcher.start()
        
        # Mock mount_target_filesystem
        self.mount_target_patcher = patch('WowUSB.core.mount_target_filesystem',
                                         return_value=0)
        self.mock_mount_target = self.mount_target_patcher.start()
        
        # Add cleanup
        self.addCleanup(self.mount_source_patcher.stop)
        self.addCleanup(self.mount_target_patcher.stop)
