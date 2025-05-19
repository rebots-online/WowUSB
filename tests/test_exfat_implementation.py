#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Test script for WowUSB-DS9 exFAT implementation.
This script tests the exFAT filesystem handler implementation.
"""

import os
import sys
import unittest
import tempfile
import subprocess
from unittest.mock import patch, MagicMock

# Add parent directory to path for importing WowUSB modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import WowUSB.filesystem_handlers as fs_handlers
import WowUSB.utils as utils

class ExfatImplementationTests(unittest.TestCase):
    """Test cases for exFAT implementation"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="WowUSB_test.")
        
        # Mock subprocess.run
        self.patcher = patch('subprocess.run')
        self.mock_run = self.patcher.start()
        self.mock_run.return_value.returncode = 0
        self.mock_run.return_value.stdout = b""
        self.mock_run.return_value.stderr = b""
        
        # Mock check_command
        self.check_command_patcher = patch('WowUSB.utils.check_command')
        self.mock_check_command = self.check_command_patcher.start()
        self.mock_check_command.return_value = True
    
    def tearDown(self):
        """Clean up test environment"""
        # Stop patchers
        self.patcher.stop()
        self.check_command_patcher.stop()
        
        # Remove temporary directory
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_exfat_handler_initialization(self):
        """Test exFAT handler initialization"""
        # Get exFAT handler
        handler = fs_handlers.ExfatFilesystemHandler
        
        # Check handler properties
        self.assertEqual(handler.name(), "exFAT")
        self.assertTrue(handler.supports_file_size_greater_than_4gb())
        self.assertEqual(handler.parted_fs_type(), "fat32")  # parted doesn't directly support exfat
        self.assertTrue(handler.needs_uefi_support_partition())
    
    def test_exfat_format_partition_hdd(self):
        """Test exFAT format_partition method for HDD"""
        # Get exFAT handler
        handler = fs_handlers.ExfatFilesystemHandler
        
        # Mock device type detection for HDD
        with patch('builtins.open', MagicMock()) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = "1\n"  # 1 = rotational (HDD)
            mock_open.return_value = mock_file
            
            # Format partition
            result = handler.format_partition("/dev/sdX1", "WOWUSB")
            
            # Check result
            self.assertEqual(result, 0)
            
            # Check if mkexfatfs was called with correct arguments for HDD
            self.mock_run.assert_called()
            args = self.mock_run.call_args[0][0]
            self.assertIn("--cluster-size=32K", args)  # HDD optimization
    
    def test_exfat_format_partition_ssd(self):
        """Test exFAT format_partition method for SSD"""
        # Get exFAT handler
        handler = fs_handlers.ExfatFilesystemHandler
        
        # Mock device type detection for SSD
        with patch('builtins.open', MagicMock()) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = "0\n"  # 0 = non-rotational (SSD)
            mock_open.return_value = mock_file
            
            # Format partition
            result = handler.format_partition("/dev/sdX1", "WOWUSB")
            
            # Check result
            self.assertEqual(result, 0)
            
            # Check if mkexfatfs was called with correct arguments for SSD
            self.mock_run.assert_called()
            args = self.mock_run.call_args[0][0]
            self.assertIn("--cluster-size=128K", args)  # SSD optimization
            self.assertIn("--alignment=1M", args)  # SSD optimization
    
    def test_exfat_format_partition_usb_flash(self):
        """Test exFAT format_partition method for USB flash drive"""
        # Get exFAT handler
        handler = fs_handlers.ExfatFilesystemHandler
        
        # Mock device type detection for USB flash drive
        with patch('builtins.open', MagicMock()) as mock_open:
            # First call for rotational check
            mock_file1 = MagicMock()
            mock_file1.__enter__.return_value.read.return_value = "0\n"  # 0 = non-rotational
            # Second call for removable check
            mock_file2 = MagicMock()
            mock_file2.__enter__.return_value.read.return_value = "1\n"  # 1 = removable
            
            mock_open.side_effect = [mock_file1, mock_file2]
            
            # Format partition
            result = handler.format_partition("/dev/sdX1", "WOWUSB")
            
            # Check result
            self.assertEqual(result, 0)
            
            # Check if mkexfatfs was called with correct arguments for USB flash
            self.mock_run.assert_called()
            args = self.mock_run.call_args[0][0]
            self.assertIn("--cluster-size=128K", args)  # Flash optimization
            self.assertIn("--alignment=1M", args)  # Flash optimization
            self.assertIn("--quick-format", args)  # Flash optimization
    
    def test_exfat_validate_filesystem(self):
        """Test exFAT validate_filesystem method"""
        # Get exFAT handler
        handler = fs_handlers.ExfatFilesystemHandler
        
        # Mock filesystem check
        self.mock_check_command.return_value = "fsck.exfat"
        
        # Mock mount/umount operations
        with patch('tempfile.TemporaryDirectory') as mock_temp_dir, \
             patch('os.path.getsize') as mock_getsize, \
             patch('builtins.open', MagicMock()):
            
            # Set up mocks
            mock_temp_dir.return_value.__enter__.return_value = self.temp_dir
            mock_getsize.return_value = 5 * 1024 * 1024 * 1024  # 5GB
            
            # Validate filesystem
            result = handler.validate_filesystem("/dev/sdX1")
            
            # Check result
            self.assertTrue(result)
            
            # Check if fsck.exfat was called
            self.mock_run.assert_called()
    
    def test_exfat_check_dependencies(self):
        """Test exFAT check_dependencies method"""
        # Get exFAT handler
        handler = fs_handlers.ExfatFilesystemHandler
        
        # Mock version check
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "mkfs.exfat 1.3.0"
            mock_run.return_value = mock_result
            
            # Check dependencies
            is_available, missing = handler.check_dependencies()
            
            # Check result
            self.assertTrue(is_available)
            self.assertEqual(len(missing), 0)
    
    def test_exfat_get_uefi_bootloader_file(self):
        """Test exFAT get_uefi_bootloader_file method"""
        # Get exFAT handler
        handler = fs_handlers.ExfatFilesystemHandler
        
        # Get UEFI bootloader file
        url, filename = handler.get_uefi_bootloader_file()
        
        # Check result
        self.assertTrue(url.endswith("uefi-ntfs.img"))
        self.assertEqual(filename, "uefi-ntfs.img")
    
    def test_exfat_create_uefi_support_partition(self):
        """Test exFAT create_uefi_support_partition method"""
        # Get exFAT handler
        handler = fs_handlers.ExfatFilesystemHandler
        
        # Create UEFI support partition
        result = handler.create_uefi_support_partition("/dev/sdX")
        
        # Check result
        self.assertTrue(result)
        
        # Check if parted was called with correct arguments
        self.mock_run.assert_called_with([
            "parted", "--align", "none",  # Small partition, alignment not critical
            "--script",
            "/dev/sdX",
            "mkpart",
            "primary",
            "fat16",  # FAT16 for compatibility
            "--", "-2048s", "-1s"  # Last 1MB for boot support
        ])

if __name__ == "__main__":
    unittest.main()
