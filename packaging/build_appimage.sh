#!/bin/bash

set -eo pipefail

APP_NAME="WowUSB-DS9"
APP_VERSION=$(grep -Po "^version=\K['\"](.*)['\"]" setup.py | sed "s/['\"]//g") # Extract version from setup.py
ARCH=$(uname -m)
APPIMAGE_FILENAME="${APP_NAME}-${APP_VERSION}-${ARCH}.AppImage"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")" # Assumes packaging script is in 'packaging/' subdir
APPDIR="${PROJECT_DIR}/AppDir"

echo "AppImage Builder for ${APP_NAME} version ${APP_VERSION}"
echo "Project directory: ${PROJECT_DIR}"
echo "AppDir: ${APPDIR}"

# Function to download appimagetool if not found
download_appimagetool() {
    if ! command -v appimagetool &> /dev/null; then
        echo "appimagetool not found. Downloading..."
        APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage"
        wget -q "$APPIMAGETOOL_URL" -O appimagetool
        chmod +x appimagetool
        echo "appimagetool downloaded."
        # Place it somewhere in PATH or use ./appimagetool
        sudo mv appimagetool /usr/local/bin/appimagetool
        # Or alternatively: export PATH=$PWD:$PATH
    fi
}

# 0. Download appimagetool if necessary
download_appimagetool

# 1. Clean up previous AppDir and AppImage
echo "Cleaning up previous build..."
rm -rf "$APPDIR"
rm -f "${PROJECT_DIR}/${APPIMAGE_FILENAME}"

# 2. Create AppDir structure
echo "Creating AppDir structure..."
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/lib"
mkdir -p "$APPDIR/usr/share/icons/default/scalable" # For .svg icon
mkdir -p "$APPDIR/usr/share/applications"

# 3. Install WowUSB-DS9 and its Python dependencies into AppDir using pip
echo "Installing WowUSB-DS9 and Python dependencies into AppDir..."
# Create a virtual environment within AppDir to isolate Python stuff (optional but cleaner)
# python3 -m venv "$APPDIR/usr/python_env"
# "$APPDIR/usr/python_env/bin/pip" install --no-cache-dir --upgrade pip
# "$APPDIR/usr/python_env/bin/pip" install --no-cache-dir -e "${PROJECT_DIR}" # Install local package editable
# "$APPDIR/usr/python_env/bin/pip" install --no-cache-dir wxPython termcolor # Explicitly list deps

# Simpler pip install to a target directory (less isolation but common for AppImages)
# This relies on finding the correct Python version's site-packages.
# We will install the package itself and its dependencies.
# The Python interpreter will be copied separately.

# Install the package and its Python dependencies to a specific location within AppDir
# Create a temporary requirements.txt from setup.py (if needed, or install directly)
# For simplicity, we'll install the local package which should pull its deps.
# The paths for Python libs can be tricky. A common approach is to use python-appimage,
# or bundle a minimal Python, or rely on linuxdeploy's Python plugin.
# For a manual approach:
PYTHON_VERSION_MAJOR_MINOR=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_SITE_PACKAGES_DIR="$APPDIR/usr/lib/python${PYTHON_VERSION_MAJOR_MINOR}/site-packages"
mkdir -p "$PYTHON_SITE_PACKAGES_DIR"

# Install dependencies (wxPython, termcolor)
echo "Installing Python dependencies (wxPython, termcolor) to $PYTHON_SITE_PACKAGES_DIR..."
pip3 install --system --no-cache-dir --target="$PYTHON_SITE_PACKAGES_DIR" wxPython termcolor

echo "Copying WowUSB application files to $PYTHON_SITE_PACKAGES_DIR/WowUSB..."
# Copy the WowUSB package source into site-packages
# shutil.copytree in python or cp -a in bash
cp -a "${PROJECT_DIR}/WowUSB" "$PYTHON_SITE_PACKAGES_DIR/"

# 4. Copy Python interpreter and standard libraries
# This is a crucial and complex step. A proper AppImage should bundle Python.
# A naive approach is to copy `which python3` and its libs.
# This often fails due to path issues and missing transitive dependencies.
# Tools like linuxdeploy + python plugin or python-appimage are better.
# For this script, we'll do a simplified copy. This WILL LIKELY NEED REFINEMENT.
echo "Copying Python interpreter and essential libraries..."
PYTHON_EXE_PATH=$(which python3)
if [ -z "$PYTHON_EXE_PATH" ]; then
    echo "Error: python3 not found in PATH."
    exit 1
