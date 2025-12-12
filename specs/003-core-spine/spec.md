# Feature Specification: The Core Spine (Epoch 1)

**Feature Branch**: `01-core-spine`  
**Created**: 2025-12-11  
**Status**: Draft  
**Input**: "Specify the Core Spine (Epoch 1) including Transport (NATS), Shield (Rust Gateway), Brain (Elixir State), and Protocol, ensuring O(1) performance, Tenant Isolation, and Wasm Safety hooks."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Secure Connectivity (Priority: P1)

As a Tenant Developer, I want to connect to the bus using a secure WebSocket and a signed JWT so that I can establish a persistent session.

**Why this priority**: Without connectivity and auth, there is no bus. This is the "Hello World".

**Independent Test**: Can be fully tested by a script that generates a JWT and opens a WebSocket connection using `wscat` or a test client.

**Acceptance Scenarios**:

1. **Given** a valid JWT with `role: "user"`, **When** I connect to `ws://api.arqon/v1/socket`, **Then** the connection is accepted and I receive a `WELCOME` opcode.
2. **Given** an invalid/expired JWT, **When** I connect, **Then** I receive a `401 Unauthorized` and the socket closes immediately.
3. **Given** no auth header, **When** I connect, **Then** I receive `401 Unauthorized`.

---

### User Story 2 - Real-time Echo (Priority: P1)

As a Connected User, I want to send a message to a room and receive it back instantly so that I can verify real-time latency.

**Why this priority**: Proves the "Spine" (Transport) is working and routing is functional.

**Independent Test**: Connect Client A and Client B to the same room. Client A sends. Client B receives.

**Acceptance Scenarios**:

1. **Given** two authenticated clients in the same Tenant/Room, **When** Client A publishes `HELLO`, **Then** Client B receives `HELLO` within < 50ms.
2. **Given** clients in **different** Tenants, **When** Client A publishes, **Then** Client B receives **nothing** (Isolation proof).

---

### User Story 3 - Programmable Safety (Priority: P2)

As a Platform Admin, I want to deploy a Wasm policy that blocks "bad words" so that I can filter traffic without restarting the server.

**Why this priority**: Enforces the "Programmable Safety" constitutional requirement (The Overseer).

**Independent Test**: Load a mock Wasm module that rejects payloads containing "virus". Send a message with "virus".

**Acceptance Scenarios**:

1. **Given** a Safety Policy that forbids the string "malware", **When** I send a message containing "malware", **Then** the server replies with `Error: Message blocked by policy` and the message is NOT routed to other clients.
2. **Given** a clean message, **When** I send it, **Then** it is routed normally.
3. **Given** the Wasm module crashes/times out, **When** I send a message, **Then** it is **BLOCKED** (Fail Closed).

---

### User Story 4 - Presence Awareness (Priority: P2)

As a User, I want to know who else is in the room so that I can see my team's availability.

**Why this priority**: Validates the "Brain" (State Layer) and Elixir Presence CRDTs.

**Independent Test**: User A joins. User B sees "A joined". User A disconnects (force kill). User B sees "A left".

**Acceptance Scenarios**:

1. **Given** User A is in the room, **When** User B joins, **Then** User A receives a `PRESENCE_UPDATE` event listing User B.
2. **Given** User B crashes (TCP reset), **When** the heartbeat expires, **Then** User A receives a `PRESENCE_LEAVE` event.

---

### User Story 5 - Developer Experience (Priority: P2)

As a Developer, I want to control the stack via a unified CLI (`arq dev`, `arq status`) so that I don't have to memorize docker-compose commands or API paths.

**Acceptance Scenarios**:

1. **Given** I am in the repo, **When** I run `arq dev up`, **Then** the Docker stack (NATS, Brain, Shield, Jaeger, Grafana) spins up.
2. **Given** the stack is running, **When** I run `arq status`, **Then** I see the health of all services and the current connection count.
3. **Given** I need a test token, **When** I run `arq auth gen --role user`, **Then** I get a valid JWT.

---

### User Story 6 - Operational Visibility (Priority: P2)

