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
from unittest.mock import patch, MagicMock # Added patch and MagicMock

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
        
    @patch('WowUSB.bootloader.verify_bootloader', return_value=True)
    def test_get_bootloader(self, mock_verify):
        """Test get_bootloader function"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Ensure the dummy bundled file exists for get_bootloader_path to succeed initially
            dummy_bundled_path = get_bootloader_path("uefi-ntfs.img")
            if not os.path.exists(os.path.dirname(dummy_bundled_path)):
                os.makedirs(os.path.dirname(dummy_bundled_path))
            if not os.path.exists(dummy_bundled_path):
                 with open(dummy_bundled_path, "w") as f:
                    f.write("dummy content")

            path = bootloader.get_bootloader("uefi-ntfs.img", temp_dir)
            self.assertIsNotNone(path, "Failed to get bootloader")
            self.assertTrue(os.path.exists(path), "Bootloader file not found")
            mock_verify.assert_called() # Ensure verify_bootloader was called
            
    @patch('urllib.request.urlretrieve')
    @patch('WowUSB.bootloader.verify_bootloader')
    def test_bootloader_download_fallback(self, mock_verify, mock_urlretrieve):
        """Test bootloader download fallback"""

        # Setup side_effect for verify_bootloader:
        # 1st call (on corrupted bundled): False
        # 2nd call (in download_bootloader on "downloaded" file): True
        # 3rd call (in test on final path): True
        mock_verify.side_effect = [False, True, True]

        def sim_download(url, target_path):
            # Simulate download by creating/copying the dummy file
            with open(target_path, "w") as f:
                f.write("dummy content from download")
            return (target_path, None) # 보통 urlretrieve는 (filename, headers)를 반환

        mock_urlretrieve.side_effect = sim_download

        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Ensure a "bundled" (but we'll make it seem corrupted by verify_bootloader)
            #    version of the file exists for get_bootloader_path to return a path.
            #    The actual content doesn't matter as verify_bootloader is mocked.
            corrupted_bundled_path = get_bootloader_path("uefi-ntfs.img") # This path will be used by get_bootloader
            if not os.path.exists(os.path.dirname(corrupted_bundled_path)):
                os.makedirs(os.path.dirname(corrupted_bundled_path))
            with open(corrupted_bundled_path, "w") as f:
                f.write("corrupted dummy content")

            # 2. Define where the "download" will go
            download_dir = os.path.join(temp_dir, "downloaded_bootloaders")
            # os.makedirs(download_dir) # download_bootloader in SUT should create this if needed, or its target path.
                                      # Actually, get_bootloader creates a temp dir if None is passed.
                                      # If we pass a dir, it should use it.
            
            # Temporarily make get_bootloader_path point to our "corrupted" file for the first check
            # This isn't strictly necessary if the first call to verify_bootloader(bundled_path)
            # is correctly returning False due to the side_effect.
            
            path = bootloader.get_bootloader("uefi-ntfs.img", download_dir) # Pass download_dir

            self.assertIsNotNone(path, "Failed to get bootloader with fallback")
            self.assertTrue(os.path.exists(path), "Downloaded bootloader file not found")
            
            # Check that urlretrieve was called (meaning download was attempted)
            mock_urlretrieve.assert_called_once()
            # Check that verify_bootloader was called multiple times as expected
            self.assertEqual(mock_verify.call_count, 2) # Once for bundled (False), once for downloaded (True)
            # The final assert in the test calls it a third time. So, 3 if we count that.
            # Let's adjust based on the flow of get_bootloader:
            # 1. verify_bootloader(bundled_path) -> False (due to side_effect[0])
            # 2. download_bootloader is called.
            # 3. Inside download_bootloader: verify_bootloader(temp_downloaded_path) -> True (due to side_effect[1])
            # So, by the time get_bootloader returns, verify_bootloader was called twice.
            
            # The test itself then calls verify_bootloader one more time.
            self.assertTrue(bootloader.verify_bootloader(path),
                           "Downloaded bootloader should pass verification")
            self.assertEqual(mock_verify.call_count, 3)


if __name__ == "__main__":
    unittest.main()
