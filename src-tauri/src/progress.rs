use std::sync::Arc;
use tokio::sync::{RwLock, broadcast};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ProgressUpdate {
    pub progress: u8,
    pub message: String,
    pub stage: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

pub struct ProgressManager {
    sender: broadcast::Sender<ProgressUpdate>,
    cancelled: Arc<RwLock<bool>>,
}

impl ProgressManager {
    pub fn new() -> Self {
        let (sender, _) = broadcast::channel(100);

        Self {
            sender,
            cancelled: Arc::new(RwLock::new(false)),
        }
    }

    pub async fn update(&self, progress: u8, message: String, stage: String) -> Result<(), broadcast::error::SendError<ProgressUpdate>> {
        let update = ProgressUpdate {
            progress,
            message,
            stage,
            timestamp: chrono::Utc::now(),
        };

        self.sender.send(update)
    }

    pub fn subscribe(&self) -> broadcast::Receiver<ProgressUpdate> {
        self.sender.subscribe()
    }

    pub async fn cancel(&self) -> Result<(), crate::error::WowUsbError> {
        let mut cancelled = self.cancelled.write().await;
        *cancelled = true;
        Ok(())
    }

    pub async fn is_cancelled(&self) -> bool {
        let cancelled = self.cancelled.read().await;
        *cancelled
    }

    pub async fn reset(&self) {
        let mut cancelled = self.cancelled.write().await;
        *cancelled = false;
    }
}

impl Default for ProgressManager {
    fn default() -> Self {
        Self::new()
    }
}