//! Axum middleware that runs the Wasm policy engine for each request.
//!
//! The middleware extracts the request payload, invokes the `PolicyEngine` with the
//! configured Wasm module, and either forwards the request or returns an error
//! based on the policy decision.

use axum::{
    body::Body,
    extract::State,
    http::Request,
    middleware::Next,
    response::Response,
};
use std::sync::Arc;

/// Axum middleware that runs the Wasm policy engine.
pub async fn wasm_middleware(
    State(state): State<Arc<crate::AppState>>,
    req: Request<Body>,
    next: Next,
) -> Result<Response, Response> {
    // Extract body bytes (assuming the request body implements `bytes::Bytes` or similar).
    // For simplicity we only handle empty bodies here; real implementation would
    // read the body into a Vec<u8>.
    let payload: Vec<u8> = vec![]; // Placeholder – actual extraction needed.

    // Run the policy engine.
    match state.policy.validate(&payload).await {
        Ok(true) => {
            // Policy allowed – continue to the next handler.
            Ok(next.run(req).await)
        }
        Ok(false) => {
            // Explicit deny from policy.
            let resp = Response::builder()
                .status(axum::http::StatusCode::FORBIDDEN)
                .body(Body::empty())
                .unwrap();
            Err(resp)
        }
        Err(_e) => {
            // Policy error – fail closed.
            let resp = Response::builder()
                .status(axum::http::StatusCode::INTERNAL_SERVER_ERROR)
                .body(Body::empty())
                .unwrap();
            Err(resp)
        }
    }
}
