#!/bin/bash
# Build script for WowUSB-DS9 Debian package

set -e

# Check for required tools
for cmd in dpkg-buildpackage debuild dh_make; do
    if ! command -v $cmd &> /dev/null; then
        echo "Error: Required command '$cmd' not found. Please install the 'devscripts' and 'dh-make' packages."
        exit 1
    fi
done

# Get the project directory (parent of the script directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Go to the project directory
cd "$PROJECT_DIR"

# Clean up any previous build artifacts
rm -rf build/ dist/ *.egg-info/

# Build the source package
echo "Building Debian source package..."
dpkg-buildpackage -S -us -uc

# Build the binary package
echo "Building Debian binary package..."
dpkg-buildpackage -b -us -uc

# Move the packages to a more convenient location
echo "Moving packages to dist/ directory..."
mkdir -p dist
mv ../wowusb-ds9_*.deb ../wowusb-ds9_*.changes ../wowusb-ds9_*.buildinfo dist/ 2>/dev/null || true

echo "Debian packages built successfully!"
echo "Packages are available in the dist/ directory:"
ls -lh dist/

echo ""
echo "To install the package, run:"
echo "sudo dpkg -i dist/wowusb-ds9_*.deb"
echo "sudo apt-get install -f  # To resolve any dependencies"
