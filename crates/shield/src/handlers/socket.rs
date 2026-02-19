use crate::auth::jwt::{decode_token, extract_bearer_token, Claims, JwtConfig};
use crate::middleware::schema::SchemaValidator;
use crate::policy::engine::PolicyEngine;
use crate::router::mirroring::{should_mirror, MirrorConfig};
use crate::router::nats_bridge::NatsBridge;
use crate::AppState;
use axum::{
    extract::ws::{Message, WebSocket, WebSocketUpgrade},
    extract::State,
    http::HeaderMap,
    http::StatusCode,
    response::IntoResponse,
    response::Response,
};
use serde::Serialize;
use tracing::{info, warn};

/// The Actor State for each WebSocket connection.
pub struct ConnectionActor {
    socket: WebSocket,
    nats: NatsBridge,
    claims: Claims,
    trace_id: String,
    mirror_config: MirrorConfig,
    policy: PolicyEngine,
    schema: SchemaValidator,
}

impl ConnectionActor {
    pub fn new(
        socket: WebSocket,
        nats: NatsBridge,
        mirror_config: MirrorConfig,
        claims: Claims,
        policy: PolicyEngine,
        schema: SchemaValidator,
    ) -> Self {
        let trace_id = uuid::Uuid::new_v4().to_string();
        Self {
            socket,
            nats,
            claims,
            trace_id,
            mirror_config,
            policy,
            schema,
        }
    }

    pub async fn run(mut self) {
        info!(
            trace_id = %self.trace_id,
            tenant_id = %self.claims.tenant_id,
            "ConnectionActor started"
        );

        while let Some(msg) = self.socket.recv().await {
            match msg {
                Ok(Message::Binary(payload)) => {
                    // 1. Schema Validation (FR-015)
                    if let Err(e) = self.schema.validate(&payload) {
                        warn!(tenant=%self.claims.tenant_id, "Schema Violation: {}", e);
                        // Optional: Send error to client
                        continue;
                    }

                    // 2. Policy Validation (FR-006)
                    match self.policy.validate(&payload).await {
                        Ok(false) => {
                            warn!(tenant=%self.claims.tenant_id, "Policy Deny");
                            continue;
                        }
                        Err(e) => {
                            warn!(tenant=%self.claims.tenant_id, "Policy Error: {}", e);
                            continue;
                        }
                        _ => {}
                    }

                    // Zero-Copy Hot Path: Forward to NATS
                    let subject = format!("in.t.{}.raw", self.claims.tenant_id);
                    let payload_bytes = bytes::Bytes::from(payload.clone());

                    if let Err(e) = self.nats.publish(&subject, payload_bytes.clone()).await {
                        warn!("Failed to publish to NATS: {}", e);
                        continue;
                    }

                    // Echo back to client (Checkpoint 3)
                    if let Err(e) = self.socket.send(Message::Binary(payload.clone())).await {
                        warn!("Failed to echo message: {}", e);
                    }

                    // Traffic Mirroring
                    if let Some(percent) = self.mirror_config.get_percent(&subject) {
                        if should_mirror(&self.trace_id, percent) {
                            if let Err(e) = self.nats.mirror_publish(&subject, payload_bytes).await
                            {
                                warn!("Failed to mirror to shadow: {}", e);
                            }
                        }
                    }
                }
                Ok(Message::Text(text)) => {
                    // Echo text messages back (for testing)
                    if let Err(e) = self.socket.send(Message::Text(text)).await {
                        warn!("Failed to echo text: {}", e);
                    }
                }
                Ok(Message::Close(_)) => {
                    info!("Client disconnected");
                    break;
                }
                Err(e) => {
                    warn!("Socket error: {}", e);
                    break;
                }
                _ => {}
            }
        }
    }
}

#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum AuthError {
    #[error("Missing Authorization header")]
    MissingAuthorization,
    #[error("Authorization header is not Bearer token format")]
    InvalidAuthorizationFormat,
    #[error("JWT decode failed")]
    InvalidToken,
}

#[derive(Serialize)]
struct ErrorBody {
    error: &'static str,
    details: String,
}

pub fn claims_from_headers(
    headers: &HeaderMap,
    jwt_config: &JwtConfig,
) -> Result<Claims, AuthError> {
    let auth_header = headers
        .get("authorization")
        .and_then(|h| h.to_str().ok())
        .ok_or(AuthError::MissingAuthorization)?;

    let token = extract_bearer_token(auth_header).ok_or(AuthError::InvalidAuthorizationFormat)?;
    decode_token(token, jwt_config).map_err(|_| AuthError::InvalidToken)
}

fn unauthorized_response(err: &AuthError) -> Response {
    let body = ErrorBody {
        error: "Unauthorized",
        details: err.to_string(),
    };
    (StatusCode::UNAUTHORIZED, axum::Json(body)).into_response()
}

pub async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
    headers: HeaderMap,
) -> impl IntoResponse {
    let jwt_config = JwtConfig::default();
    let claims = match claims_from_headers(&headers, &jwt_config) {
        Ok(c) => c,
        Err(e) => {
            warn!("WebSocket auth rejected: {}", e);
            return unauthorized_response(&e);
        }
    };

    ws.on_upgrade(move |socket| async move {
        let actor = ConnectionActor::new(
            socket,
            state.nats.clone(),
            state.mirror_config.clone(),
            claims,
            state.policy.clone(),
            state.schema.clone(),
        );
        actor.run().await;
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::auth::jwt::JwtConfig;
    use axum::http::HeaderValue;
    use jsonwebtoken::{encode, EncodingKey, Header};

    fn test_config() -> JwtConfig {
        JwtConfig {
            secret: "test-secret".to_string(),
            skip_validation: false,
        }
    }

    fn valid_token(secret: &str) -> String {
        let claims = Claims {
            sub: "user-1".to_string(),
            tenant_id: "tenant-a".to_string(),
            exp: (chrono::Utc::now().timestamp() + 3600) as usize,
            iat: chrono::Utc::now().timestamp() as usize,
        };
        encode(
            &Header::default(),
            &claims,
            &EncodingKey::from_secret(secret.as_bytes()),
        )
        .expect("token generation must succeed")
    }

    #[test]
    fn test_claims_from_headers_rejects_missing_auth() {
        let headers = HeaderMap::new();
        let result = claims_from_headers(&headers, &test_config());
        assert_eq!(result.unwrap_err(), AuthError::MissingAuthorization);
    }

    #[test]
    fn test_claims_from_headers_rejects_invalid_format() {
        let mut headers = HeaderMap::new();
        headers.insert("authorization", HeaderValue::from_static("Basic abc"));
        let result = claims_from_headers(&headers, &test_config());
        assert_eq!(result.unwrap_err(), AuthError::InvalidAuthorizationFormat);
    }

    #[test]
    fn test_claims_from_headers_accepts_valid_token() {
        let mut headers = HeaderMap::new();
        let token = valid_token("test-secret");
        headers.insert(
            "authorization",
            HeaderValue::from_str(&format!("Bearer {}", token)).unwrap(),
        );
        let claims = claims_from_headers(&headers, &test_config()).unwrap();
        assert_eq!(claims.sub, "user-1");
        assert_eq!(claims.tenant_id, "tenant-a");
    }
}
