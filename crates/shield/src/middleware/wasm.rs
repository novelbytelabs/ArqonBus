//! Axum middleware that runs the Wasm policy engine for each request.
//!
//! The middleware extracts the request payload, invokes the `PolicyEngine` with the
//! configured Wasm module, and either forwards the request or returns an error
//! based on the policy decision.

use axum::{
    body::to_bytes, body::Body, extract::State, http::Request, http::StatusCode, middleware::Next,
    response::Response,
};
use std::sync::Arc;

/// Axum middleware that runs the Wasm policy engine.
pub async fn wasm_middleware(
    State(state): State<Arc<crate::AppState>>,
    req: Request<Body>,
    next: Next,
) -> Result<Response, Response> {
    let (parts, body) = req.into_parts();
    let payload = to_bytes(body, 2 * 1024 * 1024)
        .await
        .map_err(|_| response_for_status(StatusCode::PAYLOAD_TOO_LARGE))?;
    let payload_vec = payload.to_vec();
    let rebuilt_req = Request::from_parts(parts, Body::from(payload));

    // Run the policy engine.
    match state.policy.validate(&payload_vec).await {
        Ok(true) => {
            // Policy allowed – continue to the next handler.
            Ok(next.run(rebuilt_req).await)
        }
        Ok(false) => {
            // Explicit deny from policy.
            Err(response_for_status(StatusCode::FORBIDDEN))
        }
        Err(_e) => {
            // Policy error – fail closed.
            Err(response_for_status(StatusCode::INTERNAL_SERVER_ERROR))
        }
    }
}

fn response_for_status(status: StatusCode) -> Response {
    Response::builder()
        .status(status)
        .body(Body::empty())
        .expect("building middleware response must not fail")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        build_state, default_mirror_config, middleware::schema::SchemaValidator,
        policy::engine::PolicyEngine, router::nats_bridge::NatsBridge,
    };
    use axum::{routing::post, Router};
    use std::sync::Arc;
    use tower::ServiceExt;

    async fn app_with_policy(policy: PolicyEngine) -> Router {
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
    async fn test_wasm_middleware_allows_non_empty_when_policy_allows() {
        let mut policy = PolicyEngine::new().expect("policy engine");
        let module_path = format!("{}/policies/block_empty.wasm", env!("CARGO_MANIFEST_DIR"));
        policy.load_module(module_path).expect("policy load");
        let app = app_with_policy(policy).await;

        let req = Request::builder()
            .method("POST")
            .uri("/inspect")
            .body(Body::from(vec![1_u8, 2, 3]))
            .expect("request");

        let resp = app.oneshot(req).await.expect("response");
        assert_eq!(resp.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_wasm_middleware_denies_empty_payload_when_policy_denies() {
        let mut policy = PolicyEngine::new().expect("policy engine");
        let module_path = format!("{}/policies/block_empty.wasm", env!("CARGO_MANIFEST_DIR"));
        policy.load_module(module_path).expect("policy load");
        let app = app_with_policy(policy).await;

        let req = Request::builder()
            .method("POST")
            .uri("/inspect")
            .body(Body::empty())
            .expect("request");

        let resp = app.oneshot(req).await.expect("response");
        assert_eq!(resp.status(), StatusCode::FORBIDDEN);
    }

    #[tokio::test]
    async fn test_wasm_middleware_fail_closed_on_policy_error() {
        let mut policy = PolicyEngine::new().expect("policy engine");
        let module_path = format!("{}/policies/block_empty.wasm", env!("CARGO_MANIFEST_DIR"));
        policy.load_module(module_path).expect("policy load");
        let app = app_with_policy(policy).await;

        // >64KiB will exceed block_empty.wasm exported memory and trigger policy error.
        let req = Request::builder()
            .method("POST")
            .uri("/inspect")
            .body(Body::from(vec![1_u8; 70_000]))
            .expect("request");

        let resp = app.oneshot(req).await.expect("response");
        assert_eq!(resp.status(), StatusCode::INTERNAL_SERVER_ERROR);
    }
}
