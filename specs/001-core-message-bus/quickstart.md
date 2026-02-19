# Quickstart Guide: ArqonBus v1.0 Integration Scenarios

**Feature**: 001-core-message-bus  
**Created**: 2025-11-30  
**Use Cases**: Integration examples and test scenarios

## Overview

This quickstart guide provides concrete integration scenarios for ArqonBus v1.0, demonstrating how to connect, communicate, and leverage the message bus for various use cases.

## Integration Scenarios

### Scenario 1: Basic Chat Application

**Use Case**: Simple multi-user chat with rooms and channels  
**Client Type**: Web application (JavaScript)  
**Architecture**: Browser → WebSocket → ArqonBus → Broadcast to room members

**Setup Steps**:
1. Connect to ArqonBus WebSocket endpoint
2. Join default room (science) and channel (general)
3. Send and receive chat messages
4. Monitor connection status and handle disconnects

**Message Flow**:
```
Client A → science:general → Client B, Client C
Client B → science:explore → Client A (if subscribed)
```

**Code Example** (JavaScript):
```javascript
// Connect to ArqonBus
const ws = new WebSocket('ws://localhost:9100');

// Subscribe to default channel
const subscription = {
  version: "1.0",
  id: "arq_sub_001",
  type: "command",
  room: "science",
  channel: "general",
  from: "web_client_1",
  timestamp: new Date().toISOString(),
  payload: { command: "join_channel", parameters: {} }
};

// Send chat message
const message = {
  version: "1.0",
  id: "arq_msg_001",
  type: "event",
  room: "science",
  channel: "general",
  from: "web_client_1",
  timestamp: new Date().toISOString(),
  payload: { message: "Hello everyone!" }
};
```

---

### Scenario 2: Real-time Dashboard

**Use Case**: Monitoring dashboard displaying system metrics  
**Client Type**: Dashboard (dedicated monitoring client)  
**Architecture**: Dashboard → WebSocket → Subscribe to telemetry stream

**Setup Steps**:
1. Connect to main ArqonBus server
2. Subscribe to integriguard:telemetry-stream channel
3. Connect to telemetry WebSocket server for additional events
4. Display real-time metrics and system status

**Message Flow**:
```
System Events → integriguard:telemetry-stream → Dashboard Client
Telemetry Server → integriguard:dashboard-events → Dashboard Client
```

**Key Features**:
- Real-time system metrics
- Client connection/disconnection events
- Message volume tracking
- Room/channel utilization

---

### Scenario 3: Multi-Agent Communication

**Use Case**: AI agents coordinating through structured channels  
**Client Type**: AI agents with specialized behaviors  
**Architecture**: Agent A ↔ Room:Channel ↔ Agent B with history persistence

**Setup Steps**:
1. Connect AI agents with personality configurations
2. Subscribe to dedicated room (e.g., research:coordination)
3. Exchange structured messages with metadata
4. Use private channels for direct agent-to-agent communication

**Message Example** (AI Agent):
```json
{
  "version": "1.0",
  "id": "arq_agent_001",
  "type": "event",
  "room": "research",
  "channel": "coordination",
  "from": "research_agent_1",
  "timestamp": "2025-01-01T12:00:00.000Z",
  "payload": {
    "message": "Starting analysis phase",
    "metadata": {
      "personality": "analytical",
      "priority": "high",
      "expected_duration": "5_minutes"
    }
  }
}
```

**AI Agent Activity Tracking**:
- Automatic emission of agent_activity events
- Personality-based routing optimization
- Coordination channel monitoring

---

### Scenario 4: Enterprise Integration

**Use Case**: Service-to-service communication within enterprise  
**Client Type**: Backend services (Python)  
**Architecture**: Service A → Redis-backed persistence → Service B (with history)

**Setup Steps**:
1. Configure ArqonBus with Redis Streams persistence
2. Connect backend services with service-type classification
3. Use dedicated service channels for command/response patterns
4. Leverage message history for audit trails

