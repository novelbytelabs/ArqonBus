mod handlers;
mod router;
mod policy;
mod middleware;
mod registry;

use axum::{routing::get, Router};
use axum::middleware::from_fn_with_state;
use std::net::SocketAddr;
use std::sync::Arc;
use tracing::info;
use crate::router::nats_bridge::NatsBridge;
use crate::handlers::socket::ws_handler;
use crate::policy::engine::PolicyEngine;
use crate::middleware::wasm::wasm_middleware;

#[derive(Clone)]
pub struct AppState {
    nats: NatsBridge,
    policy: PolicyEngine,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // 1. Init Telemetry
    tracing_subscriber::fmt::init();
    info!("Shield Reactor booting...");

    // 2. Connect to NATS
    let nats_url = std::env::var("NATS_URL").unwrap_or_else(|_| "nats://127.0.0.1:4222".to_string());
    let nats_bridge = NatsBridge::connect(&nats_url).await?;
    info!("Connected to NATS Spine at {}", nats_url);

    // 3. Init Policy Engine
    let policy_engine = PolicyEngine::new()?;
    info!("Wasm Policy Engine initialized");

    // 4. Build Router (middleware integration pending full Axum 0.7 compatibility)
    let state = AppState { nats: nats_bridge, policy: policy_engine };
    let app = Router::new()
        .route("/ws", get(ws_handler))
        // TODO: Re-enable wasm middleware once signature is fully compatible
        // .layer(from_fn_with_state(state.clone(), wasm_middleware))
        .with_state(state);

    // 4. Bind Server
    let addr = SocketAddr::from(([0, 0, 0, 0], 4000));
    info!("Shield listening on {}", addr);
    
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
