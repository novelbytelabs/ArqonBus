pub mod auth;
pub mod handlers;
pub mod middleware;
pub mod policy;
pub mod registry;
pub mod router;
pub mod telemetry;

use axum::{routing::get, Router};
use handlers::socket::ws_handler;
use middleware::schema::SchemaValidator;
use policy::engine::PolicyEngine;
use router::{
    mirroring::{MirrorConfig, MirrorRule},
    nats_bridge::NatsBridge,
};

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
        .with_state(state)
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::{Request, StatusCode},
    };
    use tower::ServiceExt;

    #[test]
    fn test_default_mirror_config_is_enabled_and_has_rule() {
        let cfg = default_mirror_config();
        assert!(cfg.enabled);
        assert_eq!(cfg.rules.len(), 1);
        assert_eq!(cfg.rules[0].prefix, "in.t.");
    }

    #[tokio::test]
    async fn test_build_state_and_router_returns_ws_route() {
        let nats = NatsBridge::disconnected();
        let policy = PolicyEngine::new().expect("policy engine");
        let schema = SchemaValidator::new("/tmp/missing.desc", "arqon.v1.Envelope", false);
        let state = build_state(nats, policy, default_mirror_config(), schema);
        let app = build_router(state);

        let req = Request::builder()
            .method("GET")
            .uri("/ws")
            .header("connection", "upgrade")
            .header("upgrade", "websocket")
            .header("sec-websocket-version", "13")
            .header("sec-websocket-key", "dGhlIHNhbXBsZSBub25jZQ==")
            .body(Body::empty())
            .expect("request");

        let resp = app.oneshot(req).await.expect("response");
        assert!(
            resp.status() == StatusCode::UNAUTHORIZED
                || resp.status() == StatusCode::UPGRADE_REQUIRED,
            "expected auth rejection or websocket-upgrade required, got {}",
            resp.status()
        );
    }
}
