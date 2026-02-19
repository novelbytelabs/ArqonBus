use anyhow::Result;
use async_nats::{Client, HeaderMap};
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PublishRecord {
    pub subject: String,
    pub payload: bytes::Bytes,
    pub headers: Option<HeaderMap>,
}

#[derive(Clone)]
pub struct NatsBridge {
    client: Option<Client>,
    recorder: Option<Arc<Mutex<Vec<PublishRecord>>>>,
}

impl NatsBridge {
    pub async fn connect(url: &str) -> Result<Self> {
        let client = async_nats::connect(url).await?;
        Ok(Self {
            client: Some(client),
            recorder: None,
        })
    }

    pub fn disconnected() -> Self {
        Self {
            client: None,
            recorder: None,
        }
    }

    pub fn recording_for_tests() -> (Self, Arc<Mutex<Vec<PublishRecord>>>) {
        let recorder = Arc::new(Mutex::new(Vec::new()));
        (
            Self {
                client: None,
                recorder: Some(recorder.clone()),
            },
            recorder,
        )
    }

    pub async fn publish(&self, subject: &str, payload: bytes::Bytes) -> Result<()> {
        self.publish_with_optional_headers(subject, None, payload)
            .await
    }

    /// Publish a message with custom headers.
    pub async fn publish_with_headers(
        &self,
        subject: &str,
        headers: HeaderMap,
        payload: bytes::Bytes,
    ) -> Result<()> {
        self.publish_with_optional_headers(subject, Some(headers), payload)
            .await
    }

    /// Publish a mirrored (shadow) message with the x-arqon-shadow header.
    pub async fn mirror_publish(
        &self,
        original_subject: &str,
        payload: bytes::Bytes,
    ) -> Result<()> {
        let shadow_subject = format!("shadow.{}", original_subject);
        let mut headers = HeaderMap::new();
        headers.insert("x-arqon-shadow", "true");
        self.publish_with_headers(&shadow_subject, headers, payload)
            .await
    }

    async fn publish_with_optional_headers(
        &self,
        subject: &str,
        headers: Option<HeaderMap>,
        payload: bytes::Bytes,
    ) -> Result<()> {
        if let Some(client) = &self.client {
            if let Some(h) = headers {
                client
                    .publish_with_headers(subject.to_string(), h, payload)
                    .await?;
            } else {
                client.publish(subject.to_string(), payload).await?;
            }
            return Ok(());
        }

        if let Some(recorder) = &self.recorder {
            let mut guard = recorder.lock().await;
            guard.push(PublishRecord {
                subject: subject.to_string(),
                payload,
                headers,
            });
            return Ok(());
        }

        Err(anyhow::anyhow!("NATS client unavailable"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_disconnected_bridge_fails_closed() {
        let bridge = NatsBridge::disconnected();
        let result = bridge
            .publish("in.t.tenant.raw", bytes::Bytes::from_static(b"msg"))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_recording_bridge_captures_publish() {
        let (bridge, recorder) = NatsBridge::recording_for_tests();
        bridge
            .publish("in.t.tenant.raw", bytes::Bytes::from_static(b"msg"))
            .await
            .expect("record publish");

        let records = recorder.lock().await;
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].subject, "in.t.tenant.raw");
        assert_eq!(records[0].payload, bytes::Bytes::from_static(b"msg"));
        assert!(records[0].headers.is_none());
    }

    #[tokio::test]
    async fn test_recording_bridge_captures_headers() {
        let (bridge, recorder) = NatsBridge::recording_for_tests();
        let mut headers = HeaderMap::new();
        headers.insert("x-test", "1");
        bridge
            .publish_with_headers(
                "shadow.in.t.tenant.raw",
                headers,
                bytes::Bytes::from_static(b"msg"),
            )
            .await
            .expect("record publish with headers");

        let records = recorder.lock().await;
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].subject, "shadow.in.t.tenant.raw");
        assert!(records[0].headers.is_some());
    }
}
