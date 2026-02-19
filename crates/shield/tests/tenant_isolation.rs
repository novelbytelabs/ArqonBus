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
use tokio_tungstenite::{
    connect_async,
    tungstenite::{client::ClientRequestBuilder, http::Uri, Message},
};

fn issue_token(tenant_id: &str) -> String {
    let secret = std::env::var("JWT_SECRET").unwrap_or_else(|_| "arqon-dev-secret".to_string());
    let claims = Claims {
        sub: format!("user-{tenant_id}"),
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
    let state = build_state(
        nats,
        PolicyEngine::new().expect("policy engine"),
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

fn auth_request(url: &str, token: &str) -> ClientRequestBuilder {
    ClientRequestBuilder::new(url.parse::<Uri>().expect("valid uri"))
        .with_header("Authorization", format!("Bearer {token}"))
}

#[tokio::test]
async fn tenant_binary_messages_route_to_distinct_subjects() {
    let (url, handle, recorder) = spawn_server().await;
    let token_a = issue_token("tenant-a");
    let token_b = issue_token("tenant-b");

    let (mut ws_a, _) = connect_async(auth_request(&url, &token_a))
        .await
        .expect("connect tenant A");
    let (mut ws_b, _) = connect_async(auth_request(&url, &token_b))
        .await
        .expect("connect tenant B");

    ws_a.send(Message::Binary(vec![1_u8, 2, 3].into()))
        .await
        .expect("send A");
    ws_b.send(Message::Binary(vec![4_u8, 5, 6].into()))
        .await
        .expect("send B");

    let echo_a = ws_a.next().await.expect("echo A").expect("echo A ok");
    let echo_b = ws_b.next().await.expect("echo B").expect("echo B ok");
    assert!(matches!(echo_a, Message::Binary(_)));
    assert!(matches!(echo_b, Message::Binary(_)));

    let records = recorder.lock().await;
    assert_eq!(records.len(), 2);
    let subjects: Vec<String> = records.iter().map(|r| r.subject.clone()).collect();
    assert!(subjects.contains(&"in.t.tenant-a.raw".to_string()));
    assert!(subjects.contains(&"in.t.tenant-b.raw".to_string()));

    handle.abort();
}
