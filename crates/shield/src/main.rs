use shield::{
    build_router, build_state, default_mirror_config, middleware::schema::SchemaValidator,
    policy::engine::PolicyEngine, router::nats_bridge::NatsBridge, telemetry,
};
use std::net::SocketAddr;
use tracing::info;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // 1. Init Telemetry (Tracing + Metrics)
    tracing_subscriber::fmt::init();
    telemetry::init_metrics();
    info!("Shield Reactor booting...");
    enforce_auth_preflight()?;

    // 2. Connect to NATS
    let nats_url =
        std::env::var("NATS_URL").unwrap_or_else(|_| "nats://127.0.0.1:4222".to_string());
    let nats_bridge = NatsBridge::connect(&nats_url).await?;
    info!("Connected to NATS Spine at {}", nats_url);

    // 3. Init Policy Engine
    let mut policy_engine = PolicyEngine::new()?;
    if let Ok(policy_path) = std::env::var("POLICY_WASM_PATH") {
        policy_engine.load_module(policy_path)?;
        info!("Loaded policy module from POLICY_WASM_PATH");
    }
    info!("Wasm Policy Engine initialized");

    let schema_validator =
        SchemaValidator::new("envelope.desc", "arqon.v1.Envelope", schema_strict_mode());
    schema_validator.ensure_ready()?;

    // 4. Init Mirror Config (TD-001: load from config file)
    let mirror_config = default_mirror_config();

    // 5. Build Router with Wasm Policy Middleware
    let state = build_state(nats_bridge, policy_engine, mirror_config, schema_validator);
    let app = build_router(state);

    // 6. Bind Server
    let addr = SocketAddr::from(([0, 0, 0, 0], 4000));
    info!("Shield listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

fn schema_strict_mode() -> bool {
    std::env::var("ARQON_SCHEMA_STRICT")
        .map(|v| v == "1" || v.eq_ignore_ascii_case("true"))
        .unwrap_or(true)
}

fn enforce_auth_preflight() -> anyhow::Result<()> {
    let jwt_secret = std::env::var("JWT_SECRET").unwrap_or_default();
    if jwt_secret.trim().is_empty() {
        anyhow::bail!("JWT_SECRET must be configured for Shield startup");
    }

    if std::env::var("JWT_SKIP_VALIDATION").is_ok() {
        anyhow::bail!("JWT_SKIP_VALIDATION is not allowed in Shield runtime");
    }

    Ok(())
}
