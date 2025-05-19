#!/bin/bash
# WowUSB-DS9 Linux Filesystem Test Script
# This script tests F2FS and BTRFS support with Linux distributions

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    exit 1
fi

# Check for required tools
check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}Error: $1 is required but not installed${NC}"
        return 1
    fi
    return 0
}

check_filesystem_tools() {
    local fs_type="$1"
    local missing_tools=()
    
    case "$fs_type" in
        f2fs)
            if ! check_dependency "mkfs.f2fs"; then
                missing_tools+=("f2fs-tools")
            fi
            ;;
        btrfs)
            if ! check_dependency "mkfs.btrfs"; then
                missing_tools+=("btrfs-progs")
            fi
            ;;
        *)
            echo -e "${RED}Error: Unsupported filesystem type: $fs_type${NC}"
            return 1
            ;;
    esac
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo -e "${RED}Error: The following tools are required but not installed:${NC}"
        for tool in "${missing_tools[@]}"; do
            echo -e "${RED}  - $tool${NC}"
        done
        return 1
    fi
    
    return 0
}

# Function to test filesystem creation
test_filesystem_creation() {
    local fs_type="$1"
    local iso_path="$2"
    local target_device="$3"
    local with_persistence="$4"
    
    echo -e "${BLUE}=== Testing $fs_type filesystem creation with $(basename "$iso_path") ===${NC}"
    
    # Check filesystem tools
    if ! check_filesystem_tools "$fs_type"; then
        echo -e "${RED}Skipping $fs_type test due to missing tools${NC}"
        return 1
    fi
    
    # Unmount any existing mounts
    echo -e "${GREEN}Unmounting any existing mounts...${NC}"
    for mount_point in $(mount | grep "$target_device" | awk '{print $3}'); do
        umount "$mount_point" 2>/dev/null || true
    done
    
    # Create bootable USB
    echo -e "${GREEN}Creating bootable USB with $fs_type filesystem...${NC}"
    local start_time=$(date +%s)
    
    if [ "$with_persistence" = "true" ]; then
        echo -e "${GREEN}Adding persistence support...${NC}"
        wowusb --device "$iso_path" "$target_device" --target-filesystem "${fs_type^^}" --persistence 4096
    else
        wowusb --device "$iso_path" "$target_device" --target-filesystem "${fs_type^^}"
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo -e "${GREEN}Creation completed in $duration seconds${NC}"
    
    # Verify filesystem
    echo -e "${GREEN}Verifying filesystem...${NC}"
    local fs_info=$(lsblk -f "$target_device"1 -o FSTYPE | tail -n 1)
    echo -e "${GREEN}Filesystem type: $fs_info${NC}"
    
    if [[ "$fs_info" != *"$fs_type"* ]]; then
        echo -e "${RED}Error: Filesystem verification failed. Expected $fs_type, got $fs_info${NC}"
        return 1
    fi
    
    # Mount and check files
    echo -e "${GREEN}Mounting filesystem to verify files...${NC}"
    local mount_point="/mnt/test_$fs_type"
    mkdir -p "$mount_point"
    
    if ! mount "$target_device"1 "$mount_point"; then
        echo -e "${RED}Error: Failed to mount filesystem${NC}"
        return 1
    fi
    
    # Check for essential boot files
    echo -e "${GREEN}Checking for essential boot files...${NC}"
    if [ -d "$mount_point/boot" ]; then
        echo -e "${GREEN}Boot directory found${NC}"
        ls -la "$mount_point/boot" | head -n 10
    else
        echo -e "${RED}Error: Boot directory not found${NC}"
        umount "$mount_point"
        return 1
    fi
    
    if [ -d "$mount_point/EFI" ]; then
        echo -e "${GREEN}EFI directory found (UEFI boot supported)${NC}"
        ls -la "$mount_point/EFI" | head -n 10
    else
        echo -e "${YELLOW}Warning: EFI directory not found (UEFI boot may not be supported)${NC}"
    fi
    
    # Check filesystem-specific features
    if [ "$fs_type" = "btrfs" ]; then
        echo -e "${GREEN}Checking BTRFS-specific features...${NC}"
        echo -e "${GREEN}Subvolumes:${NC}"
        btrfs subvolume list "$mount_point" || echo -e "${YELLOW}No subvolumes found${NC}"
        
        echo -e "${GREEN}Filesystem usage:${NC}"
        btrfs filesystem df "$mount_point"
    fi
    
    # Check persistence setup if enabled
    if [ "$with_persistence" = "true" ]; then
        echo -e "${GREEN}Checking persistence setup...${NC}"
        if [ "$fs_type" = "f2fs" ]; then
            if [ -f "$mount_point/persistence.conf" ]; then
                echo -e "${GREEN}Persistence configuration found${NC}"
                cat "$mount_point/persistence.conf"
            else
                echo -e "${YELLOW}Warning: Persistence configuration not found${NC}"
            fi
        elif [ "$fs_type" = "btrfs" ]; then
            echo -e "${GREEN}Checking for persistence subvolume...${NC}"
            btrfs subvolume list "$mount_point" | grep -i "persistence" || echo -e "${YELLOW}No persistence subvolume found${NC}"
        fi
    fi
    
    # Unmount
    echo -e "${GREEN}Unmounting filesystem...${NC}"
    umount "$mount_point"
    
    echo -e "${GREEN}$fs_type filesystem test completed successfully${NC}"
    return 0
}

# Main function
main() {
    # Parse command line arguments
    local fs_type=""
    local iso_path=""
    local target_device=""
    local with_persistence="false"
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --filesystem)
                fs_type="$2"
                shift 2
                ;;
            --iso)
                iso_path="$2"
                shift 2
                ;;
            --target)
                target_device="$2"
                shift 2
                ;;
            --persistence)
                with_persistence="true"
                shift
                ;;
            --help)
                echo "Usage: $0 --filesystem [f2fs|btrfs] --iso /path/to/linux.iso --target /dev/sdX [--persistence]"
                exit 0
                ;;
            *)
                echo -e "${RED}Error: Unknown option: $1${NC}"
                echo "Usage: $0 --filesystem [f2fs|btrfs] --iso /path/to/linux.iso --target /dev/sdX [--persistence]"
                exit 1
                ;;
        esac
    done
    
    # Validate arguments
    if [ -z "$fs_type" ] || [ -z "$iso_path" ] || [ -z "$target_device" ]; then
        echo -e "${RED}Error: Missing required arguments${NC}"
        echo "Usage: $0 --filesystem [f2fs|btrfs] --iso /path/to/linux.iso --target /dev/sdX [--persistence]"
        exit 1
    fi
    
    if [ ! -f "$iso_path" ]; then
        echo -e "${RED}Error: ISO file not found: $iso_path${NC}"
        exit 1
    fi
    
    if [ ! -b "$target_device" ]; then
        echo -e "${RED}Error: Target device not found or not a block device: $target_device${NC}"
        exit 1
    fi
    
    # Confirm with user
    echo -e "${RED}WARNING: All data on $target_device will be lost!${NC}"
    read -p "Are you sure you want to continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Operation cancelled by user${NC}"
        exit 0
    fi
    
    # Run the test
    if test_filesystem_creation "$fs_type" "$iso_path" "$target_device" "$with_persistence"; then
        echo -e "${GREEN}Test completed successfully!${NC}"
        echo -e "${GREEN}Please test bootability on target hardware.${NC}"
    else
        echo -e "${RED}Test failed!${NC}"
        exit 1
    fi
}

# Run the main function
main "$@"
