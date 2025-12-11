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

### Key Entities

- **Envelope**: The outer Protobuf wrapper containing Headers and Payload.
- **Session**: A stateful connection mapped to a `UserID` and `TenantID`.
- **Room**: A simplified topic/channel abstraction for grouping Sessions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Connection Handshake (TCP + TLS + Auth) takes **< 100ms** at p99.
- **SC-002**: End-to-End Latency (Pub -> Sub) is **< 30ms** for intra-region clients.
- **SC-003**: A single Shield node can handle **10,000+** idle connections with **< 1GB** RAM usage.
- **SC-004**: Safety Policy evaluation adds **< 2ms** overhead per message.
