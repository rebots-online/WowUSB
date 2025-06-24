#!/bin/bash
# Create a bootable ISO from a directory using xorriso
# Usage: create_iso.sh <source_dir> <output_iso>
set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <source_dir> <output_iso>"
    exit 1
fi

SRC="$1"
OUTPUT="$2"

if [ ! -d "$SRC" ]; then
    echo "Source directory not found: $SRC"
    exit 1
fi

xorriso -as mkisofs -r -J -joliet -iso-level 3 -o "$OUTPUT" -V WOWUSB "$SRC"
