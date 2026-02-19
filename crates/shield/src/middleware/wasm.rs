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
