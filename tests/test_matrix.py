#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (C)2025 Robin L. M. Cheung, MBA

"""
Test matrix for WowUSB-DS9.
This module defines test scenarios for comprehensive testing.
"""

import os
import sys
import unittest
import itertools

# Add parent directory to path for importing WowUSB modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Test matrix configuration
WINDOWS_VERSIONS = [
    {"name": "Windows 7", "iso_pattern": "*win7*.iso"},
    {"name": "Windows 8.1", "iso_pattern": "*win8*.iso"},
    {"name": "Windows 10", "iso_pattern": "*win10*.iso"},
    {"name": "Windows 11", "iso_pattern": "*win11*.iso"}
]

FILESYSTEM_TYPES = [
    {"name": "FAT32", "type": "FAT", "supports_large_files": False},
    {"name": "NTFS", "type": "NTFS", "supports_large_files": True},
    {"name": "exFAT", "type": "EXFAT", "supports_large_files": True},
    {"name": "F2FS", "type": "F2FS", "supports_large_files": True},
    {"name": "BTRFS", "type": "BTRFS", "supports_large_files": True}
]

INSTALLATION_MODES = [
    {"name": "Device Mode", "mode": "device"},
    {"name": "Partition Mode", "mode": "partition"}
]

BOOT_MODES = [
    {"name": "Legacy BIOS", "requires_uefi": False},
    {"name": "UEFI", "requires_uefi": True}
]

WINTOGO_MODES = [
    {"name": "Standard Installation", "wintogo": False},
    {"name": "Windows-To-Go", "wintogo": True}
]

def generate_test_scenarios():
    """
    Generate all possible test scenarios based on the test matrix.
    
    Returns:
        list: List of test scenario dictionaries
    """
    scenarios = []
    
    # Generate all combinations
    combinations = itertools.product(
        WINDOWS_VERSIONS,
        FILESYSTEM_TYPES,
        INSTALLATION_MODES,
        BOOT_MODES,
        WINTOGO_MODES
    )
    
    for win_ver, fs_type, install_mode, boot_mode, wintogo_mode in combinations:
        # Skip invalid combinations
        
        # Windows-To-Go requires device mode
        if wintogo_mode["wintogo"] and install_mode["mode"] != "device":
            continue
            
        # Windows-To-Go only works with Windows 10/11
        if wintogo_mode["wintogo"] and "Windows 1" not in win_ver["name"]:
            continue
            
        # UEFI boot with non-FAT32 requires UEFI support partition
        if boot_mode["requires_uefi"] and fs_type["name"] != "FAT32" and install_mode["mode"] == "partition":
            continue
            
        # Create scenario
        scenario = {
            "windows_version": win_ver["name"],
            "iso_pattern": win_ver["iso_pattern"],
            "filesystem": fs_type["name"],
            "filesystem_type": fs_type["type"],
            "supports_large_files": fs_type["supports_large_files"],
            "installation_mode": install_mode["name"],
            "installation_mode_arg": install_mode["mode"],
            "boot_mode": boot_mode["name"],
            "requires_uefi": boot_mode["requires_uefi"],
            "wintogo": wintogo_mode["wintogo"]
        }
        
        # Generate scenario name
        scenario["name"] = f"{win_ver['name']} - {fs_type['name']} - {install_mode['name']} - {boot_mode['name']}"
        if wintogo_mode["wintogo"]:
            scenario["name"] += " - Windows-To-Go"
            
        scenarios.append(scenario)
    
    return scenarios

def get_test_scenarios():
    """
    Get all valid test scenarios.
    
    Returns:
        list: List of test scenario dictionaries
    """
    return generate_test_scenarios()

def get_prioritized_scenarios():
    """
    Get a prioritized subset of test scenarios for quick testing.
    
    Returns:
        list: List of prioritized test scenario dictionaries
    """
    all_scenarios = generate_test_scenarios()
    prioritized = []
    
    # Include at least one scenario for each Windows version
    for win_ver in WINDOWS_VERSIONS:
        for scenario in all_scenarios:
            if scenario["windows_version"] == win_ver["name"]:
                prioritized.append(scenario)
                break
    
    # Include at least one scenario for each filesystem type
    for fs_type in FILESYSTEM_TYPES:
        found = False
        for scenario in prioritized:
            if scenario["filesystem"] == fs_type["name"]:
                found = True
                break
                
        if not found:
            for scenario in all_scenarios:
                if scenario["filesystem"] == fs_type["name"]:
                    prioritized.append(scenario)
                    break
    
    # Include at least one Windows-To-Go scenario
    wintogo_found = False
    for scenario in prioritized:
        if scenario["wintogo"]:
            wintogo_found = True
            break
            
    if not wintogo_found:
        for scenario in all_scenarios:
            if scenario["wintogo"]:
                prioritized.append(scenario)
                break
    
    return prioritized

def print_test_matrix():
    """Print the test matrix in a readable format"""
    scenarios = get_test_scenarios()
    
    print(f"Total number of test scenarios: {len(scenarios)}")
    print("\nTest Matrix:")
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   - Windows Version: {scenario['windows_version']}")
        print(f"   - Filesystem: {scenario['filesystem']}")
        print(f"   - Installation Mode: {scenario['installation_mode']}")
        print(f"   - Boot Mode: {scenario['boot_mode']}")
        print(f"   - Windows-To-Go: {'Yes' if scenario['wintogo'] else 'No'}")

if __name__ == "__main__":
    print_test_matrix()
