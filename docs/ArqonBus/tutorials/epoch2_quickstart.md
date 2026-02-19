# Epoch 2 Quickstart

This guide walks you through running ArqonBus with Epoch 2 features.

## Prerequisites

- Conda environment: `helios-gpu-118`
- Rust toolchain (installed in conda env)

## Step 1: Activate Conda Environment

```bash
conda activate helios-gpu-118
```

## Step 2: Check if NATS is Running

```bash
ss -tlnp | grep 4222
```

If you see output with `LISTEN` on port 4222, NATS is already running. Skip to Step 4.

If no output, start NATS:

```bash
nats-server -js
```

!!! note "Port Already in Use?"
    If `nats-server` says "address already in use" but `ss` shows nothing, wait a few seconds and try again. The port may be in TIME_WAIT state.

## Step 3: Run the Shield Server

In a new terminal:

```bash
conda activate helios-gpu-118
NATS_URL=nats://localhost:4222 cargo run -p shield
```

You should see:

```
[INFO] Connected to NATS Spine at nats://localhost:4222
[INFO] Wasm Policy Engine initialized
[INFO] Shield listening on 0.0.0.0:4000
```

## Step 4: Connect via WebSocket

In another terminal:

```bash
wscat -c ws://localhost:4000/ws
```

!!! warning "wscat Not Found or Broken?"
    If wscat fails, install it fresh:
    ```bash
    npm install -g wscat
    ```
    
    If you still get errors, use the full NVM path:
    ```bash
    ~/.nvm/versions/node/v22.20.0/bin/wscat -c ws://localhost:4000/ws
    ```

You should see:
```
Connected (press CTRL+C to quit)
>
```

## Step 5: Run the Test Suite

Verify all Epoch 2 features:

```bash
cargo test -p shield
```

Expected: **14 tests passing**

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `nats-server: command not found` | Installed in conda env: `/home/irbsurfer/miniconda3/envs/helios-gpu-118/bin/nats-server` |
| `address already in use` | NATS is already running. Check with `ss -tlnp \| grep 4222` |
| `wscat: Cannot find module` | Use `npm install -g wscat` or full path `~/.nvm/versions/node/v22.20.0/bin/wscat` |
