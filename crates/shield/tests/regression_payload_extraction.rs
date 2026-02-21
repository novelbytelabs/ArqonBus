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
async fn regression_non_empty_payload_is_not_treated_as_empty() {
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
