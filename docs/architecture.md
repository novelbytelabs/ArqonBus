# ArqonBus Architecture

ArqonBus is built on a layered, modular architecture designed for reliability, scalability, and ease of integration.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Applications                     │
│              (WebSocket + HTTP Monitoring)                  │
└─────────────────┬───────────────────────────────────────────┘ 
                  │ WebSocket + HTTP                            
┌─────────────────┴─────────────────────────────────────────────┐
│                     ArqonBus Core                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   WebSocket │  │    HTTP     │  │  Telemetry  │            │
│  │   Server    │  │   Server    │  │   Server    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Message Router                              │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │ │
│  │  │    Rooms    │ │   Channels  │ │  Client Registry    │ │ │
│  │  │   Manager   │ │   Manager   │ │                     │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Command Executor                            │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │ │
│  │  │ Built-in    │ │ Authorization│ │   Validation       │ │ │
│  │  │ Commands    │ │    System    │ │   System           │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Storage Backends                            │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │ │
│  │  │   Memory    │ │    Redis    │ │   Storage Interface │ │ │
│  │  │  Storage    │ │   Streams   │ │                     │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

## Core Components

### Transport Layer

**WebSocket Server** (`src/arqonbus/transport/websocket_bus.py`)

- Handles WebSocket connections and message routing
- Supports connection lifecycle management
- Implements message validation and protocol enforcement
- Manages client sessions and heartbeats

**HTTP Server** (`src/arqonbus/transport/http_server.py`)

- Provides REST endpoints for monitoring and administration
- Health checks and status reporting
- Metrics collection and Prometheus export
- Storage history queries

### Protocol Layer

**Message Envelope** (`src/arqonbus/protocol/envelope.py`)

- Structured message format with required fields
- JSON serialization/deserialization
- Type-safe message validation
- ID generation with `arq_` prefix convention

**Message Validator** (`src/arqonbus/protocol/validator.py`)

- Comprehensive message validation
- Command-specific validation rules
- Timestamp and ID format validation
- Target entity validation (client/room/channel)

### Routing Layer

**Message Router** (`src/arqonbus/routing/router.py`)

- Central routing coordination
- Room and channel management
- Message delivery orchestration
- Routing statistics and monitoring

**Client Registry** (`src/arqonbus/routing/client_registry.py`)

- Client connection tracking
- Room and channel membership management
- Connection lifecycle events
- Client metadata storage

**Rooms Manager** (`src/arqonbus/routing/rooms.py`)

- Room-based message routing
- Member management
- Broadcast capabilities
- Room lifecycle management

**Channels Manager** (`src/arqonbus/routing/channels.py`)

- Channel-based message routing
- Channel creation and deletion
- Message broadcasting
- Channel membership

### Command System

**Command Executor** (`src/arqonbus/commands/executor.py`)

- Command registration and discovery
- Parameter validation
- Execution orchestration
- Response formatting

**Built-in Commands** (`src/arqonbus/commands/builtin.py`)

- Status reporting
- Channel management
- Room operations
- System information

**Command Authorization** (`src/arqonbus/commands/auth.py`)

- Role-based access control
- Rate limiting
- Permission validation
- Security enforcement

### Storage Layer

**Storage Interface** (`src/arqonbus/storage/interface.py`)

- Abstract storage backend interface
- Common storage operations
- Storage health monitoring
- Backend registry

**Memory Storage** (`src/arqonbus/storage/memory.py`)

- In-memory message storage
- Thread-safe operations
- Ring buffer implementation
- Fast access patterns

**Redis Streams** (`src/arqonbus/storage/redis_streams.py`)

- Redis-based persistent storage
- Stream-based message organization
- Automatic fallback to memory storage
- Stream cleanup and maintenance

### Telemetry Layer

**Telemetry Server** (`src/arqonbus/telemetry/server.py`)

- WebSocket-based telemetry broadcasting
- Event buffering and batching
- Client connection management
- Performance monitoring

**Telemetry Handler** (`src/arqonbus/telemetry/handlers.py`)

- Event validation and enrichment
- Event filtering and processing
- Batch processing
- Event aggregation

**Telemetry Emitter** (`src/arqonbus/telemetry/emitter.py`)

- Centralized event emission
- Event type definitions
- Subscriber management
- Event buffering

### Monitoring Layer

**Metrics Collector** (`src/arqonbus/utils/metrics.py`)

- System metrics collection
- Command execution metrics
- Performance monitoring
- Histogram and counter tracking

**Prometheus Exporter** (`src/arqonbus/utils/prometheus.py`)

- Prometheus format export
- Metric naming and labeling
- Health check integration
- Performance metrics

**Structured Logging** (`src/arqonbus/utils/logging.py`)

- Structured log formatting
- Performance logging
- Business event tracking
- Contextual logging

## Configuration Management

**Config System** (`src/arqonbus/config/config.py`)

- Environment-based configuration
- Configuration validation
- Default value management
- Configuration hot-reloading

## Message Flow

