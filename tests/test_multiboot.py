#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Test script for WowUSB-DS9 multi-boot functionality.
This script tests the multi-boot functionality of WowUSB-DS9.
"""

import os
import sys
import unittest
import tempfile
import subprocess
from unittest.mock import patch, MagicMock, call

# Add parent directory to path for importing WowUSB modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import WowUSB.multiboot as multiboot
from tests.test_base import WowUSBTestCase

class MultiBootTests(WowUSBTestCase):
    """Test cases for multi-boot functionality"""
    
    def test_multiboot_manager_initialization(self):
        """Test MultiBootManager initialization"""
        # Create MultiBootManager
        mb_manager = multiboot.MultiBootManager("/dev/sdX", verbose=True)
        
        # Check attributes
        self.assertEqual(mb_manager.target_device, "/dev/sdX")
        self.assertTrue(mb_manager.verbose)
        self.assertEqual(mb_manager.os_entries, [])
        self.assertIsNone(mb_manager.efi_partition)
        self.assertIsNone(mb_manager.boot_partition)
        self.assertIsNone(mb_manager.shared_partition)
        self.assertEqual(mb_manager.temp_mounts, {})
    
    def test_create_partition_layout_gpt(self):
        """Test create_partition_layout with GPT"""
        # Create MultiBootManager
        mb_manager = multiboot.MultiBootManager("/dev/sdX")
        
        # Mock subprocess.run
        self.mock_run.return_value.returncode = 0
        
        # Test create_partition_layout
        result = mb_manager.create_partition_layout(
            partition_table="gpt",
            efi_size_mb=200,
            boot_size_mb=200,
            shared_size_mb=4096,
            shared_filesystem="EXFAT"
        )
        
        # Check result
        self.assertEqual(result, 0)
        
        # Check partitions
        self.assertEqual(mb_manager.efi_partition, "/dev/sdX1")
        self.assertEqual(mb_manager.boot_partition, "/dev/sdX2")
        self.assertEqual(mb_manager.shared_partition, "/dev/sdX3")
        
        # Verify subprocess calls
        self.mock_run.assert_any_call(["wipefs", "--all", "/dev/sdX"], capture_output=True, text=True)
        self.mock_run.assert_any_call(["parted", "--script", "/dev/sdX", "mklabel", "gpt"], 
                                    capture_output=True, text=True)
        self.mock_run.assert_any_call([
            "parted", "--script", "/dev/sdX",
            "mkpart", "ESP", "fat32", "1MiB", "201MiB",
            "set", "1", "boot", "on",
            "set", "1", "esp", "on"
        ], capture_output=True, text=True)
        self.mock_run.assert_any_call([
            "parted", "--script", "/dev/sdX",
            "mkpart", "BOOT", "fat32", "201MiB", "401MiB"
        ], capture_output=True, text=True)
        self.mock_run.assert_any_call([
            "parted", "--script", "/dev/sdX",
            "mkpart", "SHARED", "401MiB", "4497MiB"
        ], capture_output=True, text=True)
        self.mock_run.assert_any_call(["mkfs.fat", "-F", "32", "-n", "ESP", "/dev/sdX1"], 
                                    capture_output=True, text=True)
        self.mock_run.assert_any_call(["mkfs.fat", "-F", "32", "-n", "BOOT", "/dev/sdX2"], 
                                    capture_output=True, text=True)
    
    def test_create_partition_layout_mbr(self):
        """Test create_partition_layout with MBR"""
        # Create MultiBootManager
        mb_manager = multiboot.MultiBootManager("/dev/sdX")
        
        # Mock subprocess.run
        self.mock_run.return_value.returncode = 0
        
        # Test create_partition_layout
        result = mb_manager.create_partition_layout(
            partition_table="mbr",
            boot_size_mb=200,
            shared_size_mb=4096,
            shared_filesystem="EXFAT"
        )
        
        # Check result
        self.assertEqual(result, 0)
        
        # Check partitions
        self.assertIsNone(mb_manager.efi_partition)
        self.assertEqual(mb_manager.boot_partition, "/dev/sdX1")
        self.assertEqual(mb_manager.shared_partition, "/dev/sdX2")
        
        # Verify subprocess calls
        self.mock_run.assert_any_call(["wipefs", "--all", "/dev/sdX"], capture_output=True, text=True)
        self.mock_run.assert_any_call(["parted", "--script", "/dev/sdX", "mklabel", "mbr"], 
                                    capture_output=True, text=True)
        self.mock_run.assert_any_call([
            "parted", "--script", "/dev/sdX",
            "mkpart", "primary", "fat32", "1MiB", "201MiB",
            "set", "1", "boot", "on"
        ], capture_output=True, text=True)
        self.mock_run.assert_any_call([
            "parted", "--script", "/dev/sdX",
            "mkpart", "primary", "201MiB", "4297MiB"
        ], capture_output=True, text=True)
        self.mock_run.assert_any_call(["mkfs.fat", "-F", "32", "-n", "BOOT", "/dev/sdX1"], 
                                    capture_output=True, text=True)
    
    def test_add_os_partition(self):
        """Test add_os_partition"""
        # Create MultiBootManager
        mb_manager = multiboot.MultiBootManager("/dev/sdX")
        
        # Mock subprocess.run
        self.mock_run.return_value.returncode = 0
        self.mock_run.return_value.stdout = "sdX\nsdX1\nsdX2\nsdX3\n"
        
        # Mock parted output
        parted_output = """
