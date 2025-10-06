use crate::disk::{Device, PartitionConfig, PlatformDiskOps};
use crate::error::{WowUsbError, Result};
use std::process::Command;
use std::path::Path;
use tokio::process::Command as AsyncCommand;

pub struct WindowsDiskOps;

impl WindowsDiskOps {
    pub fn new() -> Self {
        Self
    }
}

impl PlatformDiskOps for WindowsDiskOps {
    async fn list_devices(&self) -> Result<Vec<Device>> {
        // Use PowerShell to get disk information
        let powershell_script = r#"
        Get-Disk | Where-Object {$_.IsSystem -eq $false} | ForEach-Object {
            $partitions = Get-Partition -DiskNumber $_.Number | Where-Object {$_.DriveLetter}
            $drive = if ($partitions) { $partitions[0].DriveLetter } else { $null }

            [PSCustomObject]@{
                Number = $_.Number
                Model = $_.Model
                Size = $_.Size
                BusType = $_.BusType
                MediaType = $_.MediaType
                IsSystem = $_.IsSystem
                IsRemovable = $_.IsRemovable
                DriveLetter = $drive
            }
        } | ConvertTo-Json
        "#;

        let output = AsyncCommand::new("powershell")
            .args(&["-Command", powershell_script])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::device_operation(
                format!("PowerShell command failed: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        let json_str = String::from_utf8(output.stdout)?;
        let disks: Vec<serde_json::Value> = serde_json::from_str(&json_str)?;

        let mut devices = Vec::new();

        for disk in disks {
            if let (Some(number), Some(model), Some(size)) = (
                disk.get("Number").and_then(|v| v.as_i64()),
                disk.get("Model").and_then(|v| v.as_str()),
                disk.get("Size").and_then(|v| v.as_i64())
            ) {
                let device_path = format!("\\\\.\\PhysicalDrive{}", number);
                let drive_letter = disk.get("DriveLetter")
                    .and_then(|v| v.as_str())
                    .filter(|s| !s.is_empty());

                let size_gb = size / (1024 * 1024 * 1024);
                let size_str = format!("{} GB", size_gb);

                let mountpoint = drive_letter.map(|letter| format!("{}:", letter));

                let is_removable = disk.get("IsRemovable")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(false);

                let is_usb = disk.get("BusType")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_lowercase().contains("usb"))
                    .unwrap_or(false);

                devices.push(Device {
                    name: device_path,
                    size: size_str,
                    model: model.to_string(),
                    filesystem: None, // Would need additional query
                    mountpoint,
                    is_removable,
                    is_usb,
                });
            }
        }

        Ok(devices)
    }

    async fn verify_device(&self, device: &str) -> Result<bool> {
        // Extract disk number from device path
        let disk_number = if device.starts_with("\\\\.\\PhysicalDrive") {
            device.strip_prefix("\\\\.\\PhysicalDrive")
                .unwrap_or("0")
                .parse::<u32>()
                .unwrap_or(0)
        } else {
            return Ok(false);
        };

        let powershell_script = format!(r#"
        try {{
            Get-Disk -Number {} | Out-Null
            $true
        }} catch {{
            $false
        }}
        "#, disk_number);

        let output = AsyncCommand::new("powershell")
            .args(&["-Command", &powershell_script])
            .output()
            .await?;

        if !output.status.success() {
            return Ok(false);
        }

        let result = String::from_utf8(output.stdout)?.trim();
        Ok(result == "True")
    }

    async fn create_partitions(&self, device: &str, config: &[PartitionConfig]) -> Result<()> {
        let disk_number = self.extract_disk_number(device)?;

        // Clear the disk
        let clear_script = format!(r#"
        Clear-Disk -Number {} -RemoveData -Confirm:$false
        "#, disk_number);

        let output = AsyncCommand::new("powershell")
            .args(&["-Command", &clear_script])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::device_operation(
                format!("Failed to clear disk: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        // Initialize as GPT
        let init_script = format!(r#"
        Initialize-Disk -Number {} -PartitionStyle GPT
        "#, disk_number);

        let output = AsyncCommand::new("powershell")
            .args(&["-Command", &init_script])
            .output()
            .await?;

        if !output.status.success() {
            return Err(WowUsbError::device_operation(
                format!("Failed to initialize disk: {}", String::from_utf8_lossy(&output.stderr))
            ));
        }

        // Create partitions
        let mut current_size = 0;
        for (index, partition) in config.iter().enumerate() {
            let size_mb = if partition.size_mb == 0 {
                "Max" // Use remaining space
            } else {
                &format!("{}MB", partition.size_mb)
            };

            let create_script = format!(r#"
            New-Partition -DiskNumber {} -Size {} -DriveLetter {} -AssignDriveLetter
            "#, disk_number, size_mb, char(b'C' + index as u8));

            let output = AsyncCommand::new("powershell")
                .args(&["-Command", &create_script])
                .output()
                .await?;

            if !output.status.success() {
                return Err(WowUsbError::device_operation(
                    format!("Failed to create partition: {}", String::from_utf8_lossy(&output.stderr))
                ));
            }

            current_size += partition.size_mb;
        }

        Ok(())
    }

    async fn format_partition(&self, partition: &str, filesystem: &str, label: &str) -> Result<()> {
        let drive_letter = self.extract_drive_letter(partition)?;
        let drive_path = format!("{}:", drive_letter);

        let format_script = match filesystem {
            "fat32" => format!(r#"Format-Volume -DriveLetter {} -FileSystem FAT32 -NewFileSystemLabel "{}" -Confirm:$false"#, drive_letter, label),
            "ntfs" => format!(r#"Format-Volume -DriveLetter {} -FileSystem NTFS -NewFileSystemLabel "{}" -Confirm:$false"#, drive_letter, label),
            "exfat" => format!(r#"Format-Volume -DriveLetter {} -FileSystem exFAT -NewFileSystemLabel "{}" -Confirm:$false"#, drive_letter, label),
            _ => {
                return Err(WowUsbError::filesystem(
                    format!("Unsupported filesystem: {}", filesystem)
                ));
            }
        };

        let output = AsyncCommand::new("powershell")
            .args(&["-Command", &format_script])
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
        // Windows doesn't use traditional mount points
        // We return the drive letter
        let drive_letter = self.extract_drive_letter(partition)?;
        Ok(format!("{}:", drive_letter))
    }

    async fn unmount_partition(&self, mountpoint: &str) -> Result<()> {
        // On Windows, we can use Remove-PartitionAccessPath if needed
        // For now, this is a no-op as Windows handles this differently
        Ok(())
    }

    async fn wipe_device(&self, device: &str) -> Result<()> {
        let disk_number = self.extract_disk_number(device)?;

        let clear_script = format!(r#"
        Clear-Disk -Number {} -RemoveData -Confirm:$false
        "#, disk_number);

        let output = AsyncCommand::new("powershell")
            .args(&["-Command", &clear_script])
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
        // Use 7-Zip to validate ISO
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
                // Windows bootloader installation would use tools like Rufus APIs
                // For now, this is a placeholder
                return Err(WowUsbError::not_implemented(
                    "Windows bootloader installation not yet implemented"
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

impl WindowsDiskOps {
    fn extract_disk_number(&self, device: &str) -> Result<u32> {
        if device.starts_with("\\\\.\\PhysicalDrive") {
            device.strip_prefix("\\\\.\\PhysicalDrive")
                .unwrap_or("0")
                .parse::<u32>()
                .map_err(|_| WowUsbError::validation("Invalid device format"))
        } else {
            Err(WowUsbError::validation("Invalid device format"))
        }
    }

    fn extract_drive_letter(&self, partition: &str) -> Result<char> {
        if partition.len() >= 2 && partition.chars().nth(1) == Some(':') {
            Ok(partition.chars().next().unwrap())
        } else {
            Err(WowUsbError::validation("Invalid partition format"))
        }
    }
}