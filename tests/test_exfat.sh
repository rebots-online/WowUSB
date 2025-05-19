
#!/bin/bash
# WowUSB-DS9 exFAT Implementation Test Script
# This script tests the exFAT implementation, particularly for large file support

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
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
        exit 1
    fi
}

check_dependency losetup
check_dependency mkfs.exfat
check_dependency mount
check_dependency umount
check_dependency dd

echo -e "${GREEN}All required dependencies are installed${NC}"

# Create a temporary directory for testing
TEMP_DIR=$(mktemp -d)
echo -e "${GREEN}Created temporary directory: $TEMP_DIR${NC}"

# Create a test image file (8GB)
TEST_IMAGE="$TEMP_DIR/exfat_test.img"
echo -e "${GREEN}Creating 8GB test image file...${NC}"
dd if=/dev/zero of="$TEST_IMAGE" bs=1M count=8192 status=progress

# Set up loop device
echo -e "${GREEN}Setting up loop device...${NC}"
LOOP_DEV=$(losetup -f --show "$TEST_IMAGE")
echo -e "${GREEN}Using loop device: $LOOP_DEV${NC}"

# Format with exFAT
echo -e "${GREEN}Formatting with exFAT...${NC}"
mkfs.exfat -n "WOWUSBTEST" "$LOOP_DEV"

# Create mount point
MOUNT_POINT="$TEMP_DIR/mnt"
mkdir -p "$MOUNT_POINT"

# Mount the filesystem
echo -e "${GREEN}Mounting exFAT filesystem...${NC}"
mount -t exfat "$LOOP_DEV" "$MOUNT_POINT"

# Test large file creation
echo -e "${GREEN}Testing large file creation (5GB)...${NC}"
dd if=/dev/zero of="$MOUNT_POINT/large_file.bin" bs=1M count=5120 status=progress

# Verify file size
FILE_SIZE=$(stat -c %s "$MOUNT_POINT/large_file.bin")
EXPECTED_SIZE=$((5120 * 1024 * 1024))

if [ "$FILE_SIZE" -eq "$EXPECTED_SIZE" ]; then
    echo -e "${GREEN}Large file test passed! File size: $FILE_SIZE bytes${NC}"
else
    echo -e "${RED}Large file test failed! Expected: $EXPECTED_SIZE, Got: $FILE_SIZE${NC}"
    # Clean up and exit with error
    umount "$MOUNT_POINT" 2>/dev/null || true
    losetup -d "$LOOP_DEV" 2>/dev/null || true
    rm -rf "$TEMP_DIR" 2>/dev/null || true
    exit 1
fi

# Test file copy performance
echo -e "${GREEN}Testing file copy performance...${NC}"
time dd if=/dev/zero of="$MOUNT_POINT/perf_test.bin" bs=1M count=1024 status=progress

# Test random I/O performance
echo -e "${GREEN}Testing random I/O performance...${NC}"
time dd if=/dev/urandom of="$MOUNT_POINT/random_test.bin" bs=1M count=100 status=progress

# Test file integrity
echo -e "${GREEN}Testing file integrity...${NC}"
CHECKSUM_FILE="$TEMP_DIR/checksum.txt"
dd if=/dev/urandom of="$MOUNT_POINT/integrity_test.bin" bs=1M count=100 status=progress
md5sum "$MOUNT_POINT/integrity_test.bin" > "$CHECKSUM_FILE"

# Unmount and remount to ensure persistence
echo -e "${GREEN}Unmounting and remounting to test persistence...${NC}"
umount "$MOUNT_POINT"
mount -t exfat "$LOOP_DEV" "$MOUNT_POINT"

# Verify file integrity after remount
echo -e "${GREEN}Verifying file integrity after remount...${NC}"
if md5sum -c "$CHECKSUM_FILE"; then
    echo -e "${GREEN}File integrity test passed!${NC}"
else
    echo -e "${RED}File integrity test failed!${NC}"
    # Clean up and exit with error
    umount "$MOUNT_POINT" 2>/dev/null || true
    losetup -d "$LOOP_DEV" 2>/dev/null || true
    rm -rf "$TEMP_DIR" 2>/dev/null || true
    exit 1
fi

# Test filesystem validation
echo -e "${GREEN}Testing filesystem validation...${NC}"
umount "$MOUNT_POINT"
if command -v fsck.exfat &> /dev/null; then
    fsck.exfat -n "$LOOP_DEV"
elif command -v exfatfsck &> /dev/null; then
    exfatfsck -n "$LOOP_DEV"
else
    echo -e "${YELLOW}Warning: No exFAT filesystem check tool found, skipping validation${NC}"
fi

# Clean up
echo -e "${GREEN}Cleaning up...${NC}"
losetup -d "$LOOP_DEV"
rm -rf "$TEMP_DIR"

echo -e "${GREEN}exFAT implementation test completed successfully!${NC}"

