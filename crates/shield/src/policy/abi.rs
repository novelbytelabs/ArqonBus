//! ABI definitions for the Wasm host used by the Shield policy engine.
//!
//! This module defines the functions that are exposed to Wasm guest modules.
//! The ABI version is `arqon_host_v1` and is stable for Epoch 2.
//!
//! All host functions follow the convention `host_<action>` and operate on
//! raw pointers/lengths passed from the guest. The runtime will translate these
//! into safe Rust types before invoking the implementation.

use anyhow::Result;
use std::sync::Arc;
use wasmtime::{Caller, Linker};

/// Configuration limits for the Wasm host.
#[allow(dead_code)]
pub struct HostConfig {
    /// Maximum fuel units a module may consume before being terminated.
    pub fuel_limit: u64,
    /// Maximum linear memory size in bytes.
    pub memory_limit_bytes: u64,
}

impl Default for HostConfig {
    fn default() -> Self {
        Self {
            fuel_limit: 10_000,                  // ~5 ms on typical hardware
            memory_limit_bytes: 4 * 1024 * 1024, // 4 MiB
        }
    }
}

/// Register the ABI functions with a Wasmtime `Linker`.
pub fn register_abi<T>(linker: &mut Linker<T>, _config: Arc<HostConfig>) -> Result<()> {
    // host_log(level: i32, ptr: i32, len: i32) -> i32
    let host_log = move |mut caller: Caller<'_, T>, level: i32, ptr: i32, len: i32| {
        let memory = match caller.get_export("memory") {
            Some(wasmtime::Extern::Memory(m)) => m,
            _ => return Err::<i32, anyhow::Error>(anyhow::anyhow!("memory not exported")),
        };
        let data = memory.data(&caller)[ptr as usize..(ptr + len) as usize].to_vec();
        let msg = String::from_utf8_lossy(&data);
        // Simple mapping: 0=error,1=warn,2=info,3=debug,4=trace
        match level {
            0 => tracing::error!("[Wasm] {}", msg),
            1 => tracing::warn!("[Wasm] {}", msg),
            2 => tracing::info!("[Wasm] {}", msg),
            3 => tracing::debug!("[Wasm] {}", msg),
            4 => tracing::trace!("[Wasm] {}", msg),
            _ => tracing::info!("[Wasm] {}", msg),
        }
        Ok(0i32)
    };
    linker.func_wrap("env", "host_log", host_log)?;

    // host_get_header(name_ptr: i32, name_len: i32, out_ptr: i32) -> i32
    // Returns length of value written to out_ptr, or -1 if not found.
    let host_get_header =
        move |_caller: Caller<'_, T>, _name_ptr: i32, _name_len: i32, _out_ptr: i32| {
            // In a real implementation we would look up request headers stored in the caller's data.
            // For now we return -1 to indicate not found.
            Ok::<i32, anyhow::Error>(-1i32)
        };
    linker.func_wrap("env", "host_get_header", host_get_header)?;

    // host_reject(code: i32, msg_ptr: i32, msg_len: i32) -> i32
    let host_reject = move |mut caller: Caller<'_, T>, code: i32, msg_ptr: i32, msg_len: i32| {
        let memory = match caller.get_export("memory") {
            Some(wasmtime::Extern::Memory(m)) => m,
            _ => return Err::<i32, anyhow::Error>(anyhow::anyhow!("memory not exported")),
        };
        let data = memory.data(&caller)[msg_ptr as usize..(msg_ptr + msg_len) as usize].to_vec();
        let msg = String::from_utf8_lossy(&data);
        tracing::warn!("[Wasm reject {}] {}", code, msg);
        // Signal rejection to the engine via a trap.
        Err::<i32, anyhow::Error>(anyhow::anyhow!("reject"))
    };
    linker.func_wrap("env", "host_reject", host_reject)?;

    // Additional host functions (e.g., get_claim, add_header) can be added here.
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use wasmtime::{Config, Engine, Linker, Store};

    #[tokio::test]
    async fn test_host_abi_registration() -> Result<()> {
        // Set up engine and linker
        let mut config = Config::new();
        config.consume_fuel(true);
        let engine = Engine::new(&config)?;
        let mut linker: Linker<()> = Linker::new(&engine);
        let host_cfg = Arc::new(HostConfig::default());
        // Register ABI functions – should succeed
        register_abi(&mut linker, host_cfg)?;
        // Create a store to ensure linker is usable
        let _store = Store::new(&engine, ());
        Ok(())
    }
}