As an Operator, I want immediate visibility into the "Core Spine" metrics (Throughput, Latency, Error Rate) via standard dashboards, so I can debug issues without digging into raw logs.

**Acceptance Scenarios**:

1. **Given** the stack is running, **When** I open Grafana (localhost:3000), **Then** I see a pre-loaded "ArqonBus Overview" dashboard.
2. **Given** a message flow, **When** I check Jaeger, **Then** I see a distributed trace spanning Shield -> Spine -> Brain.

As a Developer, I want to install the client SDK via `pip install arqon-sdk` and run it on Windows, Linux, and Mac, so that I can integrate it into my apps easily.

**Why this priority**: Adoption depends on DX. The "Complete Package" promise.

**Acceptance Scenarios**:

1. **Given** a clean Python env on Windows, **When** I run `pip install arqon-sdk`, **Then** it installs successfully.
2. **Given** the SDK is installed, **When** I run the `arqon.connect()` example, **Then** it connects to the local Docker stack.

---

### User Story 6 - Automated Delivery (Priority: P2)

As a Maintainer, I want every git push to trigger a matrix build (Linux/Mac/Windows) and publish artifacts, so that releases are automatic.

**Acceptance Scenarios**:

1. **Given** a push to `main`, **When** CI runs, **Then** it builds Rust (Shield) and Elixir (Brain) docker images and pushes to GHCR.
2. **Given** a new tag, **When** CI runs, **Then** it publishes the Python SDK to PyPI.

### Edge Cases

- **Connection Storms**: What happens when 10,000 users reconnect simultaneously? (Should throttle/backpressure, not crash).
- **Slow Consumers**: What happens when a client stops reading? (Server must drop messages/shed load, not OOM).
- **Protocol Mismatch**: What happens if a client sends valid JSON but invalid Protobuf schema? (Shield validates and rejects).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST implement the **Voltron Layering** (Shield -> Spine -> Brain) with strict isolation. See Constitution II.1.
- **FR-002**: The Shield (Rust) MUST terminate WebSockets and handle JWT validation (RS256) at the edge.
- **FR-003**: The Spine (NATS) MUST route messages based on `TenantID.RoomID` subjects.
- **FR-004**: The Brain (Elixir) MUST track Presence state using standard OTP patterns (Phoenix Presence/CRDTs).
- **FR-005**: The Protocol MUST use **Protobuf** for all internal and client-facing binary payloads.
- **FR-006**: The system MUST support **Wasm Middleware** chains in the Shield for payload inspection.
- **FR-007**: Messages MUST include `X-Twist-ID` and `X-Timestamp` headers in the envelope to support future TTC integration.
- **FR-008**: The system MUST enforce **Tenant Isolation** on every NATS publish/subscribe operation.
- **FR-009**: The project MUST provide immediate **Docker Compose** stacks for local dev (`docker compose up`).
- **FR-010**: The project MUST provide a **Python SDK** published to PyPI that wrappers the protocol.
- **FR-011**: The CI/CD pipeline MUST support **Matrix Builds** (Linux-x64, MacOS-ARM64, Windows-x64) for CLI tools.
- **FR-012**: The system MUST emit **OpenTelemetry** traces and metrics from both Rust and Elixir components.
- **FR-013**: The `arq` CLI tool MUST be provided as a single static binary for managing the lifecycle.
- **FR-014**: All Configuration MUST be defined via a strict **TOML Schema** with validation on startup (no loose env vars).

### Key Entities

- **Envelope**: The outer Protobuf wrapper containing Headers and Payload.
- **Session**: A stateful connection mapped to a `UserID` and `TenantID`.
- **Room**: A simplified topic/channel abstraction for grouping Sessions.
- **Manifest**: The `config.toml` definition of the running Node.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Connection Handshake (TCP + TLS + Auth) takes **< 100ms** at p99.
- **SC-002**: End-to-End Latency (Pub -> Sub) is **< 30ms** for intra-region clients.
- **SC-003**: A single Shield node can handle **10,000+** idle connections with **< 1GB** RAM usage.
- **SC-004**: Safety Policy evaluation adds **< 2ms** overhead per message.
