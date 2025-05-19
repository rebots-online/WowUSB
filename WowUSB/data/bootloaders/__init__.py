"""
Bootloader data files for WowUSB-DS9.
This package contains bundled bootloader images for various filesystem types.
"""

import os

# Get the directory where bootloader files are stored
BOOTLOADERS_DIR = os.path.dirname(os.path.abspath(__file__))

def get_bootloader_path(filename):
    """
    Get the full path to a bundled bootloader file
    
    Args:
        filename (str): The bootloader filename
        
    Returns:
        str: Full path to the bootloader file
    """
    return os.path.join(BOOTLOADERS_DIR, filename)
