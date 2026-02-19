use futures_util::{SinkExt, StreamExt};
use jsonwebtoken::{encode, EncodingKey, Header};
use shield::{
    auth::jwt::Claims,
    build_router, build_state, default_mirror_config,
    middleware::schema::SchemaValidator,
    policy::engine::PolicyEngine,
    router::nats_bridge::{NatsBridge, PublishRecord},
};
use std::sync::Arc;
use tokio::sync::Mutex;
use tokio::task::JoinHandle;
use tokio::time::{timeout, Duration};
use tokio_tungstenite::{
    connect_async,
    tungstenite::{client::ClientRequestBuilder, error::Error as WsError, http::Uri, Message},
};

fn issue_token(tenant_id: &str) -> String {
    let secret = std::env::var("JWT_SECRET").unwrap_or_else(|_| "arqon-dev-secret".to_string());
    let claims = Claims {
        sub: "e2e-user".to_string(),
        tenant_id: tenant_id.to_string(),
        exp: (chrono::Utc::now().timestamp() + 3600) as usize,
        iat: chrono::Utc::now().timestamp() as usize,
    };
    encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(secret.as_bytes()),
    )
    .expect("token generation")
}

async fn spawn_server() -> (String, JoinHandle<()>, Arc<Mutex<Vec<PublishRecord>>>) {
    let (nats, recorder) = NatsBridge::recording_for_tests();
    let mut policy = PolicyEngine::new().expect("policy");
    let module_path = format!("{}/policies/block_empty.wasm", env!("CARGO_MANIFEST_DIR"));
    policy.load_module(module_path).expect("load module");

    let state = build_state(
        nats,
        policy,
        default_mirror_config(),
        SchemaValidator::new("/tmp/missing.desc", "arqon.v1.Envelope", false),
    );
    let app = build_router(state);
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind listener");
    let addr = listener.local_addr().expect("local addr");
    let handle = tokio::spawn(async move {
        axum::serve(listener, app).await.expect("server run");
    });
    (format!("ws://{}/ws", addr), handle, recorder)
}

#[tokio::test]
async fn e2e_fail_closed_rejects_unauthorized_upgrade() {
    let (url, handle, _) = spawn_server().await;
    let err = connect_async(&url).await.expect_err("must reject unauth");
    match err {
        WsError::Http(resp) => {
            assert!(resp.status() == 401 || resp.status() == 403);
        }
        other => panic!("expected http 401/403, got {other:?}"),
    }
    handle.abort();
}

#[tokio::test]
async fn e2e_fail_closed_blocks_policy_runtime_errors() {
    let (url, handle, recorder) = spawn_server().await;
    let token = issue_token("tenant-failclosed");
    let req = ClientRequestBuilder::new(url.parse::<Uri>().expect("valid uri"))
        .with_header("Authorization", format!("Bearer {token}"));
    let (mut ws, _) = connect_async(req).await.expect("connect");

    // >64KiB triggers policy memory error in block_empty module and should not be echoed/published.
    ws.send(Message::Binary(vec![1_u8; 70_000].into()))
        .await
        .expect("send");
    let blocked = timeout(Duration::from_millis(150), ws.next()).await;
    assert!(
        blocked.is_err(),
        "policy runtime errors should fail closed without echo"
    );

    let records = recorder.lock().await;
    assert!(
        records.is_empty(),
        "policy runtime errors should prevent publish"
    );

    handle.abort();
}
