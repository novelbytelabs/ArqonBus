use axum::http::{HeaderMap, HeaderValue};
use jsonwebtoken::{encode, EncodingKey, Header};
use shield::auth::jwt::{Claims, JwtConfig};
use shield::handlers::socket::{claims_from_headers, AuthError};
use shield::middleware::schema::SchemaValidator;

fn jwt_config() -> JwtConfig {
    JwtConfig {
        secret: "integration-secret".to_string(),
        skip_validation: false,
    }
}

fn valid_token(secret: &str) -> String {
    let claims = Claims {
        sub: "integration-user".to_string(),
        tenant_id: "tenant-int".to_string(),
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
fn integration_claims_from_headers_validates_strictly() {
    let mut headers = HeaderMap::new();
    headers.insert("authorization", HeaderValue::from_static("Basic abc"));
    let err = claims_from_headers(&headers, &jwt_config()).unwrap_err();
    assert_eq!(err, AuthError::InvalidAuthorizationFormat);

    let token = valid_token("integration-secret");
    headers.insert(
        "authorization",
        HeaderValue::from_str(&format!("Bearer {}", token)).expect("valid header"),
    );
    let claims = claims_from_headers(&headers, &jwt_config()).expect("valid claims");
    assert_eq!(claims.tenant_id, "tenant-int");
}

#[test]
fn integration_schema_validator_strict_mode_is_fail_closed() {
    let strict = SchemaValidator::new("/tmp/missing-integration.desc", "arqon.v1.Envelope", true);
    assert!(strict.ensure_ready().is_err());
    assert!(strict.validate(b"\x08\x01").is_err());

    let permissive =
        SchemaValidator::new("/tmp/missing-integration.desc", "arqon.v1.Envelope", false);
    assert!(permissive.ensure_ready().is_ok());
    assert!(permissive.validate(b"\x08\x01").is_ok());
}