**Message Pattern** (Command/Response):
```json
// Command from Service A
{
  "version": "1.0",
  "id": "arq_cmd_001",
  "type": "command",
  "room": "services",
  "channel": "database",
  "from": "api_service",
  "timestamp": "2025-01-01T12:00:00.000Z",
  "payload": {
    "command": "status",
    "parameters": { "check": "connection_pool" }
  }
}

// Response from Database Service
{
  "version": "1.0",
  "id": "arq_resp_001",
  "type": "command_response",
  "room": "services",
  "channel": "database",
  "from": "db_service",
  "timestamp": "2025-01-01T12:00:00.025Z",
  "payload": {
    "request_id": "arq_cmd_001",
    "status": "success",
    "result": {
      "active_connections": 15,
      "max_connections": 100,
      "avg_response_time_ms": 2.3
    }
  }
}
```

---

### Scenario 5: High-Availability Deployment

**Use Case**: Production deployment with monitoring and health checks  
**Client Type**: Multiple clients in various environments  
**Architecture**: Load balancer → Multiple ArqonBus instances → Shared Redis backend

**Setup Steps**:
1. Deploy multiple ArqonBus instances behind load balancer
2. Configure shared Redis Streams for cross-instance message persistence
3. Set up HTTP endpoints for health monitoring
4. Configure Prometheus metrics collection

**Health Check Integration**:
```bash
# Kubernetes liveness probe
curl -f http://arqonbus:8080/health

# Prometheus metrics
curl http://arqonbus:8080/metrics | grep arqonbus_active_clients
```

**Redis Configuration**:
```bash
export ARQONBUS_REDIS_URL=redis://redis-cluster:6379
export ARQONBUS_STORAGE=redis
export ARQONBUS_HISTORY_SIZE=1000
```

---

## Testing Scenarios

### Connection Testing
1. **Single Client Connection**: Verify basic connection and handshake
2. **Multiple Concurrent Clients**: Test 100+ simultaneous connections
3. **Connection Drop/Recovery**: Simulate network interruptions
4. **Resource Exhaustion**: Test behavior under connection limits

### Message Routing Testing
1. **Room-based Routing**: Messages delivered only to subscribed rooms
2. **Channel-based Filtering**: Fine-grained routing within rooms
3. **Private Message Delivery**: Direct client-to-client communication
4. **Message History Retrieval**: Redis-backed history queries

### Command Testing
1. **Built-in Commands**: status, ping, list_channels, channel_info
2. **Channel Management**: create_channel, delete_channel, join_channel, leave_channel
3. **Authorization**: Admin-only command restrictions
4. **Error Handling**: Invalid commands and parameters

### Performance Testing
1. **Message Throughput**: 10,000+ messages per second
2. **Latency Testing**: p99 < 50ms routing time
3. **Memory Usage**: Efficient handling of large numbers of clients
4. **Redis Performance**: Persistence performance under load

### Failure Mode Testing
1. **Redis Unavailability**: Graceful degradation to memory mode
2. **Network Partitions**: Handling of temporary disconnections
3. **Malformed Messages**: Protocol validation and rejection
4. **Resource Exhaustion**: Behavior under memory/CPU constraints

## Common Integration Patterns

### Request/Response Pattern
Use commands with command_response for synchronous operations:
- Database queries
- Status checks
- Configuration requests

### Pub/Sub Pattern
Use events for asynchronous broadcast communication:
- Real-time updates
- System notifications
- Analytics events

### Private Messaging
Use private message type for direct client communication:
- User-to-user chat
- Service-to-service communication
- Critical alerts

### Telemetry Integration
Monitor system health through dedicated telemetry channels:
- System metrics
- Performance monitoring
- Usage analytics

## Best Practices

### Client Design
- Implement robust reconnection logic
- Handle protocol violations gracefully
- Use structured payload data
- Include appropriate metadata

### Message Design
- Keep payloads concise and structured
- Use meaningful room/channel naming
- Include relevant metadata for routing
- Follow version compatibility guidelines

### Error Handling
- Validate messages before sending
- Handle command failures appropriately
- Implement backoff strategies for reconnection
- Log errors with sufficient context

### Performance Optimization
- Batch messages when appropriate
- Use appropriate client types
- Monitor message rates and sizes
- Leverage persistence only when needed