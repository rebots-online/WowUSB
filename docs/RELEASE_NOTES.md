# WowUSB-DS9 v0.4.0 Release Notes

*Release Date: June 1, 2025*

Welcome to WowUSB-DS9 v0.4.0! This release focuses on improving project maintainability, documentation, and the release process. We've reorganized the project structure to make it more intuitive and added comprehensive documentation to help both users and contributors.

## What's New

### Project Reorganization
- **Centralized Documentation**: All documentation has been moved to a dedicated `docs/` directory for better organization
- **Structured Checklists**: Added comprehensive release checklists to ensure consistent and reliable releases
- **Documentation Map**: Created a visual map of all documentation files for easier navigation
- **Improved File Structure**: Cleaned up the project root by moving non-essential files to appropriate directories

### Enhanced Documentation
- **Updated CHANGELOG**: Completely revamped following Keep a Changelog standards
- **Release Process**: Documented the entire release process for maintainers
- **Developer Guides**: Improved contribution guidelines and technical documentation
- **User Documentation**: Updated user guides with the new file locations and features

### Release Process Improvements
- **Automated Version Bumping**: Streamlined version management
- **Comprehensive Testing**: Added detailed testing procedures to the release checklist
- **Security Scanning**: Integrated security checks into the release process
- **Better Logging**: Added structured logging for release activities

## Upgrade Notes
- The main documentation has been moved to the `docs/` directory. Update any bookmarks or references accordingly.
- The release process has been formalized - please review the new checklists if you're a maintainer.
- All documentation links in the codebase have been updated to reflect the new structure.

## Known Issues
- Some internal links in documentation might need updating if they referenced files that were moved
- Users with custom scripts that reference documentation files may need to update their paths

## System Requirements
- Python 3.6 or higher
- Administrative/root privileges for USB operations
- Required system packages as listed in the installation guide

## Getting Started
For new users, please refer to the updated documentation in the `docs/` directory. The main user guide is now located at `docs/USER_GUIDE.md`.

