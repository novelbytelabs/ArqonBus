//! JWT authentication and claims extraction.

use anyhow::{anyhow, Result};
use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};

/// JWT claims structure for ArqonBus.
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Claims {
    /// Subject (user/service identifier)
    pub sub: String,
    /// Tenant ID
    pub tenant_id: String,
    /// Expiration timestamp (Unix epoch)
    pub exp: usize,
    /// Issued at timestamp
    pub iat: usize,
}

/// Configuration for JWT validation.
#[derive(Clone)]
pub struct JwtConfig {
    /// Secret key for HS256 tokens (for dev/testing)
    pub secret: String,
    /// Whether to skip validation (dev mode only)
    pub skip_validation: bool,
}

impl Default for JwtConfig {
    fn default() -> Self {
        Self {
            secret: std::env::var("JWT_SECRET").unwrap_or_else(|_| "arqon-dev-secret".to_string()),
            skip_validation: std::env::var("JWT_SKIP_VALIDATION").is_ok(),
        }
    }
}

/// Decode and validate a JWT token.
pub fn decode_token(token: &str, config: &JwtConfig) -> Result<Claims> {
    if config.skip_validation {
        // Dev mode: decode without validation
        let parts: Vec<&str> = token.split('.').collect();
        if parts.len() != 3 {
            return Err(anyhow!("Invalid JWT format"));
        }

        use base64::Engine;
        let payload = base64::engine::general_purpose::URL_SAFE_NO_PAD
            .decode(parts[1])
            .map_err(|e| anyhow!("Failed to decode JWT payload: {}", e))?;
        let claims: Claims = serde_json::from_slice(&payload)
            .map_err(|e| anyhow!("Failed to parse JWT claims: {}", e))?;
        return Ok(claims);
    }

    let key = DecodingKey::from_secret(config.secret.as_bytes());
    let mut validation = Validation::new(Algorithm::HS256);
    validation.validate_exp = true;

    let token_data = decode::<Claims>(token, &key, &validation)
        .map_err(|e| anyhow!("JWT validation failed: {}", e))?;

    Ok(token_data.claims)
}

/// Extract bearer token from Authorization header.
pub fn extract_bearer_token(auth_header: &str) -> Option<&str> {
    if auth_header.starts_with("Bearer ") {
        Some(&auth_header[7..])
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use jsonwebtoken::{encode, EncodingKey, Header};

    #[test]
    fn test_decode_valid_token() {
        let config = JwtConfig {
            secret: "test-secret".to_string(),
            skip_validation: false,
        };

        let claims = Claims {
            sub: "user123".to_string(),
            tenant_id: "tenant-abc".to_string(),
            exp: (chrono::Utc::now().timestamp() + 3600) as usize,
            iat: chrono::Utc::now().timestamp() as usize,
        };

        let token = encode(
            &Header::default(),
            &claims,
            &EncodingKey::from_secret(config.secret.as_bytes()),
        )
        .unwrap();

        let decoded = decode_token(&token, &config).unwrap();
        assert_eq!(decoded.sub, "user123");
        assert_eq!(decoded.tenant_id, "tenant-abc");
    }

    #[test]
    fn test_extract_bearer_token() {
        assert_eq!(extract_bearer_token("Bearer abc123"), Some("abc123"));
        assert_eq!(extract_bearer_token("abc123"), None);
        assert_eq!(extract_bearer_token("Basic abc123"), None);
    }

    #[test]
    fn test_invalid_token() {
        let config = JwtConfig {
            secret: "test-secret".to_string(),
            skip_validation: false,
        };

        let result = decode_token("invalid.token.here", &config);
        assert!(result.is_err());
    }
}
