use thiserror::Error;

#[derive(Error, Debug)]
pub enum WowUsbError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Device operation failed: {0}")]
    DeviceOperation(String),

    #[error("Filesystem error: {0}")]
    Filesystem(String),

    #[error("Platform error: {0}")]
    Platform(String),

    #[error("Validation error: {0}")]
    Validation(String),

    #[error("ISO processing error: {0}")]
    IsoProcessing(String),

    #[error("Progress error: {0}")]
    Progress(String),

    #[error("Configuration error: {0}")]
    Configuration(String),

    #[error("Operation cancelled")]
    Cancelled,

    #[error("Not implemented: {0}")]
    NotImplemented(String),
}

impl WowUsbError {
    pub fn device_operation(msg: impl Into<String>) -> Self {
        Self::DeviceOperation(msg.into())
    }

    pub fn filesystem(msg: impl Into<String>) -> Self {
        Self::Filesystem(msg.into())
    }

    pub fn platform(msg: impl Into<String>) -> Self {
        Self::Platform(msg.into())
    }

    pub fn validation(msg: impl Into<String>) -> Self {
        Self::Validation(msg.into())
    }

    pub fn iso_processing(msg: impl Into<String>) -> Self {
        Self::IsoProcessing(msg.into())
    }

    pub fn progress(msg: impl Into<String>) -> Self {
        Self::Progress(msg.into())
    }

    pub fn configuration(msg: impl Into<String>) -> Self {
        Self::Configuration(msg.into())
    }

    pub fn not_implemented(msg: impl Into<String>) -> Self {
        Self::NotImplemented(msg.into())
    }
}

pub type Result<T> = std::result::Result<T, WowUsbError>;