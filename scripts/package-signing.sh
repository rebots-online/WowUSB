#!/bin/bash
set -e

PLATFORM=$1

echo "Signing packages for $PLATFORM"

case $PLATFORM in
  linux)
    echo "=== Signing Linux packages ==="

    # Sign AppImage if gpg key is available
    if [ -n "$GPG_SIGNING_KEY" ]; then
        for appimage in *.AppImage; do
            if [ -f "$appimage" ]; then
                echo "Signing $appimage"
                echo "$GPG_SIGNING_KEY" | gpg --import --batch --import
                gpg --output "$appimage.sig" --detach-sign "$appimage"
            fi
        done
    fi

    # Sign deb packages if key is available
    if [ -n "$DEB_SIGNING_KEY" ]; then
        for deb in *.deb; do
            if [ -f "$deb" ]; then
                echo "Signing $deb"
                debsign --re-sign -k "$DEB_SIGNING_KEY" "$deb"
            fi
        done
    fi
    ;;

  windows)
    echo "=== Signing Windows packages ==="

    # PowerShell-based signing for Windows
    if [ -n "$CODESIGN_CERTIFICATE_BASE64" ] && [ -n "$CODESIGN_PASSWORD" ]; then
        echo "Available certificate detected, signing Windows packages..."

        for installer in *.exe *.msi; do
            if [ -f "$installer" ]; then
                echo "Signing $installer"

                # Convert base64 certificate back to file
                echo "$CODESIGN_CERTIFICATE_BASE64" | base64 -d > cert.pfx

                # Sign the installer
                signtool sign /f cert.pfx /p "$CODESIGN_PASSWORD" "$installer"

                # Clean up
                rm cert.pfx
            fi
        done
    else
        echo "No code signing certificates available"
        echo "Set CODESIGN_CERTIFICATE_BASE64 and CODESIGN_PASSWORD secrets to enable Windows code signing"
    fi
    ;;

  *)
    echo "Unsupported platform for signing: $PLATFORM"
    ;;
esac

echo "Package signing completed for $platform"