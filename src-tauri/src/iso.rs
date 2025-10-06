use crate::error::{WowUsbError, Result};
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IsoInfo {
    pub path: String,
    pub size: u64,
    pub os_type: String,
    pub version: Option<String>,
    pub architecture: Option<String>,
    pub has_large_files: bool,
    pub bootable: bool,
    pub supports_uefi: bool,
    pub supports_legacy: bool,
}

pub struct IsoProcessor {
    temp_dir: String,
}

impl IsoProcessor {
    pub fn new() -> Self {
        let temp_dir = format!("/tmp/wowusb_iso_{}", std::process::id());
        Self { temp_dir }
    }

    pub async fn analyze_iso(&self, iso_path: &str) -> Result<IsoInfo> {
        let path = Path::new(iso_path);

        if !path.exists() {
            return Err(WowUsbError::validation("ISO file does not exist"));
        }

        // Get file size
        let metadata = std::fs::metadata(path)?;
        let size = metadata.len();

        // Analyze ISO content
        let os_type = self.detect_os_type(iso_path).await?;
        let version = self.extract_version(iso_path, &os_type).await?;
        let architecture = self.detect_architecture(iso_path).await?;
        let has_large_files = self.check_for_large_files(iso_path).await?;
        let (supports_uefi, supports_legacy) = self.check_boot_support(iso_path).await?;

        Ok(IsoInfo {
            path: iso_path.to_string(),
            size,
            os_type,
            version,
            architecture,
            has_large_files,
            bootable: supports_uefi || supports_legacy,
            supports_uefi,
            supports_legacy,
        })
    }

