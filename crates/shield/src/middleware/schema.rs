use anyhow::Result;
use prost_reflect::{DescriptorPool, DynamicMessage};
use std::path::Path;
use tracing::{info, warn};

#[derive(Clone)]
pub struct SchemaValidator {
    pool: Option<DescriptorPool>,
    message_name: String,
    strict: bool,
    init_error: Option<String>,
}

impl SchemaValidator {
    pub fn new(descriptor_path: &str, message_name: &str, strict: bool) -> Self {
        let mut init_error: Option<String> = None;
        let pool = if Path::new(descriptor_path).exists() {
            match std::fs::read(descriptor_path) {
                Ok(bytes) => match DescriptorPool::decode(bytes.as_slice()) {
                    Ok(p) => {
                        info!(
                            "Schema Validator loaded descriptors from {} (strict={})",
                            descriptor_path, strict
                        );
                        Some(p)
                    }
                    Err(e) => {
                        let msg = format!("Failed to decode descriptor set: {}", e);
                        warn!("{}", msg);
                        init_error = Some(msg);
                        None
                    }
                },
                Err(e) => {
                    let msg = format!("Failed to read descriptor file {}: {}", descriptor_path, e);
                    warn!("{}", msg);
                    init_error = Some(msg);
                    None
                }
            }
        } else {
            let msg = format!("Descriptor file {} not found", descriptor_path);
            warn!("{}", msg);
            init_error = Some(msg);
            None
        };

        if strict && pool.is_none() {
            warn!(
                "Schema validation strict mode enabled and descriptors unavailable; payload validation will fail closed"
            );
        }

        Self {
            pool,
            message_name: message_name.to_string(),
            strict,
            init_error,
        }
    }

    pub fn ensure_ready(&self) -> Result<()> {
        if self.strict && self.pool.is_none() {
            return Err(anyhow::anyhow!(
                "Schema validator not ready in strict mode: {}",
                self.init_error
                    .as_deref()
                    .unwrap_or("descriptor pool unavailable")
            ));
        }
        Ok(())
    }

    pub fn validate(&self, payload: &[u8]) -> Result<()> {
        if let Some(pool) = &self.pool {
            let descriptor = pool
                .get_message_by_name(&self.message_name)
                .ok_or_else(|| {
                    anyhow::anyhow!("Message {} not found in descriptor", self.message_name)
                })?;

            let _msg = DynamicMessage::decode(descriptor, payload)
                .map_err(|e| anyhow::anyhow!("Schema Validation Failed: {}", e))?;

            Ok(())
        } else if self.strict {
            Err(anyhow::anyhow!(
                "Schema validation unavailable in strict mode: {}",
                self.init_error
                    .as_deref()
                    .unwrap_or("descriptor pool unavailable")
            ))
        } else {
            Ok(())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_non_strict_mode_allows_missing_descriptor() {
        let validator =
            SchemaValidator::new("/tmp/does-not-exist.desc", "arqon.v1.Envelope", false);
        assert!(validator.ensure_ready().is_ok());
        assert!(validator.validate(b"\x08\x01").is_ok());
    }

    #[test]
    fn test_strict_mode_fails_when_descriptor_missing() {
        let validator = SchemaValidator::new("/tmp/does-not-exist.desc", "arqon.v1.Envelope", true);
        assert!(validator.ensure_ready().is_err());
        assert!(validator.validate(b"\x08\x01").is_err());
    }
}
