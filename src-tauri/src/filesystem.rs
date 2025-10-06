use crate::error::{WowUsbError, Result};
use std::collections::HashMap;

pub trait PlatformFilesystemOps: Send + Sync {
    fn get_available_filesystems(&self) -> Result<Vec<String>>;
    fn check_filesystem_support(&self, fs_type: &str) -> Result<bool>;
    fn get_filesystem_info(&self, fs_type: &str) -> Result<FilesystemInfo>;
    fn get_optimal_filesystem(&self, has_large_files: bool, target_os: &str) -> Result<String>;
}

#[derive(Debug, Clone)]
pub struct FilesystemInfo {
    pub name: String,
    pub supports_large_files: bool,
    pub max_file_size: u64,
    pub max_volume_size: u64,
    pub recommended_for: Vec<String>,
    pros: Vec<String>,
    cons: Vec<String>,
}

pub struct FilesystemManager {
    ops: Box<dyn PlatformFilesystemOps>,
    filesystem_cache: std::sync::Mutex<HashMap<String, FilesystemInfo>>,
}

impl FilesystemManager {
    pub fn new() -> Self {
        #[cfg(target_os = "windows")]
        let ops = Box::new(crate::filesystem::windows::WindowsFilesystemOps::new());

        #[cfg(target_os = "linux")]
        let ops = Box::new(crate::filesystem::linux::LinuxFilesystemOps::new());

        #[cfg(target_os = "macos")]
        let ops = Box::new(crate::filesystem::macos::MacOSFilesystemOps::new());

        Self {
            ops,
            filesystem_cache: std::sync::Mutex::new(HashMap::new()),
        }
    }

    pub fn get_available_filesystems(&self) -> Result<Vec<String>> {
        self.ops.get_available_filesystems()
    }

    pub fn check_filesystem_support(&self, fs_type: &str) -> Result<bool> {
        self.ops.check_filesystem_support(fs_type)
    }

    pub fn get_filesystem_info(&self, fs_type: &str) -> Result<FilesystemInfo> {
        // Check cache first
        {
            let cache = self.filesystem_cache.lock().unwrap();
            if let Some(info) = cache.get(fs_type) {
                return Ok(info.clone());
            }
        }

        // Get from backend
        let info = self.ops.get_filesystem_info(fs_type)?;

        // Cache the result
        {
            let mut cache = self.filesystem_cache.lock().unwrap();
            cache.insert(fs_type.to_string(), info.clone());
        }

        Ok(info)
    }

    pub fn get_optimal_filesystem(&self, has_large_files: bool, target_os: &str) -> Result<String> {
        self.ops.get_optimal_filesystem(has_large_files, target_os)
    }

    pub fn format_size_bytes(&self, bytes: u64) -> String {
        const UNITS: &[&str] = &["B", "KB", "MB", "GB", "TB"];
        let mut size = bytes as f64;
        let mut unit_index = 0;

        while size >= 1024.0 && unit_index < UNITS.len() - 1 {
            size /= 1024.0;
            unit_index += 1;
        }

        if unit_index == 0 {
            format!("{} {}", bytes, UNITS[unit_index])
        } else {
            format!("{:.1} {}", size, UNITS[unit_index])
        }
    }
}

// Platform implementations
#[cfg(target_os = "windows")]
pub mod windows {
    use super::*;

    pub struct WindowsFilesystemOps;

    impl WindowsFilesystemOps {
        pub fn new() -> Self {
            Self
        }
    }

    impl PlatformFilesystemOps for WindowsFilesystemOps {
        fn get_available_filesystems(&self) -> Result<Vec<String>> {
            Ok(vec![
                "NTFS".to_string(),
                "FAT32".to_string(),
                "exFAT".to_string(),
            ])
        }

        fn check_filesystem_support(&self, fs_type: &str) -> Result<bool> {
            match fs_type.to_lowercase().as_str() {
                "ntfs" | "fat32" | "exfat" => Ok(true),
                _ => Ok(false),
            }
        }

