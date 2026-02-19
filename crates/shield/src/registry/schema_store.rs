//! Schema store backed by NATS KV bucket.
//!
//! Stores and retrieves Protobuf FileDescriptorSet schemas
//! with in-memory caching and TTL support.

use anyhow::{anyhow, Result};
use async_nats::jetstream::{self, kv::Store};
use flate2::read::GzDecoder;
use std::collections::HashMap;
use std::io::Read;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;

/// Configuration for the schema registry.
#[derive(Clone, Debug)]
pub struct RegistryConfig {
    pub enabled: bool,
    pub kv_bucket: String,
    pub cache_ttl_seconds: u64,
}

impl Default for RegistryConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            kv_bucket: "ARQON_SCHEMAS".to_string(),
            cache_ttl_seconds: 300,
        }
    }
}

/// Cached schema entry.
struct CacheEntry {
    data: Vec<u8>,
    expires_at: Instant,
}

/// Schema store with NATS KV backend and in-memory cache.
pub struct SchemaStore {
    store: Store,
    cache: Arc<RwLock<HashMap<String, CacheEntry>>>,
    ttl: Duration,
}

impl SchemaStore {
    /// Create a new schema store connected to NATS KV.
    pub async fn new(js: jetstream::Context, config: &RegistryConfig) -> Result<Self> {
        let store = js.get_key_value(&config.kv_bucket).await?;
        Ok(Self {
            store,
            cache: Arc::new(RwLock::new(HashMap::new())),
            ttl: Duration::from_secs(config.cache_ttl_seconds),
        })
    }

    /// Get a schema by ID, using cache if available.
    pub async fn get_schema(&self, schema_id: &str) -> Result<Option<Vec<u8>>> {
        // Check cache first
        {
            let cache = self.cache.read().await;
            if let Some(entry) = cache.get(schema_id) {
                if entry.expires_at > Instant::now() {
                    return Ok(Some(entry.data.clone()));
                }
            }
        }

        // Fetch from NATS KV
        let entry = self.store.get(schema_id).await?;
        match entry {
            Some(data) => {
                // Decompress gzipped data
                let decompressed = decompress_gzip(&data)?;

                // Update cache
                {
                    let mut cache = self.cache.write().await;
                    cache.insert(
                        schema_id.to_string(),
                        CacheEntry {
                            data: decompressed.clone(),
                            expires_at: Instant::now() + self.ttl,
                        },
                    );
                }

                Ok(Some(decompressed))
            }
            None => Ok(None),
        }
    }

    /// Clear expired entries from the cache.
    pub async fn cleanup_cache(&self) {
        let mut cache = self.cache.write().await;
        let now = Instant::now();
        cache.retain(|_, entry| entry.expires_at > now);
    }
}

/// Decompress gzipped data.
fn decompress_gzip(data: &[u8]) -> Result<Vec<u8>> {
    let mut decoder = GzDecoder::new(data);
    let mut decompressed = Vec::new();
    decoder
        .read_to_end(&mut decompressed)
        .map_err(|e| anyhow!("Failed to decompress schema: {}", e))?;
    Ok(decompressed)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gzip_decompression() {
        use flate2::write::GzEncoder;
        use flate2::Compression;
        use std::io::Write;

        // Compress test data
        let original = b"Hello, Protobuf schema!";
        let mut encoder = GzEncoder::new(Vec::new(), Compression::default());
        encoder.write_all(original).unwrap();
        let compressed = encoder.finish().unwrap();

        // Decompress
        let result = decompress_gzip(&compressed).unwrap();
        assert_eq!(result, original);
    }

    #[test]
    fn test_registry_config_default() {
        let config = RegistryConfig::default();
        assert!(config.enabled);
        assert_eq!(config.kv_bucket, "ARQON_SCHEMAS");
        assert_eq!(config.cache_ttl_seconds, 300);
    }
}
