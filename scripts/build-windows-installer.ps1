param(
    [Parameter(Mandatory=$true)]
    [string]$Platform,
    [Parameter(Mandatory=$true)]
    [string]$Version,
    [Parameter(Mandatory=$true)]
    [ValidateSet('nsis', 'msi')]
    [string]$Type
)

Write-Host "Building $Type installer for $Platform version $Version" -ForegroundColor Green

# Parse version components
$VersionParts = $Version.Split('.')
$MajorVersion = $VersionParts[0].Replace('v', '')
$MinorVersion = $VersionParts[1]
$BuildNumber = $VersionParts[2]

# Ensure 5-digit build number
$BuildNumber = "{0:D5}" -f [int]$BuildNumber

Write-Host "Major: $MajorVersion, Minor: $MinorVersion, Build: $BuildNumber (5 digits)" -ForegroundColor Cyan

$ProgressMessage = "Building $Type installer"
$ProgressStep = 0

function Update-Progress {
    param([string]$Message, [int]$Step = 1)
    $ProgressStep += $Step
    $ProgressPercentage = [math]::Round(($ProgressStep / 6) * 100)
    Write-Progress -Activity $ProgressMessage -Status "Running" -PercentComplete $ProgressPercentage
}

# Function to write progress
function Write-Progress {
    param([string]$Message, [string]$Status, [int]$PercentComplete = 0])
    Write-Host $Message -ForegroundColor $(
        if ($Status -eq "Success") { "Green" }
        elseif ($Status -eq "Running") { "Yellow" }
        elseif ($Status -eq "Error") { "Red" }
        else { "White" }
    ) -NoNewline
}

