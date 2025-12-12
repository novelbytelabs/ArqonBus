mod handlers;
mod router;
mod policy;
mod middleware;
mod registry;
mod auth;
mod telemetry;

use axum::{routing::get, Router, middleware::from_fn_with_state};
use std::net::SocketAddr;
use std::sync::Arc;
use tracing::info;
use crate::router::nats_bridge::NatsBridge;
use crate::handlers::socket::ws_handler;
use crate::policy::engine::PolicyEngine;
use crate::router::mirroring::{MirrorConfig, MirrorRule};
use crate::middleware::wasm::wasm_middleware;
use crate::middleware::schema::SchemaValidator;

#[derive(Clone)]
pub struct AppState {
    pub nats: NatsBridge,
    pub policy: PolicyEngine,
    pub policy: PolicyEngine,
    pub mirror_config: MirrorConfig,
    pub schema: SchemaValidator,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // 1. Init Telemetry (Tracing + Metrics)
    tracing_subscriber::fmt::init();
    telemetry::init_metrics();
    info!("Shield Reactor booting...");

    // 2. Connect to NATS
    let nats_url = std::env::var("NATS_URL").unwrap_or_else(|_| "nats://127.0.0.1:4222".to_string());
    let nats_bridge = NatsBridge::connect(&nats_url).await?;
    info!("Connected to NATS Spine at {}", nats_url);

    // 3. Init Policy Engine
    let policy_engine = PolicyEngine::new()?;
    let policy_engine = PolicyEngine::new()?;
    info!("Wasm Policy Engine initialized");

    let schema_validator = SchemaValidator::new("envelope.desc", "arqon.v1.Envelope");

    // 4. Init Mirror Config (TODO: load from config file)
    let mirror_config = MirrorConfig {
        enabled: true,
        rules: vec![
            MirrorRule {
                prefix: "in.t.".to_string(),
                percent: 0.10, // 10% mirroring by default
            },
        ],
    };

    // 5. Build Router with Wasm Policy Middleware
    let state = AppState { 
        nats: nats_bridge, 
        policy: policy_engine,
        nats: nats_bridge, 
        policy: policy_engine,
        mirror_config,
        schema: schema_validator,
    };
    let app = Router::new()
        .route("/ws", get(ws_handler))
        .layer(from_fn_with_state(Arc::new(state.clone()), wasm_middleware))
        .with_state(state);

    // 6. Bind Server
    let addr = SocketAddr::from(([0, 0, 0, 0], 4000));
    info!("Shield listening on {}", addr);
    
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
