use anyhow::Result;
use prost_reflect::{DescriptorPool, DynamicMessage};
use tracing::{info, warn};
use std::path::Path;

#[derive(Clone)]
pub struct SchemaValidator {
    pool: Option<DescriptorPool>,
    message_name: String,
}

impl SchemaValidator {
    pub fn new(descriptor_path: &str, message_name: &str) -> Self {
        let pool = if Path::new(descriptor_path).exists() {
             match std::fs::read(descriptor_path) {
                Ok(bytes) => {
                    match DescriptorPool::decode(bytes.as_slice()) {
                        Ok(p) => {
                            info!("Schema Validator loaded descriptors from {}", descriptor_path);
                            Some(p)
                        },
                        Err(e) => {
                            warn!("Failed to decode descriptor set: {}", e);
                            None
                        }
                    }
                },
                Err(e) => {
                    warn!("Failed to read descriptor file {}: {}", descriptor_path, e);
                    None
                }
             }
        } else {
            warn!("Descriptor file {} not found. Schema validation DISABLED.", descriptor_path);
            None
        };

        Self {
            pool,
            message_name: message_name.to_string(),
        }
    }

    pub fn validate(&self, payload: &[u8]) -> Result<()> {
        if let Some(pool) = &self.pool {
             let descriptor = pool.get_message_by_name(&self.message_name)
                .ok_or_else(|| anyhow::anyhow!("Message {} not found in descriptor", self.message_name))?;
            
             let _msg = DynamicMessage::decode(descriptor, payload)
                .map_err(|e| anyhow::anyhow!("Schema Validation Failed: {}", e))?;
             
             Ok(())
        } else {
            // Passthrough if no schema loaded (Dev mode / Sandbox)
            Ok(())
        }
    }
}
