use crate::disk::{Device, PartitionConfig, PlatformDiskOps};
use crate::error::{WowUsbError, Result};
use std::process::Command;
use std::path::Path;
use tokio::process::Command as AsyncCommand;

pub struct MacOSDiskOps;

impl MacOSDiskOps {
    pub fn new() -> Self {
        Self
    }
}

impl PlatformDiskOps for MacOSDiskOps {
    async fn list_devices(&self) -> Result<Vec<Device>> {
        let output = AsyncCommand::new("diskutil")
            .args(&["list", "-external", "-physical"])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::device_operation(
                format!("diskutil failed: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        let output_str = String::from_utf8(output.stdout)?;
        let mut devices = Vec::new();

        for line in output_str.lines() {
            if line.trim().starts_with("/dev/disk") {
                let device_path = line.trim().to_string();

                // Get detailed information
                if let Ok(device_info) = self.get_device_info(&device_path).await {
                    devices.push(device_info);
                }
            }
        }

        Ok(devices)
    }

    async fn verify_device(&self, device: &str) -> Result<bool> {
        let output = AsyncCommand::new("diskutil")
            .args(&["info", device])
            .output()
            .await?;

        Ok(output.status.success())
    }

    async fn create_partitions(&self, device: &str, config: &[PartitionConfig]) -> Result<()> {
        // First, unmount the disk
        let output = AsyncCommand::new("diskutil")
            .args(&["unmountDisk", "force", device])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::device_operation(
                format!("Failed to unmount disk: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        // Partition the disk
        let mut partition_args = vec!["partitionDisk".to_string(), device.to_string()];

        for (index, partition) in config.iter().enumerate() {
            let partition_spec = if partition.size_mb == 0 {
                format!("0:{}", partition.filesystem)
            } else {
                format!("{}GB:{}", partition.size_mb / 1024, partition.filesystem)
            };

            partition_args.push(partition_spec);
        }

        let output = AsyncCommand::new("diskutil")
            .args(&partition_args)
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::device_operation(
                format!("Failed to partition disk: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        Ok(())
    }

    async fn format_partition(&self, partition: &str, filesystem: &str, label: &str) -> Result<()> {
        let format_args = match filesystem {
            "fat32" => vec!["eraseVolume", "FAT32", partition, "--name", label],
            "ntfs" => vec!["eraseVolume", "NTFS", partition, "--name", label],
            "exfat" => vec!["eraseVolume", "ExFAT", partition, "--name", label],
            "apfs" => vec!["eraseVolume", "APFS", partition, "--name", label],
            _ => {
                return Err(WowUsbError::filesystem(
                    format!("Unsupported filesystem: {}", filesystem)
                ));
            }
        };

        let output = AsyncCommand::new("diskutil")
            .args(&format_args)
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::filesystem(
                format!("Failed to format partition: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        Ok(())
    }

    async fn mount_partition(&self, partition: &str, mountpoint: &str) -> Result<String> {
        std::fs::create_dir_all(mountpoint)?;

        let output = AsyncCommand::new("diskutil")
            .args(&["mount", "-mountPoint", mountpoint, partition])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::device_operation(
                format!("Failed to mount partition: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        Ok(mountpoint.to_string())
    }

    async fn unmount_partition(&self, mountpoint: &str) -> Result<()> {
        let output = AsyncCommand::new("diskutil")
            .args(&["unmount", mountpoint])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::device_operation(
                format!("Failed to unmount partition: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        Ok(())
    }

    async fn wipe_device(&self, device: &str) -> Result<()> {
        let output = AsyncCommand::new("diskutil")
            .args(&["zeroDisk", device])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::device_operation(
                format!("Failed to wipe disk: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        Ok(())
    }

    async fn validate_iso(&self, iso_path: &str) -> Result<bool> {
        let output = AsyncCommand::new("hdiutil")
            .args(&["attach", "-readonly", "-noverify", iso_path])
            .output()
            .await?;

        if output.status.success() {
            // Detach the image
            let output_str = String::from_utf8(output.stdout)?;
            if let Some(line) = output_str.lines().next() {
                let mount_info = line.trim();
                if mount_info.starts_with("/dev/") {
                    let output = AsyncCommand::new("hdiutil")
                        .args(&["detach", mount_info])
                        .output()
                        .await?;
                }
            }
            Ok(true)
        } else {
            Ok(false)
        }
    }

    async fn extract_iso(&self, iso_path: &str, target_path: &str) -> Result<()> {
        // Mount the ISO
        let output = AsyncCommand::new("hdiutil")
            .args(&["attach", iso_path])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::iso_processing(
                format!("Failed to mount ISO: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        // Get mount point
        let output_str = String::from_utf8(output.stdout)?;
        let mount_point = output_str
            .lines()
            .find(|line| line.trim().starts_with("/Volumes/"))
            .and_then(|line| line.split_whitespace().last());

        if let Some(mount_point) = mount_point {
            // Copy files
            let output = AsyncCommand::new("cp")
                .args(&["-R", mount_point, target_path])
                .output()
                .await?;

            if !output.status.success() {
                return Err(WowUsbError::iso_processing(
                    format!("Failed to copy files: {}", String::from_utf8_lossy(&output.stderr))
                ));
            }

            // Unmount the ISO
            let output = AsyncCommand::new("hdiutil")
                .args(&["detach", mount_point])
                .output()
                .await?;

            if !output.status.success() {
                return Err(WowUsbError::iso_processing(
                    format!("Failed to unmount ISO: {}", String::from_utf8_lossy(&output.stderr))
                ));
            }
        }

        Ok(())
    }

    async fn install_bootloader(&self, device: &str, bootloader_type: &str) -> Result<()> {
        match bootloader_type {
            "grub2" => {
                return Err(WowUsbError::not_implemented(
                    "GRUB installation on macOS not yet implemented"
                ));
            }
            _ => {
                return Err(WowUsbError::not_implemented(
                    format!("Bootloader type not supported: {}", bootloader_type)
                ));
            }
        }
    }
}

impl MacOSDiskOps {
    async fn get_device_info(&self, device: &str) -> Result<Device> {
        let output = AsyncCommand::new("diskutil")
            .args(&["info", device])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::device_operation(
                format!("Failed to get device info: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        let output_str = String::from_utf8(output.stdout)?;
        let mut model = "Unknown".to_string();
        let mut size = "Unknown".to_string();
        let mut is_removable = false;
        let mut is_usb = false;

        for line in output_str.lines() {
            if line.contains("Device Node:") {
                // Device name is already known
            } else if line.contains("Device / Media Name:") {
                model = line.split(':').nth(1).unwrap_or("Unknown").trim().to_string();
            } else if line.contains("Total Size:") {
                size = line.split(':').nth(1).unwrap_or("Unknown").trim().to_string();
            } else if line.contains("External") {
                is_removable = true;
            } else if line.contains("USB") {
                is_usb = true;
            }
        }

        Ok(Device {
            name: device.to_string(),
            size,
            model,
            filesystem: None,
            mountpoint: None,
            is_removable,
            is_usb,
        })
    }
}