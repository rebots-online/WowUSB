use crate::disk::{Device, PartitionConfig, PlatformDiskOps};
use crate::error::{WowUsbError, Result};
use std::process::Command;
use std::path::Path;
use tokio::process::Command as AsyncCommand;

pub struct LinuxDiskOps {
    temp_dir: String,
}

impl LinuxDiskOps {
    pub fn new() -> Self {
        let temp_dir = format!("/tmp/wowusb_{}", std::process::id());
        Self { temp_dir }
    }
}

impl PlatformDiskOps for LinuxDiskOps {
    async fn list_devices(&self) -> Result<Vec<Device>> {
        let output = AsyncCommand::new("lsblk")
            .args(&["-J", "-o", "NAME,SIZE,MODEL,FSTYPE,MOUNTPOINT,TYPE,MOUNTPOINT"])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::device_operation(
                format!("lsblk failed: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        let json_str = String::from_utf8(output.stdout)?;
        let lsblk_output: serde_json::Value = serde_json::from_str(&json_str)?;

        let mut devices = Vec::new();

        if let Some(blockdevices) = lsblk_output.get("blockdevices").and_then(|v| v.as_array()) {
            for device in blockdevices {
                if let (Some(name), Some(size)) = (
                    device.get("name").and_then(|v| v.as_str()),
                    device.get("size").and_then(|v| v.as_str())
                ) {
                    // Skip system disks and internal devices that aren't removable
                    let device_path = format!("/dev/{}", name);
                    if self.is_removable_device(&device_path).await? || name.starts_with("sd") {
                        let model = device.get("model")
                            .and_then(|v| v.as_str())
                            .unwrap_or("Unknown")
                            .to_string();

                        let filesystem = device.get("fstype")
                            .and_then(|v| v.as_str())
                            .map(|s| s.to_string());

                        let mountpoint = device.get("mountpoint")
                            .and_then(|v| v.as_str())
                            .filter(|s| !s.is_empty())
                            .map(|s| s.to_string());

                        let is_removable = self.is_removable_device(&device_path).await?;
                        let is_usb = name.starts_with("sd") && is_removable;

                        devices.push(Device {
                            name: device_path,
                            size: size.to_string(),
                            model,
                            filesystem,
                            mountpoint,
                            is_removable,
                            is_usb,
                        });
                    }
                }
            }
        }

        Ok(devices)
    }

    async fn verify_device(&self, device: &str) -> Result<bool> {
        let path = Path::new(device);
        if !path.exists() {
            return Ok(false);
        }

        // Check if it's a block device
        let output = AsyncCommand::new("stat")
            .args(&["-c", "%F", device])
            .output()
            .await?;

        if !output.status.success() {
            return Ok(false);
        }

        let file_type = String::from_utf8(output.stdout)?;
        Ok(file_type.trim() == "block special file")
    }

    async fn create_partitions(&self, device: &str, config: &[PartitionConfig]) -> Result<()> {
        // Create partition table
        let output = AsyncCommand::new("parted")
            .args(&["--script", device, "mklabel", "gpt"])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::device_operation(
                format!("Failed to create GPT partition table: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        // Create partitions
        let mut current_start = 1; // Start at 1MB
        for (index, partition) in config.iter().enumerate() {
            let partition_num = index + 1;
            let end_mb = if partition.size_mb == 0 {
                "100%" // Use remaining space
            } else {
                &format!("{}MB", current_start + partition.size_mb)
            };

            let start_mb = format!("{}MB", current_start);

            let output = AsyncCommand::new("parted")
                .args(&[
                    "--script", device,
                    "mkpart",
                    "primary",
                    partition.filesystem.as_str(),
                    start_mb,
                    end_mb
                ])
                .output()
                .await?;

            if !output.status.success() {
                return Err(WowUsbError::device_operation(
                    format!("Failed to create partition {}: {}", partition_num, String::from_utf8_lossy(&output.stderr))
                ));
            }

            // Set bootable flag if needed
            if partition.bootable {
                let output = AsyncCommand::new("parted")
                    .args(&["--script", device, "set", &format!("{}", partition_num), "boot", "on"])
                    .output()
                    .await?;

                if !output.status.success() {
                    return Err(WowUsbError::device_operation(
                        format!("Failed to set boot flag on partition {}: {}", partition_num, String::from_utf8_lossy(&output.stderr))
                    ));
                }
            }

            current_start += partition.size_mb;
        }

        Ok(())
    }

    async fn format_partition(&self, partition: &str, filesystem: &str, label: &str) -> Result<()> {
        let output = match filesystem {
            "fat32" => {
                AsyncCommand::new("mkfs.fat")
                    .args(&["-F", "32", "-n", label, partition])
                    .output()
                    .await?
            }
            "ntfs" => {
                AsyncCommand::new("mkfs.ntfs")
                    .args(&["-f", "-L", label, partition])
                    .output()
                    .await?
            }
            "exfat" => {
                AsyncCommand::new("mkfs.exfat")
                    .args(&["-n", label, partition])
                    .output()
                    .await?
            }
            "ext4" => {
                AsyncCommand::new("mkfs.ext4")
                    .args(&["-F", "-L", label, partition])
                    .output()
                    .await?
            }
            "f2fs" => {
                AsyncCommand::new("mkfs.f2fs")
                    .args(&["-f", "-l", label, partition])
                    .output()
                    .await?
            }
            _ => {
                return Err(WowUsbError::filesystem(
                    format!("Unsupported filesystem: {}", filesystem)
                ));
            }
        };

        if !output.status.success() {
            return Err(WowUsbError::filesystem(
                format!("Failed to format partition: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        Ok(())
    }

    async fn mount_partition(&self, partition: &str, mountpoint: &str) -> Result<String> {
        // Create mount point if it doesn't exist
        std::fs::create_dir_all(mountpoint)?;

        let output = AsyncCommand::new("mount")
            .args(&[partition, mountpoint])
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
        let output = AsyncCommand::new("umount")
            .arg(mountpoint)
            .output()
            .await?;

        // Don't error if already unmounted
        if !output.status.success() && !String::from_utf8_lossy(&output.stderr).contains("not mounted") {
            return Err(WowUsbError::device_operation(
                format!("Failed to unmount partition: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        Ok(())
    }

    async fn wipe_device(&self, device: &str) -> Result<()> {
        let output = AsyncCommand::new("wipefs")
            .args(&["--all", device])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::device_operation(
                format!("Failed to wipe device: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        Ok(())
    }

    async fn validate_iso(&self, iso_path: &str) -> Result<bool> {
        let output = AsyncCommand::new("7z")
            .args(&["t", iso_path])
            .output()
            .await?;

        Ok(output.status.success())
    }

    async fn extract_iso(&self, iso_path: &str, target_path: &str) -> Result<()> {
        let output = AsyncCommand::new("7z")
            .args(&["x", iso_path, f"-o{target_path}", "-y"])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::iso_processing(
                format!("Failed to extract ISO: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        Ok(())
    }

    async fn install_bootloader(&self, device: &str, bootloader_type: &str) -> Result<()> {
        match bootloader_type {
            "grub2" => {
                // Install GRUB for UEFI
                let output = AsyncCommand::new("grub-install")
                    .args(&["--target=x86_64-efi", "--efi-directory=/boot/efi", "--removable", device])
                    .output()
                    .await?;

                if !output.status.success() {
                    return Err(WowUsbError::device_operation(
                        format!("Failed to install GRUB UEFI: {}", String::from_utf8_lossy(&output.stderr))
                    ));
                }

                // Install GRUB for BIOS
                let output = AsyncCommand::new("grub-install")
                    .args(&["--target=i386-pc", "--removable", device])
                    .output()
                    .await?;

                if !output.status.success() {
                    return Err(WowUsbError::device_operation(
                        format!("Failed to install GRUB BIOS: {}", String::from_utf8_lossy(&output.stderr))
                    ));
                }
            }
            _ => {
                return Err(WowUsbError::not_implemented(
                    format!("Bootloader type not supported: {}", bootloader_type)
                ));
            }
        }

        Ok(())
    }
}

impl LinuxDiskOps {
    async fn is_removable_device(&self, device: &str) -> Result<bool> {
        let device_name = Path::new(device)
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("");

        let sysfs_path = format!("/sys/block/{}", device_name);

        if Path::new(&sysfs_path).exists() {
            // Check removable flag
            let removable_path = format!("{}/removable", sysfs_path);
            if Path::new(&removable_path).exists() {
                let output = AsyncCommand::new("cat")
                    .arg(&removable_path)
                    .output()
                    .await?;

                if output.status.success() {
                    let removable = String::from_utf8(output.stdout)?.trim();
                    return Ok(removable == "1");
                }
            }
        }

        // Fallback: assume USB devices are removable
        Ok(device_name.starts_with("sd") && !device_name.starts_with("sda"))
    }
}