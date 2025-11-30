# Feature Specification: ArqonBus v1.0 Core Message Bus

**Feature Branch**: `001-core-message-bus`  
**Created**: 2025-11-30  
**Status**: Draft  
**Input**: Implement ArqonBus v1.0 - structured WebSocket message bus with rooms, channels, commands, optional Redis Streams, and telemetry

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real-Time Message Bus Foundation (Priority: P1)

Developers need a simple, reliable WebSocket server that can handle real-time messaging between connected clients through organized routing using rooms and channels.

**Why this priority**: This forms the core infrastructure that all other features build upon. Without the basic WebSocket server and room/channel routing, no messaging functionality exists.

**Independent Test**: Can be fully tested by starting the server, connecting multiple WebSocket clients, having them join different rooms and channels, and sending messages that are properly routed to the intended recipients based on room/channel subscriptions.

**Acceptance Scenarios**:

1. **Given** a running ArqonBus server, **When** multiple clients connect via WebSocket and subscribe to different rooms/channels, **Then** clients receive messages only from rooms and channels they are subscribed to
2. **Given** clients connected to different rooms (e.g., "science:general" vs "chat:public"), **When** a message is sent to "science:explore", **Then** only clients subscribed to the science room and explore channel receive that message
3. **Given** a client connected to "room:channel", **When** the client disconnects unexpectedly, **Then** the server gracefully handles the disconnect and removes them from their subscriptions

---

### User Story 2 - Structured Protocol and Built-in Commands (Priority: P2)

Applications need a consistent, versioned message format and server-side commands for introspection, channel management, and basic operations.

**Why this priority**: Once the messaging foundation exists, users need a predictable protocol format and basic administrative capabilities to manage channels, check server status, and troubleshoot connectivity issues.

**Independent Test**: Can be fully tested by sending messages with the required envelope format, issuing built-in commands (status, create_channel, delete_channel, join_channel, leave_channel, list_channels, channel_info, ping), and verifying responses match expected protocol specifications.

**Acceptance Scenarios**:

1. **Given** clients connected to the server, **When** a client sends a command with type "status", **Then** the server responds with detailed information about connected clients, active rooms, channels, and participant counts
2. **Given** a properly formatted message envelope with version "1.0", **When** the message is processed, **Then** it is validated against the strict schema and either accepted or rejected with appropriate error handling
3. **Given** an authorized client, **When** they issue create_channel for "newroom:testchannel", **Then** the channel is created with appropriate metadata and made available for other clients to join

---

### User Story 3 - Persistence and Observability (Priority: P3)

Organizations need optional message durability for important conversations and observability capabilities for monitoring system health and debugging issues.

**Why this priority**: While the core messaging provides immediate value, persistence and telemetry transform ArqonBus from a simple message relay into a production-ready infrastructure component suitable for business-critical applications.

**Independent Test**: Can be fully tested by configuring Redis Streams, sending messages to various channels, checking message history retrieval, monitoring telemetry streams, and verifying that system metrics are properly exposed via HTTP endpoints.

**Acceptance Scenarios**:

1. **Given** Redis Streams is configured, **When** clients send messages to channels, **Then** messages persist beyond client connections and can be retrieved using the history command with configurable retention periods
2. **Given** telemetry is enabled, **When** clients connect, send messages, and disconnect, **Then** activity events are broadcast to the integriguard:telemetry-stream and agent_activity events are sent to dashboard-events
3. **Given** HTTP endpoints are available, **When** requests are made to /health, /metrics, and /version, **Then** appropriate responses are returned with current system status, Prometheus-formatted metrics, and version information

### Edge Cases

- What happens when maximum room/channel participant limits are reached?
- How does system handle network partitions where clients lose connection but attempt to send messages?
- How does server behave when all configured system rooms cannot be created at startup?
- What occurs when clients send malformed message envelopes or unauthorized commands?
- How does the system recover when Redis Streams becomes unavailable during operation?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a real-time WebSocket server that handles persistent, bi-directional connections with configurable host and port settings
- **FR-002**: System MUST support structured routing through rooms (logical namespaces) and channels (sub-streams within rooms) using room:channel format
- **FR-003**: System MUST implement a strict, versioned message envelope with required fields: version, id, type, room, channel, from, timestamp, payload, and optional metadata
- **FR-004**: System MUST provide built-in server commands: status, create_channel, delete_channel, join_channel, leave_channel, list_channels, channel_info, ping, and history
- **FR-005**: System MUST support optional persistence via Redis Streams while defaulting to in-memory FIFO ring buffer with configurable size
- **FR-006**: System MUST implement separate telemetry WebSocket server on configurable port for monitoring and activity event broadcasting
- **FR-007**: System MUST expose minimal HTTP endpoints: /health (liveness), /version (server/protocol versions), /metrics (Prometheus format)
- **FR-008**: System MUST support client types (human, ai-agent, dashboard, service) with metadata including client_id, screen_name, avatar, personality, connected_at, last_activity
- **FR-009**: System MUST handle error scenarios: malformed envelopes, unknown commands, protocol violations, Redis failures, with appropriate logging and graceful degradation
- **FR-010**: System MUST reject malformed message envelopes and disconnect clients on repeated protocol violations
- **FR-011**: System MUST validate telemetry events with required eventType and payload fields, broadcasting to integriguard:telemetry-stream
- **FR-012**: System MUST emit lightweight agent_activity events for AI agents to integriguard:dashboard-events channel

### Key Entities

- **Message**: Structured data unit with versioned envelope containing id, type, room, channel, sender, timestamp, payload, and metadata
- **Client**: Connected entity with unique id, type classification, optional metadata (screen_name, avatar, personality), connection state, and room/channel subscriptions
- **Room**: Logical namespace containing multiple channels, created on demand or via configuration, supporting hierarchical routing
- **Channel**: Sub-stream within a room identified by room:channel format, primary routing unit, may be auto-created based on configuration
- **Command**: Server-processed message with type "command" for administrative functions (status, channel management, history retrieval, connectivity testing)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System handles 5,000 concurrent WebSocket connections on a single node without degradation
- **SC-002**: Message routing latency achieves p99 under 50ms for local network communication
- **SC-003**: Server achieves 100% reliability with no message loss when Redis Streams persistence is enabled
- **SC-004**: All built-in commands respond within 100ms under normal operating conditions
- **SC-005**: Message envelope validation rejects 100% of malformed messages while accepting all properly formatted messages
- **SC-006**: HTTP endpoints maintain 99.9% availability for health checks and metrics collection
- **SC-007**: Telemetry system broadcasts activity events within 500ms of occurrence to subscribed monitoring systems
- **SC-008**: Channel creation and management operations complete successfully in 95% of cases within 1 second
- **SC-009**: System supports protocol versioning to enable future compatibility while maintaining backward compatibility
- **SC-010**: At least one client SDK (JavaScript or Python) demonstrates successful full-duplex communication following the established protocol