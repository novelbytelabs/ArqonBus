use axum::http::HeaderMap;
use shield::auth::jwt::JwtConfig;
use shield::handlers::socket::{claims_from_headers, AuthError};
use shield::router::nats_bridge::NatsBridge;

#[test]
fn regression_no_anonymous_fallback_on_missing_auth_header() {
    let headers = HeaderMap::new();
    let cfg = JwtConfig {
        secret: "regression-secret".to_string(),
        skip_validation: false,
    };

    let result = claims_from_headers(&headers, &cfg);
    assert_eq!(result.unwrap_err(), AuthError::MissingAuthorization);
}

#[tokio::test]
async fn regression_disconnected_nats_bridge_rejects_publish() {
    let bridge = NatsBridge::disconnected();
    let result = bridge
        .publish("in.t.regression.raw", bytes::Bytes::from_static(b"payload"))
        .await;
    assert!(result.is_err());
}
