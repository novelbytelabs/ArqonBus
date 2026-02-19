use anyhow::Result;
use async_nats::{Client, HeaderMap};

#[derive(Clone)]
pub struct NatsBridge {
    client: Option<Client>,
}

impl NatsBridge {
    pub async fn connect(url: &str) -> Result<Self> {
        let client = async_nats::connect(url).await?;
        Ok(Self {
            client: Some(client),
        })
    }

    pub fn disconnected() -> Self {
        Self { client: None }
    }

    pub async fn publish(&self, subject: &str, payload: bytes::Bytes) -> Result<()> {
        let client = self
            .client
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("NATS client unavailable"))?;
        client.publish(subject.to_string(), payload).await?;
        Ok(())
    }

    /// Publish a message with custom headers.
    pub async fn publish_with_headers(
        &self,
        subject: &str,
        headers: HeaderMap,
        payload: bytes::Bytes,
    ) -> Result<()> {
        let client = self
            .client
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("NATS client unavailable"))?;
        client
            .publish_with_headers(subject.to_string(), headers, payload)
            .await?;
        Ok(())
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
}
