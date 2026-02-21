use axum::{body::Body, http::Request, http::StatusCode, routing::post, Router};
use shield::{
    build_state, default_mirror_config, middleware::schema::SchemaValidator,
    middleware::wasm::wasm_middleware, policy::engine::PolicyEngine,
    router::nats_bridge::NatsBridge,
};
use std::sync::Arc;
use tower::ServiceExt;

fn app_with_policy(policy: PolicyEngine) -> Router {
    let state = build_state(
        NatsBridge::disconnected(),
        policy,
        default_mirror_config(),
        SchemaValidator::new("/tmp/missing.desc", "arqon.v1.Envelope", false),
    );
    Router::new()
        .route("/inspect", post(|| async { StatusCode::OK }))
        .layer(axum::middleware::from_fn_with_state(
            Arc::new(state.clone()),
            wasm_middleware,
        ))
        .with_state(state)
}

#[tokio::test]
async fn middleware_chain_allows_non_empty_payload() {
    let mut policy = PolicyEngine::new().expect("policy");
    let module_path = format!("{}/policies/block_empty.wasm", env!("CARGO_MANIFEST_DIR"));
    policy.load_module(module_path).expect("module");
    let app = app_with_policy(policy);

    let req = Request::builder()
        .method("POST")
        .uri("/inspect")
        .body(Body::from(vec![1_u8, 2, 3]))
        .expect("request");
    let resp = app.oneshot(req).await.expect("response");
    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn middleware_chain_denies_empty_payload() {
    let mut policy = PolicyEngine::new().expect("policy");
    let module_path = format!("{}/policies/block_empty.wasm", env!("CARGO_MANIFEST_DIR"));
    policy.load_module(module_path).expect("module");
    let app = app_with_policy(policy);

    let req = Request::builder()
        .method("POST")
        .uri("/inspect")
        .body(Body::empty())
        .expect("request");
    let resp = app.oneshot(req).await.expect("response");
    assert_eq!(resp.status(), StatusCode::FORBIDDEN);
}

#[tokio::test]
async fn middleware_chain_fail_closed_on_policy_runtime_error() {
    let mut policy = PolicyEngine::new().expect("policy");
    let module_path = format!("{}/policies/block_empty.wasm", env!("CARGO_MANIFEST_DIR"));
    policy.load_module(module_path).expect("module");
    let app = app_with_policy(policy);

    // >64KiB exceeds block_empty module memory and forces policy error.
    let req = Request::builder()
        .method("POST")
        .uri("/inspect")
        .body(Body::from(vec![1_u8; 70_000]))
        .expect("request");
    let resp = app.oneshot(req).await.expect("response");
    assert_eq!(resp.status(), StatusCode::INTERNAL_SERVER_ERROR);
}