### Basic Message Flow
1. **Client Connection**: WebSocket connection established
2. **Message Reception**: Message received and validated
3. **Routing Decision**: Router determines message destination(s)
4. **Storage**: Message stored in appropriate backend(s)
5. **Delivery**: Message delivered to target client(s)
6. **Telemetry**: Event emitted for monitoring

### Command Execution Flow
1. **Command Reception**: Command message validated
2. **Authorization**: Client permissions checked
3. **Validation**: Command parameters validated
4. **Execution**: Command executed with metrics
5. **Response**: Result formatted and sent back
6. **Telemetry**: Command event recorded

### Room/Channel Messaging
1. **Join Operation**: Client joins room/channel
2. **Message Routing**: Router identifies routing targets
3. **Member Lookup**: Registry provides member list
4. **Message Distribution**: Message sent to all members
5. **Storage**: Message stored for history
6. **Telemetry**: Join/leave events recorded

## Error Handling and Resilience

### Graceful Degradation
- **Redis Unavailable**: Automatic fallback to memory storage
- **Telemetry Failures**: Core messaging continues unaffected
- **HTTP Server Failures**: WebSocket server remains operational
- **Connection Failures**: Automatic retry and health monitoring

### Thread Safety
- **Storage Operations**: Thread-safe storage backends
- **Connection Management**: Lock-free connection tracking
- **Message Routing**: Atomic routing operations
- **Metrics Collection**: Thread-safe metric updates

### Health Monitoring
- **Component Health**: Regular health checks for all components
- **Performance Monitoring**: Continuous performance tracking
- **Error Tracking**: Comprehensive error logging
- **Connection Monitoring**: WebSocket connection health

## Scalability Considerations

### Horizontal Scaling
- **Stateless Design**: Minimal per-process state
- **External Storage**: Redis for shared state
- **Load Balancing**: Multiple server instances
- **Session Affinity**: Optional for WebSocket connections

### Performance Optimization
- **Connection Pooling**: Efficient Redis connection management
- **Message Batching**: Batch processing for telemetry
- **Memory Management**: Ring buffers and cleanup
- **Lock Optimization**: Fine-grained locking strategies

### Monitoring Integration
- **Prometheus Metrics**: Standard metrics export
- **Health Endpoints**: REST-based health checks
- **Telemetry Events**: Real-time event streaming
- **Structured Logging**: Comprehensive log aggregation

## Security Model

### Connection Security
- **WebSocket Security**: Standard WS/WSS protocols
- **Client Identification**: Unique client IDs with validation
- **Connection Limits**: Configurable connection limits

### Authorization
- **Role-Based Access**: Admin, user, and guest roles
- **Command Authorization**: Per-command permission checks
- **Rate Limiting**: Configurable rate limits per client

### Data Protection
- **Message Validation**: Comprehensive input validation
- **ID Format Validation**: Enforced ID format requirements
- **Timestamp Validation**: Reasonable timestamp ranges

## Configuration

The system is configured through environment variables and configuration files:

### Server Configuration
- `ARQONBUS_SERVER_HOST`: Server host address
- `ARQONBUS_SERVER_PORT`: Server port
- `ARQONBUS_LOG_LEVEL`: Logging level

### Storage Configuration
- `ARQONBUS_STORAGE_BACKEND`: Storage backend type
- `ARQONBUS_STORAGE_MAX_HISTORY`: Maximum history size
- `ARQONBUS_REDIS_URL`: Redis connection URL

### Telemetry Configuration
- `ARQONBUS_TELEMETRY_ENABLED`: Enable telemetry
- `ARQONBUS_TELEMETRY_PORT`: Telemetry server port
- `ARQONBUS_TELEMETRY_HOST`: Telemetry server host

### HTTP Configuration
- `ARQONBUS_HTTP_ENABLED`: Enable HTTP monitoring
- `ARQONBUS_HTTP_PORT`: HTTP server port
- `ARQONBUS_HTTP_HOST`: HTTP server host

## Performance Characteristics

### Throughput
- **Messages per Second**: 1000+ messages/sec per instance
- **Concurrent Connections**: 1000+ WebSocket connections
- **Command Response Time**: <100ms average response time
- **Message Latency**: <50ms end-to-end latency

### Resource Usage
- **Memory Usage**: ~50MB base + 1KB per connection
- **CPU Usage**: <5% under normal load
- **Storage**: Configurable based on history retention

### Scalability
- **Horizontal Scaling**: Linear scaling with instances
- **Storage Scaling**: Redis Streams for high-volume storage
- **Network Scaling**: Load balancer support

## Development and Testing

### Test Structure
- **Unit Tests**: Component-level testing
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Load and stress testing
- **Contract Tests**: Protocol compliance testing

### Development Tools
- **Ruff**: Code formatting and linting
- **Black**: Code formatting
- **MyPy**: Type checking
- **pytest**: Test framework

### CI/CD Integration
- **Automated Testing**: All tests run on each commit
- **Performance Testing**: Regular performance regression testing
- **Security Scanning**: Automated security vulnerability scanning
- **Documentation**: Automated documentation generation