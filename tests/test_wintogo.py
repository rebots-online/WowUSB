#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Test script for WowUSB-DS9 Windows-To-Go functionality.
This script tests the Windows-To-Go implementation.
"""

import os
import sys
import tempfile
import unittest
import subprocess
from unittest.mock import MagicMock, patch # Added MagicMock and patch

# Add parent directory to path for importing WowUSB modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import WowUSB.core as core
import WowUSB.utils as utils
import WowUSB.workaround as workaround

class WindowsToGoTests(unittest.TestCase):
    """Test cases for Windows-To-Go functionality"""
    
    def test_windows_version_detection(self):
        """Test Windows version detection"""
        # Create a mock Windows installation directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory structure
            sources_dir = os.path.join(temp_dir, "sources")
            os.makedirs(sources_dir)
            
            # Create mock Windows 10 files
            with open(os.path.join(sources_dir, "cversion.ini"), "w") as f:
                f.write("""
[HostBuild]
MinClient=10.0
BuildNumber=19041
""")
            
            # Test Windows 10 detection
            version, build, is_win11 = utils.detect_windows_version(temp_dir)
            self.assertEqual(version, "10")
            self.assertEqual(build, "19041")
            self.assertFalse(is_win11)
            
            # Create mock Windows 11 files
            with open(os.path.join(sources_dir, "appraiserres.dll"), "w") as f:
                f.write("Mock Windows 11 file")
                
            # Update cversion.ini for Windows 11
            with open(os.path.join(sources_dir, "cversion.ini"), "w") as f:
                f.write("""
[HostBuild]
MinClient=10.0
BuildNumber=22000
""")
            
            # Test Windows 11 detection
            version, build, is_win11 = utils.detect_windows_version(temp_dir)
            self.assertEqual(version, "11")
            self.assertEqual(build, "22000")
            self.assertTrue(is_win11)
    
    def test_tpm_bypass_creation(self):
        """Test TPM bypass registry file creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Windows directory structure
            windows_dir = os.path.join(temp_dir, "Windows", "System32", "config")
            os.makedirs(windows_dir, exist_ok=True)
            
            # Apply TPM bypass
            result = workaround.bypass_windows11_tpm_requirement(temp_dir)
            self.assertEqual(result, 0)
            
            # Check if registry file was created
            reg_file_path = os.path.join(temp_dir, "bypass_requirements.reg")
            self.assertTrue(os.path.exists(reg_file_path))
            
            # Check if setup script was created
            setup_script_path = os.path.join(temp_dir, "Windows", "Setup", "Scripts", "SetupComplete.cmd")
            self.assertTrue(os.path.exists(setup_script_path))
            
            # Check registry file content
            with open(reg_file_path, "r") as f:
                content = f.read()
                self.assertIn("BypassTPMCheck", content)
                self.assertIn("BypassSecureBootCheck", content)
                self.assertIn("BypassRAMCheck", content)
    
    def test_portable_drivers_configuration(self):
        """Test portable drivers configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Windows directory structure
            setup_dir = os.path.join(temp_dir, "Windows", "Setup", "Scripts")
            os.makedirs(setup_dir, exist_ok=True)
            
            # Create initial setup script
            with open(os.path.join(setup_dir, "SetupComplete.cmd"), "w") as f:
                f.write("@echo off\n")
            
            # Apply portable drivers configuration
            result = workaround.prepare_windows_portable_drivers(temp_dir)
            self.assertEqual(result, 0)
            
            # Check if registry file was created
            reg_file_path = os.path.join(temp_dir, "portable_config.reg")
            self.assertTrue(os.path.exists(reg_file_path))
            
            # Check registry file content
            with open(reg_file_path, "r") as f:
                content = f.read()
                self.assertIn("DisableCrossSessionDriverLoad", content)
                self.assertIn("HiberbootEnabled", content)
                self.assertIn("DisablePagingExecutive", content)
            
            # Check if setup script was updated
            with open(os.path.join(setup_dir, "SetupComplete.cmd"), "r") as f:
                content = f.read()
                self.assertIn("portable_config.reg", content)
                self.assertIn("Get-NetAdapter", content)
    
    def test_wintogo_partition_layout(self):
        """Test Windows-To-Go partition layout creation (mock)"""
        # Mock the subprocess.run function to avoid actual disk operations
        original_run = subprocess.run
        
        try:
            # Create a mock subprocess.run that always succeeds
            def mock_run(cmd, *args, **kwargs):
                class MockCompletedProcess:
                    def __init__(self):
                        self.returncode = 0
                        self.stdout = b""
                        self.stderr = b""
                return MockCompletedProcess()
            
            subprocess.run = mock_run
            
            # Mock the filesystem handler
            mock_fs_handler_instance = MagicMock()
            mock_fs_handler_instance.parted_fs_type.return_value = "ntfs" # or whatever is appropriate
            mock_fs_handler_instance.format_partition.return_value = 0
            
            # Mock the get_filesystem_handler function
            original_get_handler = core.fs_handlers.get_filesystem_handler
            core.fs_handlers.get_filesystem_handler = lambda x: mock_fs_handler_instance # Return an instance
            
            # Test partition layout creation
            result = core.create_wintogo_partition_layout("/dev/sdX", "NTFS", "Windows")
            self.assertEqual(result, 0)
            
        finally:
            # Restore original functions
            subprocess.run = original_run
            if 'original_get_handler' in locals():
                core.fs_handlers.get_filesystem_handler = original_get_handler

if __name__ == "__main__":
    unittest.main()