fi
cp "$PYTHON_EXE_PATH" "$APPDIR/usr/bin/python3"

# Copy essential Python stdlib. This is very basic and might miss things.
PYTHON_LIB_PATH=$(python3 -c "import sys; print(sys.path[1])") # Usually /usr/lib/pythonX.Y
# This path might be too broad or miss things if Python installed in non-standard way.
# A more robust way is to copy the Python installation's lib directory.
PYTHON_INSTALL_LIB_DIR=$(python3 -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(plat_specific=0, prefix='/usr'))")

# Copy standard library (e.g., /usr/lib/python3.8)
# This needs to be the specific version, not just a symlink target if /usr/lib/python3 is a symlink
PYTHON_STDLIB_PATH_REAL=$(readlink -f $(python3 -c "import sys; import os; print(os.path.dirname(os.__file__))"))

if [ -d "$PYTHON_STDLIB_PATH_REAL" ]; then
    echo "Copying Python standard library from $PYTHON_STDLIB_PATH_REAL to $APPDIR/usr/lib/python${PYTHON_VERSION_MAJOR_MINOR}"
    # We need the parent of the 'os.py' directory, which is the lib/pythonX.Y folder
    cp -rL "$(dirname "$PYTHON_STDLIB_PATH_REAL")"/* "$APPDIR/usr/lib/python${PYTHON_VERSION_MAJOR_MINOR}/"
else
    echo "Warning: Could not reliably determine Python standard library path: $PYTHON_STDLIB_PATH_REAL. Python might not work correctly."
fi
# Also copy any other necessary Python shared objects (e.g., _ssl.so, _sqlite3.so)
# This part is highly dependent on the Python build and wxPython needs.
# `linuxdeploy --deploy-deps-only` on the AppDir after initial setup can help.

# 5. Copy AppRun, desktop file, and icon
echo "Copying AppRun, desktop file, and icon..."
cp "${PROJECT_DIR}/appimage/AppRun" "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"

cp "${PROJECT_DIR}/appimage/wowusbgui.desktop" "$APPDIR/wowusbgui.desktop"
cp "${PROJECT_DIR}/appimage/wowusbgui.desktop" "$APPDIR/usr/share/applications/" # For menu integration tools

# Use the SVG icon as the primary, AppImage tools might prefer it.
# Also copy the PNG as a fallback or for systems that prefer it.
cp "${PROJECT_DIR}/WowUSB/data/icon.svg" "$APPDIR/wowusbgui.svg"
cp "${PROJECT_DIR}/WowUSB/data/icon.svg" "$APPDIR/usr/share/icons/default/scalable/" # Standard path for SVG
if [ -f "${PROJECT_DIR}/appimage/wowusbgui.png" ]; then
    cp "${PROJECT_DIR}/appimage/wowusbgui.png" "$APPDIR/wowusbgui.png"
fi

# 6. Create symlinks for executables if needed (woeusb, woeusbgui)
# The entry_points from setup.py usually create these when pip installs.
# If we are manually placing our woeusb module, we need to create these.
# For now, assuming AppRun will call `python3 $APPDIR/usr/share/wowusb-ds9/woeusbgui` or similar.
# Based on current AppRun, it expects `woeusbgui` to be in `$APPDIR/usr/bin`
# So, we need to place our launcher scripts there.
# The `scripts` in setup.py are WowUSB/wowusb and WowUSB/woeusbgui.
# These are Python scripts that import and run main functions.
cp "${PROJECT_DIR}/WowUSB/wowusb" "$APPDIR/usr/bin/wowusb"
cp "${PROJECT_DIR}/WowUSB/wowusbgui" "$APPDIR/usr/bin/woeusbgui"
chmod +x "$APPDIR/usr/bin/wowusb"
chmod +x "$APPDIR/usr/bin/woeusbgui"


# 7. Run appimagetool
echo "Running appimagetool..."
# Make sure appimagetool is in PATH or use ./appimagetool
if appimagetool "$APPDIR" "${PROJECT_DIR}/${APPIMAGE_FILENAME}"; then
    echo "AppImage created successfully: ${PROJECT_DIR}/${APPIMAGE_FILENAME}"
else
    echo "Error: appimagetool failed."
    exit 1
fi

# 8. Optional: Clean up AppDir
# read -p "Do you want to remove the AppDir? (y/N): " choice
# if [[ "$choice" == "y" || "$choice" == "Y" ]]; then
#     echo "Removing AppDir: $APPDIR"
#     rm -rf "$APPDIR"
# fi

echo "Build complete."