try {
    Update-Progress "Initializing build environment" 1
    Update-Progress "Loading dependencies" 2

    if ($Type -eq "nsis") {
        Update-Progress "Preparing NSIS installer script" 3
        $NSISScript = @"
!define APP_NAME "WowUSB-DS9"
!define APP_VERSION "${Version}"
!define APP_PUBLISHER "Robin L. M. Cheung, MBA"
!define APP_URL "https://github.com/rebots-online/WowUSB"
!define APP_EXECUTABLE "wowusb-ds9"

!define APP_EXECUTABLE "\$\{APP_EXECUTABLE\}.exe"
!define APP_UNINSTALLER "\$\{APP_EXECUTABLE\}.exe"

!include "MUI2.nsh"
!include "Sections.nsh"

Page directory
!define APP_DIR "C:\Program Files\WowUSB-DS9"
!define APP_START_MENU "$\"Start WowUSB-DS9\""

Request execution level highest
Request execution privileges admin

InstallDirRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" /v1

!ifdef APP_EXECUTABLE
    Exec '"${APP_EXECUTABLE}" "$INSTDIR" "$APP_EXECUTABLE" /REBOOTOK
!endif

!ifdef APP_UNINSTALLER
    Exec '"${APP_UNINSTALLER}" "$INSTDIR" /REBOOTOK
!endif

Section "Uninstall"
Display "Uninstalling WowUSB-DS9" MB_ICON
RMDir "$INSTDIR" /REBOOTOK
DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" /v1 | Out-Null
SectionEnd

Section "Shortcuts"
    WriteIniStr "$INSTDIR\WowUSB-DS9.url" "Internet Shortcut" \
        "URL=$APP_URL" \
        "IconFile=$INSTDIR\WowUSB-DS9.ico"

    CreateShortCut "$DESKTOP\WowUSB-DS9.lnk" \
        "TargetPath=$INSTDIR\wowusb-ds9.exe" \
        "WorkingDirectory=$INSTDIR" \
        "IconLocation=$INSTDIR\WowUSB-8DS9.ico"
SectionEnd

Section "Files"
    WriteIniStr "$INSTDIR\WowUSB-DS9.url" "Internet Shortcut" \
        "URL=$APP_URL" \
        "IconFile=$INSTDIR\WowUSB-DS9.ico"

    SetOutPath "$INSTDIR"
    File "WowUSB-DS9.exe" "${APP_EXECUTABLE}"
SectionEnd
"@
"@

        $NSISScript | Out-File -FilePath "installer.nsi" -Encoding UTF8

        Update-Progress "Compiling NSIS script" 4

        Update-Progress "Creating $Type installer" 5

        # Run makensis
        $Result = & "C:\Program Files (x86)\NSIS\makensis" installer.nsi

        if ($LASTEXITCODE -eq 0) {
            Update-Progress "Installer created successfully" 6
            $InstallerName = "WowUSB-DS9-${Version}-Windows-x64-Setup.exe"

            if (Test-Path $InstallerName) {
                Write-Progress "Success: $InstallerName created" 6
            } else {
                Write-Progress "Error: Installer not found" 6 -Status "Error"
            }
        } else {
            Update-Progress "NSIS compilation failed" 6 -Status "Error"
            Write-Host "Error: NSIS exit code: $LASTEXITCODE" -ForegroundColor Red
        }
    }

    elseif ($Type -eq "msi") {
        Update-Progress "Preparing WiX configuration" 3

        $WiXScript = @"
<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" Name="WowUSB-DS9" Language="1033" Version="${VERSION}" Manufacturer="Robin L. M. Cheung, MBA" UpgradeCode="1">
    <Package InstallerVersion="200" Compressed="yes" InstallScope="perMachine"/>

    <MajorUpgrade DowngradeErrorMessage="A newer version of WowUSB-DS9 is already installed." />
    <MediaTemplate EmbedCab="yes" />

    <Directory Id="TARGETDIR" Name="C:\Program Files\WowUSB-DS9">
      <Directory Id="ProgramFilesFolder" Name="Program Files" ComponentGUID="*">
        <Component Id="ProgramFilesFolder" Guid="*">
          <File Id="WowUSBExe" Name="wowusb-ds9.exe" Source="wowusb-ds9.exe" />
        </Component>
      </Directory>

    <Feature Id="ProductFeature">
      <ComponentRef Id="ProgramFilesFolder" />
    </Feature>

    <ComponentRef Id="ProgramFilesFolder"/>
  </Product>
</Wix>
"@

        $WiXScript | Out-File -FilePath "main.wxs" -Encoding UTF8

        Update-Progress "Compiling WiX project" 4

        # Compile WiX
        $Result = & "C:\Program Files (x86)\WiX Toolset v3.11\candle.exe" main.wxs

        if ($LASTEXITCODE -eq 0) {
            Update-Progress "WiX compiled successfully" 5

            # Link WiX object files
            $Result = & "C:\Program Files (x86)\WiX Toolset v3.11\candle.exe" -o WowUSB-DS9.wixobj main.wxs

            if ($LASTEXITCODE -eq 0) {
                Update-Progress "WiX linking completed" 6
                $InstallerName = "WowUSB-DS9-${VERSION}-Windows-x64.msi"

                # Build the MSI
                $Result = & "C:\Program Files (x86)\WiX Toolset v3.11\candle.exe" WowUSB-DS9.wixobj -out WowUSB-DS9.msi"

                if (Test-Path $InstallerName) {
                    Write-Progress "Success: $InstallerName created" 6
                } else {
                    Write-Progress "Error: MSI not found" 6 -Status "Error"
                }
            } else {
                Update-Progress "WiX linking failed" 5 -Status "Error"
                Write-Host "Error: WiX linking failed - exit code: $LASTEXITCODE" -ForegroundColor Red
            }
        } else {
            Update-Progress "WiX compilation failed" 4 -Status "Error"
            Write-Host "Error: WiX exit code: $LASTEXITCODE" -ForegroundColor Red
        }
    }

    else {
        Write-Progress "Unsupported installer type: $Type" 0 -Status "Error"
        Write-Host "Error: Only 'nsis' and 'msi' installers are supported" -ForegroundColor Red
    }

    Write-Progress "Build process completed" 7 -Status "Success"
}
catch {
    Write-Progress "Build process failed" -Status "Error" -ForegroundColor Red
    Write-Host "Error: $($_. Exception.Message)" -ForegroundColor Red
}

Write-Host "Build process completed for $Platform with version $VERSION" -ForegroundColor Green