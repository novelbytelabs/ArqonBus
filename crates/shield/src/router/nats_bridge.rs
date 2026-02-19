use async_nats::{Client, HeaderMap};
use anyhow::Result;

#[derive(Clone)]
pub struct NatsBridge {
    client: Client,
}

impl NatsBridge {
    pub async fn connect(url: &str) -> Result<Self> {
        let client = async_nats::connect(url).await?;
        Ok(Self { client })
    }

    pub async fn publish(&self, subject: &str, payload: bytes::Bytes) -> Result<()> {
        self.client.publish(subject.to_string(), payload).await?;
        Ok(())
    }

    /// Publish a message with custom headers.
    pub async fn publish_with_headers(
        &self,
        subject: &str,
        headers: HeaderMap,
        payload: bytes::Bytes,
    ) -> Result<()> {
        self.client
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
        self.publish_with_headers(&shadow_subject, headers, payload).await
    }
}
