use futures::StreamExt;
use serde::{Deserialize, Serialize};
use tracing::{error, info, warn};

#[derive(Deserialize, Debug)]
struct Config {
    nats_url: String,
    subject: String,
    webhook_url: String,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();
    info!("Starting op-webhook...");

    let nats_url =
        std::env::var("NATS_URL").unwrap_or_else(|_| "nats://127.0.0.1:4222".to_string());
    let subject = std::env::var("WEBHOOK_SUBJECT").unwrap_or_else(|_| "out.t.>".to_string());
    let webhook_url = std::env::var("WEBHOOK_URL").expect("WEBHOOK_URL env var required");

    let client = async_nats::connect(&nats_url).await?;
    info!("Connected to NATS at {}", nats_url);

    let mut subscriber = client.subscribe(subject.clone()).await?;
    info!("Subscribed to {}", subject);

    let http_client = reqwest::Client::new();

    while let Some(msg) = subscriber.next().await {
        let payload = msg.payload.clone();

        info!(
            "Received message on {}, forwarding to {}",
            msg.subject, webhook_url
        );

        match http_client.post(&webhook_url).body(payload).send().await {
            Ok(resp) => {
                info!("Webhook response: {}", resp.status());
            }
            Err(e) => {
                error!("Webhook failed: {}", e);
            }
        }
    }

    Ok(())
}