    async fn detect_os_type(&self, iso_path: &str) -> Result<String> {
        // Use 7z to list contents and analyze
        let output = tokio::process::Command::new("7z")
            .args(&["l", iso_path])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::iso_processing(
                format!("Failed to list ISO contents: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        let contents = String::from_utf8(output.stdout)?;
        let contents_lower = contents.to_lowercase();

        // Detect OS type based on file patterns
        if contents_lower.contains("windows") || contents_lower.contains("sources/install.wim") || contents_lower.contains("sources/install.esd") {
            Ok("Windows".to_string())
        } else if contents_lower.contains("ubuntu") || contents_lower.contains("debian") || contents_lower.contains("linux") {
            // More specific detection
            if contents_lower.contains("ubuntu") {
                Ok("Ubuntu".to_string())
            } else if contents_lower.contains("debian") {
                Ok("Debian".to_string())
            } else if contents_lower.contains("fedora") {
                Ok("Fedora".to_string())
            } else if contents_lower.contains("arch") {
                Ok("Arch Linux".to_string())
            } else {
                Ok("Linux".to_string())
            }
        } else if contents_lower.contains("install") {
            Ok("Unknown (but likely bootable)".to_string())
        } else {
            Ok("Unknown".to_string())
        }
    }

    async fn extract_version(&self, iso_path: &str, os_type: &str) -> Result<Option<String>> {
        match os_type {
            "Windows" => self.extract_windows_version(iso_path).await,
            "Ubuntu" => self.extract_ubuntu_version(iso_path).await,
            "Debian" => self.extract_debian_version(iso_path).await,
            _ => Ok(None),
        }
    }

    async fn extract_windows_version(&self, iso_path: &str) -> Result<Option<String>> {
        // For Windows, we can extract from sources/idwbinfo.txt or similar files
        let output = tokio::process::Command::new("7z")
            .args(&["e", iso_path, "sources/idwbinfo.txt", "-so"])
            .output()
            .await?;

        if output.status.success() {
            let content = String::from_utf8(output.stdout)?;
            // Parse Windows version from idwbinfo.txt
            for line in content.lines() {
                if line.contains("Version") || line.contains("Build") {
                    return Ok(Some(line.trim().to_string()));
                }
            }
        }

        Ok(None)
    }

    async fn extract_ubuntu_version(&self, iso_path: &str) -> Result<Option<String>> {
        // For Ubuntu, check .disk/info or casper/vmlinuz version info
        let output = tokio::process::Command::new("7z")
            .args(&["e", iso_path, ".disk/info", "-so"])
            .output()
            .await?;

        if output.status.success() {
            let content = String::from_utf8(output.stdout)?;
            return Ok(Some(content.trim().to_string()));
        }

        Ok(None)
    }

    async fn extract_debian_version(&self, _iso_path: &str) -> Result<Option<String>> {
        // For Debian, check .disk/info or release files
        Ok(None)
    }

    async fn detect_architecture(&self, iso_path: &str) -> Result<Option<String>> {
        // Check for architecture-specific files
        let output = tokio::process::Command::new("7z")
            .args(&["l", iso_path])
            .output()
            .await?;

        if !output.status.success() {
            return Ok(None);
        }

        let contents = String::from_utf8(output.stdout)?;
        let contents_lower = contents.to_lowercase();

        if contents_lower.contains("x64") || contents_lower.contains("amd64") {
            Ok(Some("x86_64".to_string()))
        } else if contents_lower.contains("x86") || contents_lower.contains("i386") {
            Ok(Some("i386".to_string()))
        } else if contents_lower.contains("arm64") || contents_lower.contains("aarch64") {
            Ok(Some("aarch64".to_string()))
        } else if contents_lower.contains("arm") {
            Ok(Some("ARM".to_string()))
        } else {
            Ok(None)
        }
    }

    async fn check_for_large_files(&self, iso_path: &str) -> Result<bool> {
        let output = tokio::process::Command::new("7z")
            .args(&["l", iso_path])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::iso_processing(
                format!("Failed to list ISO contents: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        let contents = String::from_utf8(output.stdout)?;
        const FOUR_GB: u64 = 4 * 1024 * 1024 * 1024;

        for line in contents.lines() {
            if line.trim().is_empty() || line.starts_with('-') {
                continue;
            }

            // Parse file size (this is a simplified parser)
            let parts: Vec<&str> = line.split_whitespace().collect();
            if parts.len() >= 4 {
                let size_str = parts[3];
                if let Ok(size_bytes) = self.parse_size_string(size_str) {
                    if size_bytes > FOUR_GB {
                        return Ok(true);
                    }
                }
            }
        }

        Ok(false)
    }

    async fn check_boot_support(&self, iso_path: &str) -> Result<(bool, bool)> {
        let output = tokio::process::Command::new("7z")
            .args(&["l", iso_path])
            .output()
            .await?;

        if !output.status.success() {
            return Ok((false, false));
        }

        let contents = String::from_utf8(output.stdout)?;
        let contents_lower = contents.to_lowercase();

        let supports_uefi = contents_lower.contains("efi") ||
                          contents_lower.contains("boot") ||
                          contents_lower.contains("efi/boot");

        let supports_legacy = contents_lower.contains("boot") ||
                             contents_lower.contains("syslinux") ||
                             contents_lower.contains("grub");

        Ok((supports_uefi, supports_legacy))
    }

    fn parse_size_string(&self, size_str: &str) -> Result<u64> {
        // Parse size strings like "123456789", "123M", "1.2G", etc.
        let size_str = size_str.trim().to_uppercase();

        if size_str.ends_with('G') {
            let numeric_part = &size_str[..size_str.len() - 1];
            let size_gb: f64 = numeric_part.parse()
                .map_err(|_| WowUsbError::validation(format!("Invalid size format: {}", size_str)))?;
            Ok((size_gb * 1024.0 * 1024.0 * 1024.0) as u64)
        } else if size_str.ends_with('M') {
            let numeric_part = &size_str[..size_str.len() - 1];
            let size_mb: f64 = numeric_part.parse()
                .map_err(|_| WowUsbError::validation(format!("Invalid size format: {}", size_str)))?;
            Ok((size_mb * 1024.0 * 1024.0) as u64)
        } else if size_str.ends_with('K') {
            let numeric_part = &size_str[..size_str.len() - 1];
            let size_kb: f64 = numeric_part.parse()
                .map_err(|_| WowUsbError::validation(format!("Invalid size format: {}", size_str)))?;
            Ok((size_kb * 1024.0) as u64)
        } else {
            // Assume bytes
            size_str.parse::<u64>()
                .map_err(|_| WowUsbError::validation(format!("Invalid size format: {}", size_str)))
        }
    }

    pub async fn validate_iso_for_target(&self, iso_info: &IsoInfo, target_os: &str) -> Result<bool> {
        match (iso_info.os_type.as_str(), target_os.to_lowercase().as_str()) {
            ("Windows", "linux") | ("Windows", "windows") => Ok(true),
            ("Ubuntu" | "Debian" | "Fedora" | "Arch Linux" | "Linux", "linux") => Ok(true),
            _ => Ok(false), // Mismatched OS types
        }
    }

    pub async fn get_recommended_filesystem(&self, iso_info: &IsoInfo) -> Result<String> {
        if iso_info.os_type == "Windows" {
            if iso_info.has_large_files {
                Ok("NTFS".to_string())
            } else {
                Ok("FAT32".to_string())
            }
        } else {
            // For Linux distributions
            if iso_info.has_large_files {
                Ok("F2FS".to_string())
            } else {
                Ok("FAT32".to_string())
            }
        }
    }
}

impl Default for IsoProcessor {
    fn default() -> Self {
        Self::new()
    }
}