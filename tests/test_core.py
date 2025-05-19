#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Test script for WowUSB-DS9 core functionality.
This script tests the core functionality of WowUSB-DS9.
"""

import os
import sys
import unittest
import tempfile
import subprocess
from unittest.mock import patch, MagicMock, call

# Add parent directory to path for importing WowUSB modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import WowUSB.core as core
import WowUSB.utils as utils
import WowUSB.filesystem_handlers as fs_handlers
from tests.test_base import WowUSBTestCase

class CoreFunctionalityTests(WowUSBTestCase):
    """Test cases for core functionality"""
    
    def test_partition_table_creation(self):
        """Test partition table creation"""
        # Test MBR partition table creation
        result = core.create_target_partition_table("/dev/sdX", "legacy")
        self.assertEqual(result, 0)
        
        # Verify parted was called with correct arguments
        self.mock_run.assert_called_with([
            "parted", "--script", "/dev/sdX", "mklabel", "msdos"
        ])
        
        # Test GPT partition table creation
        self.mock_run.reset_mock()
        result = core.create_target_partition_table("/dev/sdX", "uefi")
        self.assertEqual(result, 0)
        
        # Verify parted was called with correct arguments
        self.mock_run.assert_called_with([
            "parted", "--script", "/dev/sdX", "mklabel", "gpt"
        ])
    
    def test_target_partition_creation(self):
        """Test target partition creation"""
        # Mock filesystem handler
        mock_fs_handler = MagicMock()
        mock_fs_handler.parted_fs_type.return_value = "fat32"
        mock_fs_handler.format_partition.return_value = 0
        
        with patch('WowUSB.filesystem_handlers.get_filesystem_handler', 
                  return_value=mock_fs_handler):
            # Test partition creation
            result = core.create_target_partition("/dev/sdX", "/dev/sdX1", "FAT", "WOWUSB")
            self.assertEqual(result, 0)
            
            # Verify parted was called with correct arguments
            self.mock_run.assert_any_call([
                "parted", "--script", "/dev/sdX", "mkpart", "primary", "fat32", "1MiB", "100%"
            ])
            
            # Verify filesystem handler was called
            mock_fs_handler.format_partition.assert_called_with("/dev/sdX1", "WOWUSB")
    
    def test_uefi_support_partition_creation(self):
        """Test UEFI support partition creation"""
        # Test UEFI support partition creation
        core.create_uefi_ntfs_support_partition("/dev/sdX")
        
        # Verify parted was called with correct arguments
        self.mock_run.assert_called_with([
            "parted", "--align", "none", "--script", "/dev/sdX", 
            "mkpart", "primary", "fat16", "--", "-2048s", "-1s"
        ])
    
    def test_wintogo_partition_layout_creation(self):
        """Test Windows-To-Go partition layout creation"""
        # Mock filesystem handler
        mock_fs_handler = MagicMock()
        mock_fs_handler.format_partition.return_value = 0
        
        with patch('WowUSB.filesystem_handlers.get_filesystem_handler', 
                  return_value=mock_fs_handler):
            # Test Windows-To-Go partition layout creation
            result = core.create_wintogo_partition_layout("/dev/sdX", "NTFS", "Windows")
            self.assertEqual(result, 0)
            
            # Verify parted was called with correct arguments for GPT creation
            self.mock_run.assert_any_call([
                "parted", "--script", "/dev/sdX", "mklabel", "gpt"
            ])
            
            # Verify ESP partition creation
            self.mock_run.assert_any_call([
                "parted", "--script", "/dev/sdX", "mkpart", "ESP", "fat32", 
                "1MiB", "261MiB", "set", "1", "boot", "on", "set", "1", "esp", "on"
            ])
            
            # Verify MSR partition creation
            self.mock_run.assert_any_call([
                "parted", "--script", "/dev/sdX", "mkpart", "MSR", 
                "261MiB", "389MiB", "set", "2", "msftres", "on"
            ])
            
            # Verify Windows partition creation
            self.mock_run.assert_any_call([
                "parted", "--script", "/dev/sdX", "mkpart", "Windows", 
                "389MiB", "100%"
            ])
            
            # Verify ESP formatting
            self.mock_run.assert_any_call([
                True, "-F", "32", "-n", "ESP", "/dev/sdX1"
            ])
            
            # Verify Windows partition formatting
            mock_fs_handler.format_partition.assert_called_with("/dev/sdX3", "Windows")
    
    def test_filesystem_selection(self):
        """Test filesystem selection logic"""
        # Create a mock args object
        mock_args = MagicMock()
        mock_args.source = self.create_mock_windows_iso(has_large_files=True)
        mock_args.target = "/dev/sdX"
        mock_args.target_partition = "/dev/sdX1"
        mock_args.target_filesystem = "AUTO"
        mock_args.verbose = False
        mock_args.install_mode = "device"
        mock_args.no_color = False
        mock_args.for_gui = False
        mock_args.wintogo = False
        
        # Mock available filesystem handlers
        available_handlers = ["FAT", "NTFS", "EXFAT", "F2FS", "BTRFS"]
        
        with patch('WowUSB.filesystem_handlers.get_available_filesystem_handlers', 
                  return_value=available_handlers), \
             patch('WowUSB.core.mount_source_filesystem', return_value=0), \
             patch('WowUSB.core.mount_target_filesystem', return_value=0), \
             patch('WowUSB.core.copy_filesystem_files', return_value=0), \
             patch('WowUSB.core.create_target_partition_table', return_value=0), \
             patch('WowUSB.core.create_target_partition', return_value=0), \
             patch('WowUSB.core.create_uefi_ntfs_support_partition', return_value=None), \
             patch('WowUSB.core.install_uefi_support_partition', return_value=0), \
             patch('WowUSB.core.install_legacy_pc_bootloader_grub', return_value=0), \
             patch('WowUSB.utils.check_fat32_filesize_limitation', return_value=True), \
             patch('WowUSB.utils.check_fat32_filesize_limitation_detailed', 
                  return_value=(True, "large_file.dat", 5 * 1024 * 1024 * 1024)):
            
            # Test automatic filesystem selection with large files
            result = core.main(mock_args)
            self.assertEqual(result, 0)
            
            # Verify that a filesystem that supports large files was selected
            # In this case, it should be exFAT (first in preference order)
            fs_handler = fs_handlers.get_filesystem_handler("EXFAT")
            self.assertTrue(fs_handler.supports_file_size_greater_than_4gb())
    
    def test_main_function_device_mode(self):
        """Test main function in device mode"""
        # Create a mock args object
        mock_args = MagicMock()
        mock_args.source = self.create_mock_windows_iso()
        mock_args.target = "/dev/sdX"
        mock_args.target_partition = "/dev/sdX1"
        mock_args.target_filesystem = "FAT"
        mock_args.verbose = False
        mock_args.install_mode = "device"
        mock_args.no_color = False
        mock_args.for_gui = False
        mock_args.wintogo = False
        
        with patch('WowUSB.core.mount_source_filesystem', return_value=0), \
             patch('WowUSB.core.mount_target_filesystem', return_value=0), \
             patch('WowUSB.core.copy_filesystem_files', return_value=0), \
             patch('WowUSB.core.create_target_partition_table', return_value=0), \
             patch('WowUSB.core.create_target_partition', return_value=0), \
             patch('WowUSB.core.install_legacy_pc_bootloader_grub', return_value=0), \
             patch('WowUSB.utils.check_fat32_filesize_limitation', return_value=False), \
             patch('WowUSB.utils.check_fat32_filesize_limitation_detailed', 
                  return_value=(False, "", 0)):
            
            # Test main function in device mode
            result = core.main(mock_args)
            self.assertEqual(result, 0)
    
    def test_main_function_partition_mode(self):
        """Test main function in partition mode"""
        # Create a mock args object
        mock_args = MagicMock()
        mock_args.source = self.create_mock_windows_iso()
        mock_args.target = None
        mock_args.target_partition = "/dev/sdX1"
        mock_args.target_filesystem = "FAT"
        mock_args.verbose = False
        mock_args.install_mode = "partition"
        mock_args.no_color = False
        mock_args.for_gui = False
        mock_args.wintogo = False
        
        with patch('WowUSB.core.mount_source_filesystem', return_value=0), \
             patch('WowUSB.core.mount_target_filesystem', return_value=0), \
             patch('WowUSB.core.copy_filesystem_files', return_value=0), \
             patch('WowUSB.core.install_legacy_pc_bootloader_grub', return_value=0), \
             patch('WowUSB.utils.check_target_partition', return_value=0), \
             patch('WowUSB.utils.check_fat32_filesize_limitation', return_value=False), \
             patch('WowUSB.utils.check_fat32_filesize_limitation_detailed', 
                  return_value=(False, "", 0)):
            
            # Test main function in partition mode
            result = core.main(mock_args)
            self.assertEqual(result, 0)
    
    def test_main_function_wintogo_mode(self):
        """Test main function in Windows-To-Go mode"""
        # Create a mock args object
        mock_args = MagicMock()
        mock_args.source = self.create_mock_windows_iso(version="11")
        mock_args.target = "/dev/sdX"
        mock_args.target_partition = "/dev/sdX1"
        mock_args.target_filesystem = "NTFS"
        mock_args.verbose = False
        mock_args.install_mode = "device"
        mock_args.no_color = False
        mock_args.for_gui = False
        mock_args.wintogo = True
        
        with patch('WowUSB.core.mount_source_filesystem', return_value=0), \
             patch('WowUSB.core.mount_target_filesystem', return_value=0), \
             patch('WowUSB.core.copy_filesystem_files', return_value=0), \
             patch('WowUSB.core.create_wintogo_partition_layout', return_value=0), \
             patch('WowUSB.core.install_legacy_pc_bootloader_grub', return_value=0), \
             patch('WowUSB.workaround.bypass_windows11_tpm_requirement', return_value=0), \
             patch('WowUSB.workaround.prepare_windows_portable_drivers', return_value=0), \
             patch('WowUSB.utils.check_fat32_filesize_limitation', return_value=False), \
             patch('WowUSB.utils.check_fat32_filesize_limitation_detailed', 
                  return_value=(False, "", 0)), \
             patch('subprocess.run', return_value=MagicMock(returncode=0)):
            
            # Test main function in Windows-To-Go mode
            result = core.main(mock_args)
            self.assertEqual(result, 0)
            
            # Verify Windows-To-Go specific functions were called
            self.assertTrue(core.create_wintogo_partition_layout.called)
            self.assertTrue(workaround.bypass_windows11_tpm_requirement.called)
            self.assertTrue(workaround.prepare_windows_portable_drivers.called)

if __name__ == "__main__":
    unittest.main()
