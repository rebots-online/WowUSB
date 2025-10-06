#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Arc;
use tokio::sync::RwLock;
use tauri::Manager;

mod disk;
mod filesystem;
mod iso;
mod platform;
mod progress;
mod error;
mod version;

use disk::{DiskManager, PlatformDiskOps};
use filesystem::{FilesystemManager, PlatformFilesystemOps};
use progress::{ProgressManager, ProgressUpdate};
use error::WowUsbError;
use version;

#[derive(Clone, serde::Serialize)]
struct DeviceInfo {
    name: String,
    size: String,
    model: String,
    filesystem: Option<String>,
    mountpoint: Option<String>,
    is_removable: bool,
    is_usb: bool,
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
struct CreateConfig {
    target_os: String,
    filesystem: String,
    enable_persistence: bool,
    enable_multiboot: bool,
    wintogo_enabled: bool,
    drive_label: String,
}

#[derive(Clone, serde::Serialize)]
struct ProgressEvent {
    progress: u8,
    message: String,
    stage: String,
    timestamp: String,
}

#[derive(Clone)]
struct AppState {
    disk_manager: Arc<DiskManager>,
    filesystem_manager: Arc<FilesystemManager>,
    progress_manager: Arc<RwLock<ProgressManager>>,
}

#[tauri::command]
async fn list_devices(state: tauri::State<'_, AppState>) -> Result<Vec<DeviceInfo>, String> {
    let devices = state.disk_manager.list_devices().await
        .map_err(|e| e.to_string())?;

    Ok(devices.into_iter().map(|d| DeviceInfo {
        name: d.name,
        size: d.size,
        model: d.model,
        filesystem: d.filesystem,
        mountpoint: d.mountpoint,
        is_removable: d.is_removable,
        is_usb: d.is_usb,
    }).collect())
}

#[tauri::command]
async fn verify_device(
    device: String,
    state: tauri::State<'_, AppState>
) -> Result<bool, String> {
    let result = state.disk_manager.verify_device(&device).await
        .map_err(|e| e.to_string())?;

    Ok(result)
}

#[tauri::command]
async fn create_bootable_usb(
    source_path: String,
    target_device: String,
    config: CreateConfig,
    window: tauri::Window,
    state: tauri::State<'_, AppState>
) -> Result<String, String> {
    // Set up progress reporting
    let progress_tx = state.progress_manager.clone();
    let window_clone = window.clone();

    // Spawn progress reporting task
    tokio::spawn(async move {
        let mut rx = {
            let pm = progress_tx.read().await;
            pm.subscribe()
        };

        while let Ok(progress) = rx.recv().await {
            let progress_event = ProgressEvent {
                progress: progress.progress,
                message: progress.message.clone(),
                stage: progress.stage.clone(),
                timestamp: chrono::Utc::now().to_rfc3339(),
            };

            let _ = window_clone.emit("progress", &progress_event);
        }
    });

    // Start the USB creation process
    let result = state.disk_manager.create_bootable_usb(
        &source_path,
        &target_device,
        &config
    ).await.map_err(|e| e.to_string())?;

    Ok(result)
}

#[tauri::command]
async fn get_filesystem_info(
    state: tauri::State<'_, AppState>
) -> Result<Vec<String>, String> {
    let filesystems = state.filesystem_manager.get_available_filesystems()
        .map_err(|e| e.to_string())?;

    Ok(filesystems)
}

#[tauri::command]
async fn validate_iso(
    iso_path: String,
    state: tauri::State<'_, AppState>
) -> Result<bool, String> {
    let result = state.disk_manager.validate_iso(&iso_path).await
        .map_err(|e| e.to_string())?;

    Ok(result)
}

#[tauri::command]
async fn cancel_operation(
    state: tauri::State<'_, AppState>
) -> Result<bool, String> {
    let result = state.progress_manager.write().await.cancel().await
        .map_err(|e| e.to_string())?;

    Ok(result)
}

#[tauri::command]
async fn get_version() -> Result<String, String> {
    Ok(version::VERSION.to_string())
}

fn main() {
    // Initialize logging
    env_logger::init();

    // Create shared state
    let disk_manager = Arc::new(DiskManager::new());
    let filesystem_manager = Arc::new(FilesystemManager::new());
    let progress_manager = Arc::new(RwLock::new(ProgressManager::new()));

    let app_state = AppState {
        disk_manager,
        filesystem_manager,
        progress_manager,
    };

    tauri::Builder::default()
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            list_devices,
            verify_device,
            create_bootable_usb,
            get_filesystem_info,
            validate_iso,
            cancel_operation,
            get_version
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}