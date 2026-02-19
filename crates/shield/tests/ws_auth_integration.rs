use futures_util::{SinkExt, StreamExt};
use jsonwebtoken::{encode, EncodingKey, Header};
use shield::{
    auth::jwt::Claims, build_router, build_state, default_mirror_config,
    middleware::schema::SchemaValidator, policy::engine::PolicyEngine,
    router::nats_bridge::NatsBridge,
};
use tokio::task::JoinHandle;
use tokio_tungstenite::{
    connect_async,
    tungstenite::{client::ClientRequestBuilder, error::Error as WsError, http::Uri, Message},
};

fn jwt_secret_for_tests() -> String {
    std::env::var("JWT_SECRET").unwrap_or_else(|_| {
        let secret = "arqon-shield-test-secret".to_string();
        std::env::set_var("JWT_SECRET", &secret);
        secret
    })
}

fn issue_token(tenant_id: &str) -> String {
    let secret = jwt_secret_for_tests();
    let claims = Claims {
        sub: "ws-user".to_string(),
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

async fn spawn_server() -> (String, JoinHandle<()>) {
    let state = build_state(
        NatsBridge::disconnected(),
        PolicyEngine::new().expect("policy engine"),
        default_mirror_config(),
        SchemaValidator::new("/tmp/missing.desc", "arqon.v1.Envelope", false),
    );
    let app = build_router(state);
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind test listener");
    let addr = listener.local_addr().expect("local addr");
    let handle = tokio::spawn(async move {
        axum::serve(listener, app).await.expect("server run");
    });
    (format!("ws://{}/ws", addr), handle)
}

#[tokio::test]
async fn websocket_rejects_missing_auth_header() {
    let (url, handle) = spawn_server().await;
    let err = connect_async(&url)
        .await
        .expect_err("must reject missing auth");
    match err {
        WsError::Http(resp) => assert_eq!(resp.status(), 401),
        other => panic!("expected HTTP 401 error, got {other:?}"),
    }
    handle.abort();
}

#[tokio::test]
async fn websocket_accepts_valid_token_and_echoes_text() {
    let (url, handle) = spawn_server().await;
    let token = issue_token("tenant-auth");
    let req = ClientRequestBuilder::new(url.parse::<Uri>().expect("valid uri"))
        .with_header("Authorization", format!("Bearer {token}"));

    let (mut ws, _) = connect_async(req).await.expect("connect");
    ws.send(Message::Text("hello".into()))
        .await
        .expect("send text");

    let msg = ws.next().await.expect("message").expect("ok message");
    match msg {
        Message::Text(text) => assert_eq!(text, "hello"),
        other => panic!("expected text echo, got {other:?}"),
    }

    handle.abort();
}