Model: Disk (disk)
Disk /dev/sdX: 16.0GB
Sector size (logical/physical): 512B/512B
Partition Table: gpt
Disk Flags: 

Number  Start   End     Size    File system  Name    Flags
 1      1049kB  210MB   209MB   fat32        ESP     boot, esp
 2      210MB   410MB   200MB   fat32        BOOT    
 3      410MB   4610MB  4200MB  exfat        SHARED  
"""
        self.mock_run.return_value.stdout = parted_output
        
        # Test add_os_partition
        partition = mb_manager.add_os_partition(
            os_type="windows",
            size_mb=8192,
            filesystem="NTFS",
            label="WINDOWS"
        )
        
        # Check result
        self.assertEqual(partition, "/dev/sdX4")
        
        # Verify subprocess calls
        self.mock_run.assert_any_call(["lsblk", "-no", "NAME", "/dev/sdX"], 
                                    capture_output=True, text=True)
        self.mock_run.assert_any_call(["parted", "--script", "/dev/sdX", "unit", "MB", "print"], 
                                    capture_output=True, text=True)
        self.mock_run.assert_any_call([
            "parted", "--script", "/dev/sdX",
            "mkpart", "primary", "4610MB", "12802MB"
        ], capture_output=True, text=True)
        self.mock_run.assert_any_call([
            "parted", "--script", "/dev/sdX",
            "set", "4", "msftdata", "on"
        ], capture_output=True, text=True)
    
    def test_install_grub2_bootloader(self):
        """Test install_grub2_bootloader"""
        # Create MultiBootManager
        mb_manager = multiboot.MultiBootManager("/dev/sdX")
        mb_manager.boot_partition = "/dev/sdX2"
        mb_manager.efi_partition = "/dev/sdX1"
        
        # Mock subprocess.run
        self.mock_run.return_value.returncode = 0
        
        # Mock tempfile.mkdtemp
        with patch('tempfile.mkdtemp') as mock_mkdtemp:
            mock_mkdtemp.side_effect = ["/tmp/boot", "/tmp/efi"]
            
            # Test install_grub2_bootloader
            result = mb_manager.install_grub2_bootloader()
            
            # Check result
            self.assertEqual(result, 0)
            
            # Check temp_mounts
            self.assertEqual(mb_manager.temp_mounts, {"boot": "/tmp/boot", "efi": "/tmp/efi"})
            
            # Verify subprocess calls
            self.mock_run.assert_any_call(["mount", "/dev/sdX2", "/tmp/boot"], 
                                        capture_output=True, text=True)
            self.mock_run.assert_any_call([
                "grub-install",
                "--target=i386-pc",
                "--boot-directory=/tmp/boot/boot",
                "--recheck",
                "/dev/sdX"
            ], capture_output=True, text=True)
            self.mock_run.assert_any_call(["mount", "/dev/sdX1", "/tmp/efi"], 
                                        capture_output=True, text=True)
            self.mock_run.assert_any_call([
                "grub-install",
                "--target=x86_64-efi",
                "--boot-directory=/tmp/boot/boot",
                "--efi-directory=/tmp/efi",
                "--removable",
                "--recheck"
            ], capture_output=True, text=True)
    
    def test_add_os_entry(self):
        """Test add_os_entry"""
        # Create MultiBootManager
        mb_manager = multiboot.MultiBootManager("/dev/sdX")
        
        # Mock subprocess.run
        self.mock_run.return_value.stdout = "1234-5678"
        
        # Test add_os_entry for Windows
        result = mb_manager.add_os_entry(
            name="Windows 10",
            os_type="windows",
            partition="/dev/sdX4",
            filesystem="NTFS",
            wintogo=False
        )
        
        # Check result
        self.assertEqual(result, 0)
        
        # Check os_entries
        self.assertEqual(len(mb_manager.os_entries), 1)
        self.assertEqual(mb_manager.os_entries[0]["name"], "Windows 10")
        self.assertEqual(mb_manager.os_entries[0]["type"], "windows")
        self.assertEqual(mb_manager.os_entries[0]["partition"], "/dev/sdX4")
        self.assertEqual(mb_manager.os_entries[0]["filesystem"], "NTFS")
        self.assertEqual(mb_manager.os_entries[0]["uuid"], "1234-5678")
        self.assertEqual(mb_manager.os_entries[0]["wintogo"], False)
        
        # Test add_os_entry for Linux
        result = mb_manager.add_os_entry(
            name="Ubuntu",
            os_type="linux",
            partition="/dev/sdX5",
            filesystem="EXT4",
            kernel="/boot/vmlinuz",
            initrd="/boot/initrd.img",
            kernel_params="ro quiet splash"
        )
        
        # Check result
        self.assertEqual(result, 0)
        
        # Check os_entries
        self.assertEqual(len(mb_manager.os_entries), 2)
        self.assertEqual(mb_manager.os_entries[1]["name"], "Ubuntu")
        self.assertEqual(mb_manager.os_entries[1]["type"], "linux")
        self.assertEqual(mb_manager.os_entries[1]["partition"], "/dev/sdX5")
        self.assertEqual(mb_manager.os_entries[1]["filesystem"], "EXT4")
        self.assertEqual(mb_manager.os_entries[1]["uuid"], "1234-5678")
        self.assertEqual(mb_manager.os_entries[1]["kernel"], "/boot/vmlinuz")
        self.assertEqual(mb_manager.os_entries[1]["initrd"], "/boot/initrd.img")
        self.assertEqual(mb_manager.os_entries[1]["kernel_params"], "ro quiet splash")
    
    def test_generate_grub2_config(self):
        """Test generate_grub2_config"""
        # Create MultiBootManager
        mb_manager = multiboot.MultiBootManager("/dev/sdX")
        mb_manager.temp_mounts = {"boot": "/tmp/boot"}
        mb_manager.os_entries = [
            {
                "name": "Windows 10",
                "type": "windows",
                "partition": "/dev/sdX4",
                "filesystem": "NTFS",
                "uuid": "1234-5678",
                "wintogo": False
            },
            {
                "name": "Ubuntu",
                "type": "linux",
                "partition": "/dev/sdX5",
                "filesystem": "EXT4",
                "uuid": "5678-1234",
                "kernel": "/boot/vmlinuz",
                "initrd": "/boot/initrd.img",
                "kernel_params": "ro quiet splash"
            }
        ]
        
        # Mock open
        with patch('builtins.open', MagicMock()):
            # Test generate_grub2_config
            result = mb_manager.generate_grub2_config()
            
            # Check result
            self.assertEqual(result, 0)
    
    def test_cleanup(self):
        """Test cleanup"""
        # Create MultiBootManager
        mb_manager = multiboot.MultiBootManager("/dev/sdX")
        mb_manager.temp_mounts = {"boot": "/tmp/boot", "efi": "/tmp/efi"}
        
        # Mock os.rmdir
        with patch('os.rmdir') as mock_rmdir:
            # Test cleanup
            mb_manager.cleanup()
            
            # Check temp_mounts
            self.assertEqual(mb_manager.temp_mounts, {})
            
            # Verify subprocess calls
            self.mock_run.assert_any_call(["umount", "/tmp/boot"], stderr=subprocess.DEVNULL)
            self.mock_run.assert_any_call(["umount", "/tmp/efi"], stderr=subprocess.DEVNULL)
            
            # Verify os.rmdir calls
            mock_rmdir.assert_any_call("/tmp/boot")
            mock_rmdir.assert_any_call("/tmp/efi")
    
    def test_create_multiboot_usb(self):
        """Test create_multiboot_usb"""
        # Mock MultiBootManager
        with patch('WowUSB.multiboot.MultiBootManager') as mock_manager_class:
            # Create mock manager
            mock_manager = MagicMock()
            mock_manager.create_partition_layout.return_value = 0
            mock_manager.add_os_partition.return_value = "/dev/sdX4"
            mock_manager.add_os_entry.return_value = 0
            mock_manager.install_grub2_bootloader.return_value = 0
            mock_manager.generate_grub2_config.return_value = 0
            
            # Set mock manager as return value
            mock_manager_class.return_value = mock_manager
            
            # Mock subprocess.run
            self.mock_run.return_value.returncode = 0
            
            # Test create_multiboot_usb
            result = multiboot.create_multiboot_usb(
                target_device="/dev/sdX",
                os_configs=[
                    {
                        "type": "windows",
                        "name": "Windows 10",
                        "iso_path": "/path/to/windows.iso",
                        "size_mb": 8192,
                        "filesystem": "NTFS"
                    },
                    {
                        "type": "linux",
                        "name": "Ubuntu",
                        "iso_path": "/path/to/ubuntu.iso",
                        "size_mb": 4096,
                        "filesystem": "EXT4"
                    }
                ],
                shared_size_mb=4096,
                shared_filesystem="EXFAT",
                verbose=True
            )
            
            # Check result
            self.assertEqual(result, 0)
            
            # Verify MultiBootManager calls
            mock_manager_class.assert_called_once_with("/dev/sdX", True)
            mock_manager.create_partition_layout.assert_called_once_with(
                partition_table="gpt",
                shared_size_mb=4096,
                shared_filesystem="EXFAT"
            )
            self.assertEqual(mock_manager.add_os_partition.call_count, 2)
            self.assertEqual(mock_manager.add_os_entry.call_count, 2)
            mock_manager.install_grub2_bootloader.assert_called_once()
            mock_manager.generate_grub2_config.assert_called_once()
            mock_manager.cleanup.assert_called_once()

if __name__ == "__main__":
    unittest.main()
