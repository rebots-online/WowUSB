# Changelog for WowUSB-DS9

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-06-01

### Added
- Comprehensive release checklist for version 0.4.0
- Documentation reorganization into a dedicated `docs/` directory
- Mermaid.js documentation map for better project navigation
- Detailed project reorganization plan
- Logging system for tracking hKG updates and release progress

### Changed
- Moved all documentation files from project root to `docs/` directory
- Updated internal references to documentation files
- Improved project structure for better maintainability
- Enhanced README.md with updated file locations and project information

### Fixed
- Documentation links after file reorganization
- Potential path resolution issues in documentation references

### Security
- Added security scanning to the release checklist
- Documented security best practices for release process

### Deprecated
- Old documentation files in the root directory (now moved to `docs/`)
- Previous checklists (archived in `docs/` with "(Old - Review/Archive)" suffix)

### Removed
- Duplicate documentation files from root directory (now in `docs/`)
  
### Fixed
- Various documentation typos and inaccuracies

### Security
- Added security scanning to release process
- Documented security considerations for release

## [0.3.0] - 2025-05-19

## [0.3.0] - 2025-05-19

### Added
- Windows-To-Go support for creating portable Windows installations
  - Specialized partition layout (ESP, MSR, Windows)
  - Hardware adaptation for different systems
  - Portable driver configuration
- TPM bypass for Windows 11 compatibility
  - Registry modifications to allow Windows 11 to run on systems without TPM 2.0
  - Automatic application during Windows-To-Go creation
- exFAT filesystem support with optimizations for flash drives
  - Device-specific optimizations (SSD, HDD, USB flash)
  - Comprehensive validation
  - Performance tuning
- F2FS and BTRFS filesystem support
  - Flash-friendly filesystem options
  - Advanced features for Linux distributions
- Automatic filesystem selection based on ISO content
  - Detection of files larger than 4GB
  - Selection based on available tools
  - Preference order: exFAT > NTFS > F2FS > BTRFS > FAT32
- Comprehensive validation for NTFS and exFAT filesystems
  - Filesystem checks after formatting
  - Large file write tests
  - Mount/unmount tests
- Bundled UEFI:NTFS bootloader with fallback download mechanism
  - Integrated bootloader for UEFI booting from NTFS/exFAT
  - Automatic verification and installation
- Device-specific optimizations for different storage types
  - SSD/Flash: 128KB cluster size, 1MB alignment
  - HDD: Optimized parameters for rotational media
- Debian package configuration
  - Native installation on Debian-based systems
  - Desktop integration
- PyPI package configuration
  - Easy installation via pip
  - Automatic dependency handling
- Generic Linux package (tar.gz) with installation scripts
  - Support for various Linux distributions
  - Distribution-specific dependency handling
- Comprehensive test suite
  - Unit tests for core functionality
  - Filesystem handler tests
  - Windows-To-Go functionality tests
- User guide and troubleshooting documentation
  - Detailed usage instructions
  - Solutions to common issues
  - Technical implementation details

### Changed
- Renamed from WoeUSB-ng to WowUSB-DS9
- Improved filesystem detection and selection algorithm
- Enhanced NTFS support with better validation
- Optimized partition layout creation
- Updated documentation with comprehensive installation instructions
- Improved error handling and reporting
- Enhanced GUI with Windows-To-Go option and filesystem selection

### Fixed
- Issues with large files (>4GB) on FAT32 filesystems
- UEFI boot problems with NTFS and exFAT filesystems
- Compatibility issues with newer Windows versions
- Various error handling and reporting issues
- Reliability of bootloader installation
- Partition alignment issues
- Device detection on some systems

## [0.2.0] - 2023-04-15

### Added
- Support for Windows 11
- Basic NTFS support for large files
- Improved error handling
- Better progress reporting

### Changed
- Updated dependencies for modern Linux distributions
- Improved compatibility with newer Python versions
- Enhanced GUI with better user feedback

### Fixed
- Issues with UEFI booting on some systems
- Problems with large ISO files
- Various GUI bugs and crashes

## [0.1.0] - 2022-08-10

### Added
- Initial release based on WoeUSB-ng
- Support for Windows Vista, 7, 8.x, 10
- FAT32 filesystem support
- Basic UEFI and Legacy boot support
- Command line and GUI interfaces
