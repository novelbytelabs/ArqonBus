# ArqonBus Deployment & Operators (Design Note)

This note captures how ArqonBus expects operators to be deployed and wired, grounded in the existing staging patterns (e.g., Genesis Engine Flask workers behind Cloudflare tunnels).

It does not change the constitution; it translates it into concrete deployment expectations.

---

## 1. Operator Roles & Placement

- **Shield (Edge)**
  - Terminates client WebSocket connections.
  - Enforces auth, rate limits, and safety policies (Wasm Overseer).
  - Speaks protobuf on the wire; never holds business state.

- **Spine (Bus)**
  - Internal message fabric for topics and circuits.
  - Carries jobs and results between operators.
  - Backed by a durable broker (e.g., NATS) and/or internal routing layer.

- **Operators (Brains / Workers)**
  - Long-lived services that:
    - Subscribe to `*.jobs` topics.
    - Execute compute (Helios, NVM, BowlNet, Genesis-style distillation, etc.).
    - Publish `*.results` and telemetry.
  - May be:
    - Direct ArqonBus-native workers (using the SDK), or
    - HTTP/GRPC services fronted by thin operator proxies.

## 2. Operator Deployment Patterns

### 2.1 Native Bus Operators

- Implement the ArqonBus operator contract directly (protobuf SDK + control-plane registration).
- Run alongside the Spine in a cluster:
  - Example: `helios-operator`, `nvm-operator`, `bowlnet-operator`.
- Communicate only over the Spine; no direct client WebSocket handling.

### 2.2 HTTP/Flask Workers (Genesis Pattern)

The Genesis Engine (`staging/genesis-engine/webserver/app.py`) shows a pattern:

- Notebook logic is packaged as a Flask API (`POST /distill`).
- A local server runs behind a Cloudflare tunnel for external access.

ArqonBus treats this as:

- A **non-native operator** reachable at a stable URL.
- A thin **operator proxy**:
  - Subscribes to `genesis.jobs`.
  - Translates job payloads into HTTP requests.
  - Sends responses back as `genesis.results`.

This pattern lets existing HTTP services participate without embedding Flask inside the Shield.

### 2.3 Physical NVM / BowlNet Rigs

- Physical rigs (audio NVM, optical NVM, bowls) are surfaced via small gateway daemons:
  - Speak to hardware locally (sound card, camera, controllers).
  - Use ArqonBus SDK to act as operators:
    - `nvm.jobs` → run pulse → decode → `nvm.results`.
    - `bowlnet.jobs` → capture audio → run through bowls → `bowlnet.features`.

## 3. Topology & Routing

- **Topics**
  - `*.jobs` for inbound work.
  - `*.results` for single-shot outputs.
  - `*.streams` for continuous data (audio, frames, I/Q traces).
  - `system.control.operators` for operator registration and health.

- **Circuits**
  - Declarative wiring of topics:
    - `input.assets` → `genesis.jobs` → `genesis.results`.
    - `input.audio` → `nvm.jobs` → `nvm.results` → `bowlnet.jobs`.
  - Implemented in the Spine; operators remain oblivious to upstream/downstream details.

## 4. Environments: staging vs production

- **Staging**
  - Mirrors production topology with:
    - Fewer nodes.
    - More permissive quotas and experimental operators (e.g., Genesis Engine).
  - Used for:
    - Notebook-born engines promoted to HTTP APIs.
    - New physical rigs and safety policies.

- **Production**
  - Only vetted operators and configs:
    - Locked-down Helm/Terraform manifests under `production/`.
    - Strict adherence to the constitution (bounded queues, fail-closed safety, no layer bypass).
  - Genesis-style services that graduate are re-deployed as:
    - Native operators, or
    - Hardened HTTP services behind well-defined proxies.

## 5. Operator Lifecycle

1. **Prototype**
   - Lives in a notebook or single script.
   - Called manually or via a local Flask server (`staging/` patterns).

2. **Staging Operator**
   - Wrapped as:
     - Native ArqonBus operator using the SDK, or
     - HTTP worker with an ArqonBus proxy.
   - Registered on `system.control.operators`.
   - Observed and load-tested.

3. **Production Operator**
   - Code, config, and manifests committed under version control.
   - Deployed via CI/CD into the production cluster.
   - Subject to full SLOs, quotas, and safety policies.

This lifecycle ensures that every “engine” in this repo (Helios, NVM, BowlNet, Genesis, quantum/QML) can move from notebook → staging → ArqonBus-backed production in a consistent, governed way.

---

## 6. Example: Genesis Distillation Operator Shim

This example sketches how a proxied operator would bridge ArqonBus to the Genesis Flask worker in `staging/genesis-engine/webserver/app.py`.

It is illustrative (not a full implementation); the actual SDK types and error handling will evolve.

```python
# genesis_operator_shim.py (conceptual)

import os
import requests
from arqonbus import BusClient, JobMessage  # hypothetical SDK

GENESIS_URL = os.environ.get("GENESIS_DISTILL_URL", "http://localhost:3000/distill")

def handle_genesis_job(bus: BusClient, msg: JobMessage) -> None:
    """
    Translate a `genesis.jobs` message into an HTTP request to the Genesis worker
    and publish the response to `genesis.results`.
    """
    job_id = msg.payload["job_id"]
    image_data = msg.payload["imageData"]
    width = msg.payload["width"]
    height = msg.payload["height"]
    asset_type = msg.payload.get("assetType", "NoisyCheckerboard")

    try:
        resp = requests.post(
            GENESIS_URL,
            json={
                "imageData": image_data,
                "width": width,
                "height": height,
                "assetType": asset_type,
            },
            timeout=10,
        )
        resp.raise_for_status()
        seed = resp.json()
        bus.publish(
            topic="genesis.results",
            schema="arqonbus.genesis.result.v1",
            payload={"job_id": job_id, "seed": seed},
        )
    except Exception as e:
        bus.publish(
            topic="genesis.results",
            schema="arqonbus.genesis.result.v1",
            payload={"job_id": job_id, "error": str(e)},
        )


def main():
    bus = BusClient.connect(os.environ["ARQONBUS_URL"], token=os.environ["ARQONBUS_TOKEN"])

    # Register on the control plane
    bus.register_operator(
        operator_id="genesis-distiller-1",
        operator_type="genesis",
        supported_schemas=["arqonbus.genesis.job.v1", "arqonbus.genesis.result.v1"],
        resource_limits={"max_parallel_jobs": 4},
        hardware_profile="cpu",
    )

    # Subscribe to genesis.jobs and start consuming
    bus.subscribe("genesis.jobs", schema="arqonbus.genesis.job.v1", handler=handle_genesis_job)
    bus.run_forever()


if __name__ == "__main__":
    main()
```

Key points:

- The shim is the only process that speaks ArqonBus; the Genesis Flask app remains an HTTP worker.
- All Genesis-related traffic still flows through the Spine:
  - `genesis.jobs` → shim → HTTP worker.
  - HTTP worker → shim → `genesis.results`.
- This pattern generalizes to any existing HTTP/GRPC service that we want to onboard as an ArqonBus operator.

