use anyhow::Result;
use std::sync::Arc;
use wasmtime::{Config, Engine, Linker, Module, Store};

use crate::policy::abi;
#[derive(Clone)]
pub struct PolicyEngine {
    engine: Engine,
    module: Option<Module>,
    linker: Linker<()>,
    config: Arc<abi::HostConfig>,
}

impl PolicyEngine {
    /// Creates a new PolicyEngine with default host configuration.
    pub fn new() -> Result<Self> {
        let mut config = Config::new();
        config.async_support(true);
        // Enable fuel consumption tracking
        config.consume_fuel(true);
        let engine = Engine::new(&config)?;
        let mut linker = Linker::new(&engine);
        let host_config = Arc::new(abi::HostConfig::default());
        // Register ABI functions
        abi::register_abi(&mut linker, host_config.clone())?;
        Ok(Self {
            engine,
            module: None,
            linker,
            config: host_config,
        })
    }

    /// Load a Wasm module from the given path.
    pub fn load_module<P: AsRef<std::path::Path>>(&mut self, path: P) -> Result<()> {
        let bytes = std::fs::read(path)?;
        let module = Module::new(&self.engine, &bytes)?;
        self.module = Some(module);
        Ok(())
    }

    /// Validate a payload using the loaded Wasm module.
    pub async fn validate(&self, payload: &[u8]) -> Result<bool> {
        let module = match &self.module {
            Some(m) => m,
            None => return Ok(true), // No policy loaded => allow
        };
        let mut store = Store::new(&self.engine, ());
        store.set_fuel(self.config.fuel_limit)?;
        let instance = self.linker.instantiate_async(&mut store, module).await?;
        if !payload.is_empty() {
            let memory = instance
                .get_memory(&mut store, "memory")
                .ok_or_else(|| anyhow::anyhow!("policy module missing exported memory"))?;
            let max_payload = self.config.memory_limit_bytes as usize;
            if payload.len() > max_payload {
                return Err(anyhow::anyhow!(
                    "payload size {} exceeds policy memory limit {}",
                    payload.len(),
                    max_payload
                ));
            }
            if payload.len() > memory.data_size(&store) {
                return Err(anyhow::anyhow!(
                    "payload size {} exceeds module memory size {}",
                    payload.len(),
                    memory.data_size(&store)
                ));
            }
            memory.write(&mut store, 0, payload)?;
        }
        // Assume exported function "policy_check" takes a pointer/len and returns i32 (0=allow,1=deny)
        let func = instance.get_typed_func::<(i32, i32), i32>(&mut store, "policy_check")?;
        let result = func
            .call_async(&mut store, (0, payload.len() as i32))
            .await?;
        Ok(result == 0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_policy_engine_initialization() {
        let engine = PolicyEngine::new();
        assert!(engine.is_ok());
    }

    #[tokio::test]
    async fn test_validate_default_allow() {
        let engine = PolicyEngine::new().unwrap();
        let result = engine.validate(b"test payload").await;
        assert!(result.is_ok());
        assert!(result.unwrap());
    }

    #[tokio::test]
    async fn test_block_empty_policy_module_uses_payload_length() {
        let mut engine = PolicyEngine::new().unwrap();
        let module_path = format!("{}/policies/block_empty.wasm", env!("CARGO_MANIFEST_DIR"));
        engine.load_module(module_path).unwrap();

        let empty = engine.validate(b"").await.unwrap();
        let non_empty = engine.validate(b"hello").await.unwrap();
        assert!(!empty);
        assert!(non_empty);
    }
}
