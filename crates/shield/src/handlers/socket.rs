use axum::{
    extract::ws::{Message, WebSocket, WebSocketUpgrade},
    extract::State,
    response::IntoResponse,
    http::HeaderMap,
};
use tracing::{info, warn};
use crate::router::nats_bridge::NatsBridge;
use crate::router::mirroring::{should_mirror, MirrorConfig};
use crate::auth::jwt::{Claims, JwtConfig, decode_token, extract_bearer_token};
use crate::middleware::schema::SchemaValidator;
use crate::policy::engine::PolicyEngine;
use crate::AppState;

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
                            if let Err(e) = self.nats.mirror_publish(&subject, payload_bytes).await {
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

pub async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
    headers: HeaderMap,
) -> impl IntoResponse {
    // Extract JWT from Authorization header
    let auth_header = headers.get("authorization")
        .and_then(|h| h.to_str().ok());
    
    let jwt_config = JwtConfig::default();
    
    let claims = match auth_header {
        Some(header) => {
            match extract_bearer_token(header) {
                Some(token) => {
                    match decode_token(token, &jwt_config) {
                        Ok(c) => c,
                        Err(e) => {
                            warn!("JWT decode failed: {}", e);
                            // For dev mode, use default claims
                            Claims {
                                sub: "anonymous".to_string(),
                                tenant_id: "default".to_string(),
                                exp: 0,
                                iat: 0,
                            }
                        }
                    }
                }
                None => {
                    warn!("No Bearer token in Authorization header");
                    Claims {
                        sub: "anonymous".to_string(),
                        tenant_id: "default".to_string(),
                        exp: 0,
                        iat: 0,
                    }
                }
            }
        }
        None => {
            // No auth header - use default tenant (dev mode)
            Claims {
                sub: "anonymous".to_string(),
                tenant_id: "default".to_string(),
                exp: 0,
                iat: 0,
            }
        }
    };

    ws.on_upgrade(move |socket| async move {
        // Validation Hook (Fail Closed)
        if let Err(e) = state.policy.validate(&[]).await {
            warn!("Policy Rejection: {}", e);
            return;
        }

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