        fn get_filesystem_info(&self, fs_type: &str) -> Result<FilesystemInfo> {
            match fs_type.to_lowercase().as_str() {
                "ntfs" => Ok(FilesystemInfo {
                    name: "NTFS".to_string(),
                    supports_large_files: true,
                    max_file_size: 16 * 1024 * 1024 * 1024 * 1024, // 16TB
                    max_volume_size: 256 * 1024 * 1024 * 1024 * 1024, // 256TB
                    recommended_for: vec!["Windows".to_string(), "Large files".to_string()],
                    pros: vec![
                        "Excellent large file support".to_string(),
                        "Built-in Windows support".to_string(),
                        "Journaling filesystem".to_string(),
                        "Compression support".to_string(),
                    ],
                    cons: vec![
                        "Limited compatibility with other OS".to_string(),
                        "Performance overhead on small files".to_string(),
                    ],
                }),
                "fat32" => Ok(FilesystemInfo {
                    name: "FAT32".to_string(),
                    supports_large_files: false,
                    max_file_size: 4 * 1024 * 1024 * 1024 - 1, // 4GB - 1 byte
                    max_volume_size: 2 * 1024 * 1024 * 1024, // 2TB
                    recommended_for: vec!["Maximum compatibility".to_string()],
                    pros: vec![
                        "Universal compatibility".to_string(),
                        "Simple and reliable".to_string(),
                        "Works on virtually all systems".to_string(),
                    ],
                    cons: vec![
                        "4GB file size limit".to_string(),
                        "No journaling".to_string(),
                        "Inefficient with large volumes".to_string(),
                    ],
                }),
                "exfat" => Ok(FilesystemInfo {
                    name: "exFAT".to_string(),
                    supports_large_files: true,
                    max_file_size: 128 * 1024 * 1024 * 1024 * 1024, // 128EB (theoretical)
                    max_volume_size: 128 * 1024 * 1024 * 1024 * 1024, // 128EB
                    recommended_for: vec!["Cross-platform".to_string(), "Flash drives".to_string()],
                    pros: vec![
                        "Large file support".to_string(),
                        "Good cross-platform support".to_string(),
                        "Optimized for flash media".to_string(),
                    ],
                    cons: vec![
                        "Less robust than NTFS".to_string(),
                        "No journaling".to_string(),
                    ],
                }),
                _ => Err(WowUsbError::filesystem(
                    format!("Unknown filesystem: {}", fs_type)
                )),
            }
        }

        fn get_optimal_filesystem(&self, has_large_files: bool, target_os: &str) -> Result<String> {
            if target_os.to_lowercase() == "windows" {
                Ok("NTFS".to_string())
            } else if has_large_files {
                Ok("exFAT".to_string())
            } else {
                Ok("FAT32".to_string())
            }
        }
    }
}

#[cfg(target_os = "linux")]
pub mod linux {
    use super::*;

    pub struct LinuxFilesystemOps;

    impl LinuxFilesystemOps {
        pub fn new() -> Self {
            Self
        }
    }

    impl PlatformFilesystemOps for LinuxFilesystemOps {
        fn get_available_filesystems(&self) -> Result<Vec<String>> {
            let mut filesystems = vec![
                "FAT32".to_string(),
                "NTFS".to_string(),
                "exFAT".to_string(),
                "ext4".to_string(),
            ];

            // Check for additional filesystems
            if std::path::Path::new("/sbin/mkfs.f2fs").exists() {
                filesystems.push("F2FS".to_string());
            }

            if std::path::Path::new("/sbin/mkfs.btrfs").exists() {
                filesystems.push("BTRFS".to_string());
            }

            Ok(filesystems)
        }

        fn check_filesystem_support(&self, fs_type: &str) -> Result<bool> {
            let mkfs_command = match fs_type.to_lowercase().as_str() {
                "fat32" => "mkfs.fat",
                "ntfs" => "mkfs.ntfs",
                "exfat" => "mkfs.exfat",
                "ext4" => "mkfs.ext4",
                "f2fs" => "mkfs.f2fs",
                "btrfs" => "mkfs.btrfs",
                _ => return Ok(false),
            };

            Ok(std::path::Path::new(&format!("/sbin/{}", mkfs_command)).exists())
        }