## Feedback and Support
Please report any issues on our [issue tracker](https://github.com/rebots-online/WowUSB/issues). For support, consult the documentation or open a discussion.

---

# WowUSB-DS9 v0.3.0 Release Notes

*Release Date: May 19, 2025*

We're excited to announce the release of WowUSB-DS9 v0.3.0, a significant enhancement of the original WoeUSB/WoeUSB-ng projects. This release introduces several major features and improvements, including extended filesystem support, Windows-To-Go functionality, and improved packaging options.

## New Features

### Extended Filesystem Support
- **exFAT Support**: Added full support for exFAT filesystem with optimizations for flash drives
  - Automatic detection of device type (SSD, HDD, USB flash) and application of optimal parameters
  - Comprehensive validation to ensure filesystem integrity
  - Performance optimizations for different storage types
- **NTFS Enhancements**: Improved NTFS support with better validation and performance
  - Device-specific optimizations for SSDs and HDDs
  - Enhanced validation to prevent corruption
- **F2FS Support**: Added support for Flash-Friendly File System (F2FS)
  - Optimized for flash storage performance
  - Ideal for USB drives that will be used frequently
- **BTRFS Support**: Added support for BTRFS filesystem
  - Advanced features like compression and snapshots
  - Good for Linux-focused usage scenarios

### Windows-To-Go Support
- **Portable Windows**: Create Windows installations that run directly from USB
  - Support for both Windows 10 and Windows 11
  - Specialized partition layout (ESP, MSR, Windows)
  - Hardware adaptation for different systems
- **TPM Bypass for Windows 11**: Automatically bypass TPM 2.0 and Secure Boot requirements
  - Registry modifications to allow Windows 11 to run on systems without TPM 2.0
  - No manual tweaking required
- **Portable Driver Configuration**: Automatically configure Windows for portable operation
  - Registry modifications for hardware detection
  - Driver database optimization for multiple hardware profiles

### Bootloader Integration
- **Bundled UEFI:NTFS Bootloader**: Integrated UEFI:NTFS bootloader for UEFI booting from NTFS/exFAT
  - No need for separate downloads
  - Automatic installation to support partition
- **Fallback Download Mechanism**: Automatic fallback to download bootloader if bundle is corrupted
  - Ensures reliability even if bundled files are damaged
  - Verifies downloaded bootloader integrity

### Automatic Filesystem Selection
- **Smart Detection**: Automatically selects the optimal filesystem based on ISO content
  - Detects files larger than 4GB and chooses appropriate filesystem
  - Preference order: exFAT > NTFS > F2FS > BTRFS > FAT32
- **Tool Availability Check**: Selects filesystem based on available tools on the host system
  - Falls back to alternatives if preferred tools are not installed
  - Clear guidance on missing dependencies

## Improvements

### User Interface
- **Enhanced CLI**: Improved command-line interface with better error reporting
  - More detailed progress information
  - Clearer error messages
- **Updated GUI**: Refreshed graphical interface with new options
  - Windows-To-Go option
  - Filesystem selection dropdown
  - Improved progress reporting

### Performance
- **Optimized Formatting**: Device-specific optimizations for different storage types
  - SSD/Flash: 128KB cluster size, 1MB alignment for exFAT
  - HDD: 32KB cluster size for exFAT
  - Similar optimizations for NTFS
- **Improved Copy Process**: Better handling of large files
  - More efficient copying of large files
  - Progress reporting during long operations

### Documentation
- **Comprehensive Guides**: Added detailed documentation
  - User Guide with step-by-step instructions
  - Troubleshooting Guide for common issues
  - Technical Design document explaining implementation details
- **Updated README**: Completely revised README with installation instructions for all package types

### Packaging and Distribution
- **PyPI Package**: Added proper PyPI packaging
  - Easy installation via pip
  - Automatic dependency handling
- **Debian Package**: Added Debian package configuration
  - Native installation on Debian-based systems
  - Desktop integration
- **Generic Linux Package**: Added tar.gz package with installation scripts
  - Support for various Linux distributions
  - Distribution-specific dependency handling

## Bug Fixes

- Fixed issues with large files (>4GB) on FAT32 filesystems
- Resolved UEFI boot problems with NTFS and exFAT filesystems
- Fixed compatibility issues with newer Windows versions
- Addressed various error handling and reporting issues
- Improved reliability of bootloader installation
- Fixed issues with partition alignment
- Resolved problems with device detection on some systems

## Known Issues

- Windows-To-Go performance depends heavily on USB drive quality and speed
- Some older systems may not support booting from exFAT without additional drivers
- Windows 11 TPM bypass may not work on all systems, particularly those with very recent UEFI firmware
- F2FS and BTRFS support is primarily focused on Linux distributions and may have limited Windows compatibility
- Very large ISOs (>8GB) may experience slower copying speeds
- Secure Boot support is limited and may require manual intervention on some systems

## System Requirements

### Host System (for creating bootable USB)
- Linux distribution (Debian, Ubuntu, Fedora, Arch, etc.)
- Python 3.6 or later
- Required packages (varies by distribution):
  - `python3-pip python3-wxgtk4.0 grub2-common grub-pc-bin parted dosfstools ntfs-3g`
  - For extended filesystem support: `exfat-utils/exfatprogs f2fs-tools btrfs-progs`

### Target System (for booting from USB)
- Any system capable of booting from USB
- For UEFI boot: UEFI firmware with USB boot support
- For Windows-To-Go: 
  - USB 3.0+ port recommended
  - 4GB RAM minimum (8GB+ recommended)
  - x64 CPU with SSE2 support

## Upgrading from Previous Versions

If you're upgrading from WoeUSB-ng or an earlier version of WowUSB-DS9:

1. Uninstall the previous version:
   ```
   sudo pip3 uninstall WoeUSB-ng
   # or
   sudo pip3 uninstall WowUSB-DS9
   ```

2. Install the new version using your preferred method (see README.md for installation instructions)

3. Note that configuration files and settings from previous versions are not compatible with v0.3.0

## Acknowledgments

WowUSB-DS9 builds upon the work of:
- [WoeUSB](https://github.com/slacka/WoeUSB)
- [WoeUSB-ng](https://github.com/WoeUSB/WoeUSB-ng)
- [UEFI:NTFS](https://github.com/pbatard/uefi-ntfs) by Pete Batard

Special thanks to all contributors and testers who have helped improve this project.

## Feedback and Support

We welcome your feedback and contributions to make WowUSB-DS9 even better:
- GitHub Issues: https://github.com/rebots-online/WowUSB/issues
- GitHub Discussions: https://github.com/rebots-online/WowUSB/discussions

For detailed usage instructions, please refer to the [User Guide](USER_GUIDE.md).
For troubleshooting help, see the [Troubleshooting Guide](TROUBLESHOOTING.md).
