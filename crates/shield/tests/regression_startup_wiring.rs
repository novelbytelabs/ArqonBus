use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use shield::{
    build_router, build_state, default_mirror_config, middleware::schema::SchemaValidator,
    policy::engine::PolicyEngine, router::nats_bridge::NatsBridge,
};
use tower::ServiceExt;

#[tokio::test]
async fn regression_ws_route_is_present_after_router_build() {
    let state = build_state(
        NatsBridge::disconnected(),
        PolicyEngine::new().expect("policy engine"),
        default_mirror_config(),
        SchemaValidator::new("/tmp/missing.desc", "arqon.v1.Envelope", false),
    );
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
        resp.status() == StatusCode::UNAUTHORIZED || resp.status() == StatusCode::UPGRADE_REQUIRED,
        "expected unauthorized or upgrade required, got {}",
        resp.status()
    );
}

#[test]
fn regression_default_mirror_rule_still_exists() {
    let cfg = default_mirror_config();
    assert!(cfg.enabled);
    assert_eq!(cfg.rules.len(), 1);
    assert_eq!(cfg.rules[0].prefix, "in.t.");
}