        fn get_filesystem_info(&self, fs_type: &str) -> Result<FilesystemInfo> {
            match fs_type.to_lowercase().as_str() {
                "f2fs" => Ok(FilesystemInfo {
                    name: "F2FS".to_string(),
                    supports_large_files: true,
                    max_file_size: 16 * 1024 * 1024 * 1024 * 1024, // 16TB
                    max_volume_size: 16 * 1024 * 1024 * 1024 * 1024, // 16TB
                    recommended_for: vec!["Flash drives".to_string(), "SSD".to_string(), "Linux".to_string()],
                    pros: vec![
                        "Optimized for flash memory".to_string(),
                        "Excellent performance".to_string(),
                        "Large file support".to_string(),
                    ],
                    cons: vec![
                        "Limited Windows support".to_string(),
                        "Relatively new filesystem".to_string(),
                    ],
                }),
                "btrfs" => Ok(FilesystemInfo {
                    name: "BTRFS".to_string(),
                    supports_large_files: true,
                    max_file_size: 16 * 1024 * 1024 * 1024 * 1024, // 16EB
                    max_volume_size: 16 * 1024 * 1024 * 1024 * 1024, // 16EB
                    recommended_for: vec!["Advanced features".to_string(), "Linux".to_string()],
                    pros: vec![
                        "Copy-on-write".to_string(),
                        "Snapshots".to_string(),
                        "Self-healing".to_string(),
                        "Built-in compression".to_string(),
                    ],
                    cons: vec![
                        "Complex implementation".to_string(),
                        "Performance overhead".to_string(),
                    ],
                }),
                "ext4" => Ok(FilesystemInfo {
                    name: "ext4".to_string(),
                    supports_large_files: true,
                    max_file_size: 16 * 1024 * 1024 * 1024 * 1024, // 16TB
                    max_volume_size: 1 * 1024 * 1024 * 1024 * 1024, // 1EB
                    recommended_for: vec!["Linux".to_string(), "Reliability".to_string()],
                    pros: vec![
                        "Mature and stable".to_string(),
                        "Good performance".to_string(),
                        "Journaling filesystem".to_string(),
                    ],
                    cons: vec![
                        "Limited Windows support".to_string(),
                    ],
                }),
                // Add other filesystems (NTFS, FAT32, exFAT) from Windows implementation
                _ => {
                    // Delegate to common implementations for cross-platform filesystems
                    let windows_ops = super::windows::WindowsFilesystemOps::new();
                    windows_ops.get_filesystem_info(fs_type)
                }
            }
        }

        fn get_optimal_filesystem(&self, has_large_files: bool, target_os: &str) -> Result<String> {
            match target_os.to_lowercase().as_str() {
                "windows" => Ok("NTFS".to_string()),
                "linux" => {
                    if has_large_files {
                        // Check for F2FS first, then fallback to others
                        if self.check_filesystem_support("F2FS").unwrap_or(false) {
                            Ok("F2FS".to_string())
                        } else if self.check_filesystem_support("NTFS").unwrap_or(false) {
                            Ok("NTFS".to_string())
                        } else {
                            Ok("FAT32".to_string())
                        }
                    } else {
                        Ok("FAT32".to_string())
                    }
                },
                _ => Ok("FAT32".to_string()),
            }
        }
    }
}

#[cfg(target_os = "macos")]
pub mod macos {
    use super::*;

    pub struct MacOSFilesystemOps;

    impl MacOSFilesystemOps {
        pub fn new() -> Self {
            Self
        }
    }

    impl PlatformFilesystemOps for MacOSFilesystemOps {
        fn get_available_filesystems(&self) -> Result<Vec<String>> {
            Ok(vec![
                "FAT32".to_string(),
                "exFAT".to_string(),
                "APFS".to_string(),
            ])
        }

        fn check_filesystem_support(&self, fs_type: &str) -> Result<bool> {
            match fs_type.to_lowercase().as_str() {
                "fat32" | "exfat" | "apfs" => Ok(true),
                _ => Ok(false),
            }
        }

        fn get_filesystem_info(&self, fs_type: &str) -> Result<FilesystemInfo> {
            match fs_type.to_lowercase().as_str() {
                "apfs" => Ok(FilesystemInfo {
                    name: "APFS".to_string(),
                    supports_large_files: true,
                    max_file_size: 8 * 1024 * 1024 * 1024 * 1024, // 8EB
                    max_volume_size: 8 * 1024 * 1024 * 1024 * 1024, // 8EB
                    recommended_for: vec!["macOS".to_string(), "Modern features".to_string()],
                    pros: vec![
                        "Native macOS support".to_string(),
                        "Snapshots and clones".to_string(),
                        "Strong encryption".to_string(),
                        "Space sharing".to_string(),
                    ],
                    cons: vec![
                        "Limited cross-platform support".to_string(),
                        "Apple ecosystem only".to_string(),
                    ],
                }),
                // Add other filesystems (FAT32, exFAT) from Windows implementation
                _ => {
                    let windows_ops = super::windows::WindowsFilesystemOps::new();
                    windows_ops.get_filesystem_info(fs_type)
                }
            }
        }

        fn get_optimal_filesystem(&self, has_large_files: bool, target_os: &str) -> Result<String> {
            match target_os.to_lowercase().as_str() {
                "macos" => Ok("APFS".to_string()),
                _ => {
                    if has_large_files {
                        Ok("exFAT".to_string())
                    } else {
                        Ok("FAT32".to_string())
                    }
                }
            }
        }
    }
}