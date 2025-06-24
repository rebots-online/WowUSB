#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Test script for WowUSB-DS9 filesystem handlers.
This script tests the filesystem handlers for different filesystem types.
"""

import os
import sys
import unittest
import tempfile
import subprocess
from unittest.mock import patch, MagicMock, call

# Add parent directory to path for importing WowUSB modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import WowUSB.filesystem_handlers as fs_handlers
from tests.test_base import WowUSBTestCase

class FilesystemHandlerTests(WowUSBTestCase):
    """Test cases for filesystem handlers"""
    
    def test_get_filesystem_handler(self):
        """Test get_filesystem_handler function"""
        # Test getting FAT filesystem handler
        handler = fs_handlers.get_filesystem_handler("FAT")
        self.assertEqual(handler.name(), "FAT32") # Corrected to FAT32
        self.assertFalse(handler.supports_file_size_greater_than_4gb())
        
        # Test getting NTFS filesystem handler
        handler = fs_handlers.get_filesystem_handler("NTFS")
        self.assertEqual(handler.name(), "NTFS")
        self.assertTrue(handler.supports_file_size_greater_than_4gb())
        
        # Test getting exFAT filesystem handler
        handler = fs_handlers.get_filesystem_handler("EXFAT")
        self.assertEqual(handler.name(), "exFAT")
        self.assertTrue(handler.supports_file_size_greater_than_4gb())
        
        # Test getting F2FS filesystem handler
        handler = fs_handlers.get_filesystem_handler("F2FS")
        self.assertEqual(handler.name(), "F2FS")
        self.assertTrue(handler.supports_file_size_greater_than_4gb())
        
        # Test getting BTRFS filesystem handler
        handler = fs_handlers.get_filesystem_handler("BTRFS")
        self.assertEqual(handler.name(), "BTRFS")
        self.assertTrue(handler.supports_file_size_greater_than_4gb())
        
        # Test invalid filesystem type
        with self.assertRaises(ValueError):
            fs_handlers.get_filesystem_handler("INVALID")
    
    def test_get_optimal_filesystem_for_iso(self):
        """Test get_optimal_filesystem_for_iso function"""
        # Create mock ISO with large files
        iso_path = self.create_mock_windows_iso(has_large_files=True)
        
        # Mock available filesystem handlers
        available_handlers = ["FAT", "NTFS", "EXFAT", "F2FS", "BTRFS"]
        
        with patch('WowUSB.filesystem_handlers.get_available_filesystem_handlers', 
                  return_value=available_handlers), \
             patch('WowUSB.utils.check_fat32_filesize_limitation', return_value=True):
            
            # Test optimal filesystem selection with large files
            # Should select exFAT (first in preference order)
            optimal_fs = fs_handlers.get_optimal_filesystem_for_iso(iso_path)
            self.assertEqual(optimal_fs, "EXFAT")
        
        # Test with no large files
        with patch('WowUSB.filesystem_handlers.get_available_filesystem_handlers', 
                  return_value=available_handlers), \
             patch('WowUSB.utils.check_fat32_filesize_limitation', return_value=False):
            
            # Should select FAT (most compatible)
            optimal_fs = fs_handlers.get_optimal_filesystem_for_iso(iso_path)
            self.assertEqual(optimal_fs, "FAT32") # Corrected to FAT32
        
        # Test with limited available filesystems
        # Ensure mock returns the proper handler names like "FAT32", "NTFS"
        with patch('WowUSB.filesystem_handlers.get_available_filesystem_handlers', 
                  return_value=["FAT32", "NTFS"]), \
             patch('WowUSB.utils.check_fat32_filesize_limitation', return_value=True): # This mock for check_fat32_filesize_limitation is probably not needed as get_optimal uses _detailed
            
            # Should select NTFS (only available that supports large files)
            optimal_fs = fs_handlers.get_optimal_filesystem_for_iso(iso_path)
            self.assertEqual(optimal_fs, "NTFS")
        
        # Test with only FAT available
        with patch('WowUSB.filesystem_handlers.get_available_filesystem_handlers', 
                  return_value=["FAT32"]), \
             patch('WowUSB.utils.check_fat32_filesize_limitation', return_value=True): # Same as above
            
            # Should select FAT32 despite large files (only option, core.py will error later)
            optimal_fs = fs_handlers.get_optimal_filesystem_for_iso(iso_path)
            self.assertEqual(optimal_fs, "FAT32") # Corrected to FAT32

class FatFilesystemHandlerTests(WowUSBTestCase):
    """Test cases for FAT filesystem handler"""
    
    def test_fat_format_partition(self):
        """Test FAT format_partition method"""
        # Get FAT filesystem handler
        handler = fs_handlers.FatFilesystemHandler
        
        # Test format_partition
        result = handler.format_partition("/dev/sdX1", "WOWUSB")
        self.assertEqual(result, 0)
        
        # Verify mkfs.fat was called with correct arguments
        # The first argument should be the path to mkdosfs, mocked by WowUSBTestCase.setUp
        # The actual command in FatFilesystemHandler adds "-v"
        self.mock_run.assert_called_with([
            '/usr/bin/mock_command_path', "-F", "32", "-n", "WOWUSB", "-v", "/dev/sdX1"
        ])
    
    def test_fat_check_dependencies(self):
        """Test FAT check_dependencies method"""
        # Get FAT filesystem handler
        handler = fs_handlers.FatFilesystemHandler
        
        # Test check_dependencies with all dependencies available
        with patch('WowUSB.utils.check_command', return_value='/usr/bin/mkdosfs'): # Return a path
            is_available, missing = handler.check_dependencies()
            self.assertTrue(is_available)
            self.assertEqual(len(missing), 0)
        
        # Test check_dependencies with missing dependencies
        with patch('WowUSB.utils.check_command', return_value=None): # Return None
            is_available, missing = handler.check_dependencies()
            self.assertFalse(is_available)
            self.assertGreater(len(missing), 0)

class NtfsFilesystemHandlerTests(WowUSBTestCase):
    """Test cases for NTFS filesystem handler"""
    
    def test_ntfs_format_partition(self):
        """Test NTFS format_partition method"""
        handler = fs_handlers.NtfsFilesystemHandler
        
        def check_command_side_effect(command_name):
            if command_name == "mkntfs":
                return "/usr/bin/mkntfs_mock"
            elif command_name == "ntfsfix":
                return "/usr/bin/ntfsfix_mock"
            elif command_name == "ntfsck":
                return "/usr/bin/ntfsck_mock" # Or None if you want to test fallback
            return None

        with patch('WowUSB.utils.check_command', side_effect=check_command_side_effect) as mock_chk_cmd:
            # Test format_partition
            result = handler.format_partition("/dev/sdX1", "WOWUSB")
            self.assertEqual(result, 0)
            # Check that mkntfs was called by format_partition
            # and ntfsfix/ntfsck by the validate_filesystem call within format_partition
            expected_calls = [call("mkntfs")]
            # validate_filesystem tries ntfsfix then ntfsck if first is None
            # if ntfsfix_mock is returned, ntfsck won't be called by the 'or'
            expected_calls.append(call("ntfsfix"))
            # If you want to test the ntfsck fallback, make ntfsfix return None in side_effect
            # expected_calls.append(call("ntfsck"))

            mock_chk_cmd.assert_has_calls(expected_calls, any_order=False) # Check specific calls
            self.mock_run.assert_called() # Verify subprocess.run was called (by mkntfs and ntfsfix/ntfsck)

            # Test format_partition with device type detection (rotational)
            mock_chk_cmd.reset_mock() # Reset check_command mock for new set of calls
            self.mock_run.reset_mock() # Reset subprocess.run mock
            with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="1\n")))))), \
                 patch('os.path.basename', return_value="sdX"):
                result = handler.format_partition("/dev/sdX1", "WOWUSB_HDD")
                self.assertEqual(result, 0)
                # Check that mkntfs was called, and potentially with HDD specific args if any were asserted
                self.mock_run.assert_called()

            # Test format_partition with device type detection (non-rotational)
            self.mock_run.reset_mock() # Reset subprocess.run mock
            with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="0\n")))))), \
                 patch('os.path.basename', return_value="sdX"):
                result = handler.format_partition("/dev/sdX1", "WOWUSB_SSD")
                self.assertEqual(result, 0)
                self.mock_run.assert_called()

    def test_ntfs_validate_filesystem(self):
        """Test NTFS validate_filesystem method"""
        # Get NTFS filesystem handler
        handler = fs_handlers.NtfsFilesystemHandler
        
        # Mock subprocess.run for filesystem check
        self.mock_run.return_value.returncode = 0
        
        # Test validate_filesystem
        with patch('tempfile.TemporaryDirectory', return_value=MagicMock()), \
             patch('os.path.getsize', return_value=5 * 1024 * 1024 * 1024), \
             patch('builtins.open', MagicMock()):
            result = handler.validate_filesystem("/dev/sdX1")
            self.assertTrue(result)
    
    def test_ntfs_needs_uefi_support_partition(self):
        """Test NTFS needs_uefi_support_partition method"""
        # Get NTFS filesystem handler
        handler = fs_handlers.NtfsFilesystemHandler
        
        # Test needs_uefi_support_partition
        self.assertTrue(handler.needs_uefi_support_partition())

class ExfatFilesystemHandlerTests(WowUSBTestCase):
    """Test cases for exFAT filesystem handler"""
    
    def test_exfat_format_partition(self):
        """Test exFAT format_partition method"""
        # Get exFAT filesystem handler
        handler = fs_handlers.ExfatFilesystemHandler
        
        # Test format_partition
        result = handler.format_partition("/dev/sdX1", "WOWUSB")
        self.assertEqual(result, 0)
        
        # Verify mkexfatfs/mkfs.exfat was called
        self.mock_run.assert_called()
        
        # Test format_partition with device type detection
        with patch('builtins.open', MagicMock()), \
             patch('os.path.basename', return_value="sdX"):
            result = handler.format_partition("/dev/sdX1", "WOWUSB")
            self.assertEqual(result, 0)
    
    def test_exfat_validate_filesystem(self):
        """Test exFAT validate_filesystem method"""
        # Get exFAT filesystem handler
        handler = fs_handlers.ExfatFilesystemHandler
        
        # Mock subprocess.run for filesystem check
        self.mock_run.return_value.returncode = 0
        
        # Test validate_filesystem
        with patch('tempfile.TemporaryDirectory', return_value=MagicMock()), \
             patch('os.path.getsize', return_value=5 * 1024 * 1024 * 1024), \
             patch('builtins.open', MagicMock()):
            result = handler.validate_filesystem("/dev/sdX1")
            self.assertTrue(result)
    
    def test_exfat_needs_uefi_support_partition(self):
        """Test exFAT needs_uefi_support_partition method"""
        # Get exFAT filesystem handler
        handler = fs_handlers.ExfatFilesystemHandler
        
        # Test needs_uefi_support_partition
        self.assertTrue(handler.needs_uefi_support_partition())
    
    def test_exfat_check_dependencies(self):
        """Test exFAT check_dependencies method"""
        # Get exFAT filesystem handler
        handler = fs_handlers.ExfatFilesystemHandler
        
        # Test check_dependencies with all dependencies available
        # Mock check_command to return a path for each tool exFAT handler checks
        def mock_check_exfat_tools(command_name):
            if command_name in ['mkexfatfs', 'mkfs.exfat', 'fsck.exfat', 'exfatlabel']:
                return f'/usr/bin/{command_name}'
            return None

        with patch('WowUSB.utils.check_command', side_effect=mock_check_exfat_tools), \
             patch('subprocess.run') as mock_subproc_run:
            # Ensure subprocess.run for version check returns a valid version string
            mock_subproc_run.return_value = MagicMock(stdout="version 1.3.0", returncode=0) # Adjusted for exFAT version check
            is_available, missing = handler.check_dependencies()
            self.assertTrue(is_available, f"Missing exFAT dependencies: {missing}")
            self.assertEqual(len(missing), 0)
        
        # Test check_dependencies with missing dependencies
        with patch('WowUSB.utils.check_command', return_value=None): # All commands missing
            is_available, missing = handler.check_dependencies()
            self.assertFalse(is_available)
            self.assertGreater(len(missing), 0)

class F2fsFilesystemHandlerTests(WowUSBTestCase):
    """Test cases for F2FS filesystem handler"""
    
    def test_f2fs_format_partition(self):
        """Test F2FS format_partition method"""
        handler = fs_handlers.F2fsFilesystemHandler
        
        with patch('WowUSB.utils.check_command', return_value='/usr/bin/mkfs.f2fs_mock') as mock_chk_cmd:
            result = handler.format_partition("/dev/sdX1", "WOWUSB")
            self.assertEqual(result, 0)
            mock_chk_cmd.assert_called_with("mkfs.f2fs")
            self.mock_run.assert_called() # Check that subprocess.run was called
    
    def test_f2fs_needs_uefi_support_partition(self):
        """Test F2FS needs_uefi_support_partition method"""
        # Get F2FS filesystem handler
        handler = fs_handlers.F2fsFilesystemHandler
        
        # Test needs_uefi_support_partition
        self.assertTrue(handler.needs_uefi_support_partition())

class BtrfsFilesystemHandlerTests(WowUSBTestCase):
    """Test cases for BTRFS filesystem handler"""
    
    def test_btrfs_format_partition(self):
        """Test BTRFS format_partition method"""
        handler = fs_handlers.BtrfsFilesystemHandler
        
        with patch('WowUSB.utils.check_command', return_value='/usr/bin/mkfs.btrfs_mock') as mock_chk_cmd:
            result = handler.format_partition("/dev/sdX1", "WOWUSB")
            self.assertEqual(result, 0)
            mock_chk_cmd.assert_called_with("mkfs.btrfs")
            self.mock_run.assert_called()
    
    def test_btrfs_needs_uefi_support_partition(self):
        """Test BTRFS needs_uefi_support_partition method"""
        # Get BTRFS filesystem handler
        handler = fs_handlers.BtrfsFilesystemHandler
        
        # Test needs_uefi_support_partition
        self.assertTrue(handler.needs_uefi_support_partition())

if __name__ == "__main__":
    unittest.main()
