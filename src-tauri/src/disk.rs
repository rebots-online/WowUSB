use crate::error::{WowUsbError, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Device {
    pub name: String,
    pub size: String,
    pub model: String,
    pub filesystem: Option<String>,
    pub mountpoint: Option<String>,
    pub is_removable: bool,
    pub is_usb: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartitionConfig {
    pub size_mb: u64,
    pub filesystem: String,
    pub label: String,
    pub bootable: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateConfig {
    pub source_path: String,
    pub target_device: String,
    pub filesystem: String,
    pub drive_label: String,
    pub wintogo_enabled: bool,
    pub multiboot_enabled: bool,
    pub target_os: String,
}

pub trait PlatformDiskOps: Send + Sync {
    async fn list_devices(&self) -> Result<Vec<Device>>;
    async fn verify_device(&self, device: &str) -> Result<bool>;
    async fn create_partitions(&self, device: &str, config: &[PartitionConfig]) -> Result<()>;
    async fn format_partition(&self, partition: &str, filesystem: &str, label: &str) -> Result<()>;
    async fn mount_partition(&self, partition: &str, mountpoint: &str) -> Result<String>;
    async fn unmount_partition(&self, mountpoint: &str) -> Result<()>;
    async fn wipe_device(&self, device: &str) -> Result<()>;
    async fn validate_iso(&self, iso_path: &str) -> Result<bool>;
    async fn extract_iso(&self, iso_path: &str, target_path: &str) -> Result<()>;
    async fn install_bootloader(&self, device: &str, bootloader_type: &str) -> Result<()>;
}

#[cfg(target_os = "windows")]
mod windows;

#[cfg(target_os = "windows")]
use self::windows::WindowsDiskOps;

#[cfg(target_os = "linux")]
mod linux;

#[cfg(target_os = "linux")]
use self::linux::LinuxDiskOps;

#[cfg(target_os = "macos")]
mod macos;

#[cfg(target_os = "macos")]
use self::macos::MacOSDiskOps;

pub struct DiskManager {
    ops: Box<dyn PlatformDiskOps>,
}

impl DiskManager {
    pub fn new() -> Self {
        #[cfg(target_os = "windows")]
        let ops = Box::new(WindowsDiskOps::new());

        #[cfg(target_os = "linux")]
        let ops = Box::new(LinuxDiskOps::new());

        #[cfg(target_os = "macos")]
        let ops = Box::new(MacOSDiskOps::new());

        Self { ops }
    }

    pub async fn list_devices(&self) -> Result<Vec<Device>> {
        self.ops.list_devices().await
    }

    pub async fn verify_device(&self, device: &str) -> Result<bool> {
        self.ops.verify_device(device).await
    }

    pub async fn create_bootable_usb(&self, source_path: &str, target_device: &str, config: &CreateConfig) -> Result<String> {
        // Step 1: Validate inputs
        if source_path.is_empty() {
            return Err(WowUsbError::validation("Source path cannot be empty"));
        }
        if target_device.is_empty() {
            return Err(WowUsbError::validation("Target device cannot be empty"));
        }

        // Step 2: Validate ISO
        let is_valid_iso = self.ops.validate_iso(source_path).await?;
        if !is_valid_iso {
            return Err(WowUsbError::validation("Invalid or corrupted ISO file"));
        }

        // Step 3: Verify target device
        let is_valid_device = self.ops.verify_device(target_device).await?;
        if !is_valid_device {
            return Err(WowUsbError::validation("Invalid target device"));
        }

        // Step 4: Create partitions based on configuration
        let partitions = self.create_partition_config(config)?;
        self.ops.create_partitions(target_device, &partitions).await?;

        // Step 5: Format the main partition
        let main_partition = self.get_main_partition(target_device);
        self.ops.format_partition(&main_partition, &config.filesystem, &config.drive_label).await?;

        // Step 6: Mount and copy files
        let mountpoint = format!("/tmp/wowusb_mount_{}", std::process::id());
        std::fs::create_dir_all(&mountpoint)?;

        let actual_mountpoint = self.ops.mount_partition(&main_partition, &mountpoint).await?;
        self.ops.extract_iso(source_path, &actual_mountpoint).await?;

        // Step 7: Install bootloader
        self.ops.install_bootloader(target_device, "grub2").await?;

        // Step 8: Cleanup
        self.ops.unmount_partition(&actual_mountpoint).await?;
        std::fs::remove_dir(&mountpoint)?;

        Ok(format!("Successfully created bootable USB on {}", target_device))
    }

    fn create_partition_config(&self, config: &CreateConfig) -> Result<Vec<PartitionConfig>> {
        let mut partitions = Vec::new();

        if config.multiboot_enabled {
            // Multiboot layout: ESP, BIOS_GRUB, Windows, Payload
            partitions.push(PartitionConfig {
                size_mb: 512,
                filesystem: "fat32".to_string(),
                label: "EFI".to_string(),
                bootable: true,
            });

            partitions.push(PartitionConfig {
                size_mb: 1,
                filesystem: "bios_grub".to_string(),
                label: "BIOS_GRUB".to_string(),
                bootable: false,
            });

            partitions.push(PartitionConfig {
                size_mb: 64000, // 64GB for Windows
                filesystem: "ntfs".to_string(),
                label: "Windows".to_string(),
                bootable: false,
            });
        } else {
            // Standard single partition
            partitions.push(PartitionConfig {
                size_mb: 0, // Use remaining space
                filesystem: config.filesystem.clone(),
                label: config.drive_label.clone(),
                bootable: true,
            });
        }

        Ok(partitions)
    }

    fn get_main_partition(&self, device: &str) -> String {
        // This is a simplified version - in practice, this would be more sophisticated
        if device.ends_with("0") || !device.chars().last().unwrap().is_numeric() {
            format!("{}1", device)
        } else {
            device.to_string()
        }
    }

    pub async fn validate_iso(&self, iso_path: &str) -> Result<bool> {
        self.ops.validate_iso(iso_path).await
    }
}

// Platform implementations will go here
// For now, I'll create stub implementations