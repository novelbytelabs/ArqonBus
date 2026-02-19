pub mod auth;
pub mod handlers;
pub mod middleware;
pub mod policy;
pub mod registry;
pub mod router;
pub mod telemetry;

use axum::{middleware::from_fn_with_state, routing::get, Router};
use handlers::socket::ws_handler;
use middleware::{schema::SchemaValidator, wasm::wasm_middleware};
use policy::engine::PolicyEngine;
use router::{
    mirroring::{MirrorConfig, MirrorRule},
    nats_bridge::NatsBridge,
};
use std::sync::Arc;

#[derive(Clone)]
pub struct AppState {
    pub nats: NatsBridge,
    pub policy: PolicyEngine,
    pub mirror_config: MirrorConfig,
    pub schema: SchemaValidator,
}

pub fn default_mirror_config() -> MirrorConfig {
    MirrorConfig {
        enabled: true,
        rules: vec![MirrorRule {
            prefix: "in.t.".to_string(),
            percent: 0.10,
        }],
    }
}

pub fn build_state(
    nats: NatsBridge,
    policy: PolicyEngine,
    mirror_config: MirrorConfig,
    schema: SchemaValidator,
) -> AppState {
    AppState {
        nats,
        policy,
        mirror_config,
        schema,
    }
}

pub fn build_router(state: AppState) -> Router {
    Router::new()
        .route("/ws", get(ws_handler))
        .layer(from_fn_with_state(Arc::new(state.clone()), wasm_middleware))
        .with_state(state)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_mirror_config_is_enabled_and_has_rule() {
        let cfg = default_mirror_config();
        assert!(cfg.enabled);
        assert_eq!(cfg.rules.len(), 1);
        assert_eq!(cfg.rules[0].prefix, "in.t.");
    }
}
