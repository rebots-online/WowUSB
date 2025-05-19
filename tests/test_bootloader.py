#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Test script for WowUSB-DS9 bootloader functionality.
This script tests the bootloader module and UEFI:NTFS integration.
"""

import os
import sys
import tempfile
import unittest

# Add parent directory to path for importing WowUSB modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import WowUSB.bootloader as bootloader
from WowUSB.data.bootloaders import get_bootloader_path

class BootloaderTests(unittest.TestCase):
    """Test cases for bootloader functionality"""
    
    def test_bootloader_info(self):
        """Test bootloader information"""
        self.assertIn("uefi-ntfs.img", bootloader.BOOTLOADER_INFO)
        self.assertIn("url", bootloader.BOOTLOADER_INFO["uefi-ntfs.img"])
        self.assertIn("sha256", bootloader.BOOTLOADER_INFO["uefi-ntfs.img"])
        
    def test_bundled_bootloader_path(self):
        """Test bundled bootloader path"""
        path = get_bootloader_path("uefi-ntfs.img")
        self.assertTrue(os.path.exists(path), "Bundled bootloader not found")
        
    def test_bootloader_verification(self):
        """Test bootloader verification"""
        path = get_bootloader_path("uefi-ntfs.img")
        self.assertTrue(bootloader.verify_bootloader(path), "Bootloader verification failed")
        
    def test_get_bootloader(self):
        """Test get_bootloader function"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = bootloader.get_bootloader("uefi-ntfs.img", temp_dir)
            self.assertIsNotNone(path, "Failed to get bootloader")
            self.assertTrue(os.path.exists(path), "Bootloader file not found")
            
    def test_bootloader_download_fallback(self):
        """Test bootloader download fallback"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a corrupted bootloader file
            bundled_path = get_bootloader_path("uefi-ntfs.img")
            corrupted_path = os.path.join(temp_dir, "uefi-ntfs.img")
            
            # Create a corrupted copy
            with open(bundled_path, "rb") as src, open(corrupted_path, "wb") as dst:
                data = src.read()
                # Corrupt the data
                if len(data) > 100:
                    data = data[:50] + b'\x00' * 10 + data[60:]
                dst.write(data)
                
            # Verify the file is corrupted
            self.assertFalse(bootloader.verify_bootloader(corrupted_path), 
                            "Corrupted bootloader should fail verification")
            
            # Test download fallback
            download_dir = os.path.join(temp_dir, "download")
            os.makedirs(download_dir, exist_ok=True)
            
            # Temporarily replace the bundled path with the corrupted one
            original_get_path = bootloader.get_bootloader_path
            bootloader.get_bootloader_path = lambda x: corrupted_path
            
            try:
                path = bootloader.get_bootloader("uefi-ntfs.img", download_dir)
                self.assertIsNotNone(path, "Failed to get bootloader with fallback")
                self.assertTrue(os.path.exists(path), "Downloaded bootloader file not found")
                self.assertTrue(bootloader.verify_bootloader(path), 
                               "Downloaded bootloader should pass verification")
            finally:
                # Restore the original function
                bootloader.get_bootloader_path = original_get_path

if __name__ == "__main__":
    unittest.main()
