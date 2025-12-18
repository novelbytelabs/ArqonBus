# Sample Wasm Policy for ArqonBus Shield

This directory contains sample Wasm policy modules that demonstrate the policy engine.

## block_empty.wat

A sample policy that rejects empty payloads.

### Building

```bash
# Install wat2wasm from WABT
# https://github.com/WebAssembly/wabt

wat2wasm block_empty.wat -o block_empty.wasm
```

### Exports

- `policy_check(ptr: i32, len: i32) -> i32`
  - Returns `0` to allow the message
  - Returns `1` to deny the message (empty payload)
