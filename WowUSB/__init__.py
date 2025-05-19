
"""
WowUSB-DS9 - Create bootable Windows USB drives with advanced features
Version: 0.3.0
"""

__version__ = "0.3.0"
__author__ = "Robin L. M. Cheung, MBA"
__license__ = "GPL-3.0"
__description__ = "Create bootable Windows USB drives with support for large files and Windows-To-Go"

from WowUSB import \
    core, \
    list_devices, \
    utils, \
    workaround, \
    miscellaneous, \
    filesystem_handlers, \
    bootloader
