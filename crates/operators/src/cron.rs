use futures::StreamExt;
use tracing::{error, info};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();
    info!("Starting op-cron...");

    let nats_url =
        std::env::var("NATS_URL").unwrap_or_else(|_| "nats://127.0.0.1:4222".to_string());
    let schedule = std::env::var("CRON_SCHEDULE").unwrap_or_else(|_| "*/1 * * * *".to_string());
    let subject = std::env::var("CRON_SUBJECT").expect("CRON_SUBJECT env var required");
    let payload = std::env::var("CRON_PAYLOAD").unwrap_or_else(|_| "tick".to_string());

    let client = async_nats::connect(&nats_url).await?;
    info!("Connected to NATS at {}", nats_url);

    // Mock cron trigger loop for demo (in production use a real cron scheduler crate)
    let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(60));

    loop {
        interval.tick().await;
        info!("Cron trigger: {}", schedule);

        match client
            .publish(subject.clone(), payload.clone().into())
            .await
        {
            Ok(_) => info!("Published cron event to {}", subject),
            Err(e) => error!("Failed to publish cron event: {}", e),
        }
    }
}
