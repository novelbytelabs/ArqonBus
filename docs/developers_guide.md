# ArqonBus Developer Guide

This guide provides comprehensive information for developers who want to build applications with, extend, or contribute to ArqonBus.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Concepts](#core-concepts)
3. [API Reference](#api-reference)
4. [Message Protocol](#message-protocol)
5. [Extensibility](#extensibility)
6. [Custom Storage Backends](#custom-storage-backends)
7. [Custom Commands](#custom-commands)
8. [Authentication & Security](#authentication--security)
9. [Performance Tuning](#performance-tuning)
10. [Testing Strategies](#testing-strategies)
11. [Contributing Guidelines](#contributing-guidelines)
12. [Advanced Configuration](#advanced-configuration)
13. [Integration Patterns](#integration-patterns)

## Architecture Overview

### System Architecture

ArqonBus follows a layered architecture designed for scalability and maintainability:

```
┌─────────────────────────────────────────┐
│           Client Applications            │
├─────────────────────────────────────────┤
│              WebSocket Layer             │
├─────────────────────────────────────────┤
│            Protocol Layer                │
├─────────────────────────────────────────┤
│            Routing Layer                 │
├─────────────────────────────────────────┤
│            Command Layer                 │
├─────────────────────────────────────────┤
│            Storage Layer                 │
├─────────────────────────────────────────┤
│            Telemetry Layer               │
├─────────────────────────────────────────┤
│           Monitoring Layer               │
└─────────────────────────────────────────┘
```

### Core Components

1. **Transport Layer** (`src/arqonbus/transport/`)
   - `websocket_bus.py`: WebSocket server and connection management
   - `http_server.py`: HTTP monitoring and health endpoints

2. **Protocol Layer** (`src/arqonbus/protocol/`)
   - `envelope.py`: Message envelope definition and validation
   - `validator.py`: Protocol compliance validation
   - `ids.py`: Message and client identification

3. **Routing Layer** (`src/arqonbus/routing/`)
   - `router.py`: Central message routing coordination
   - `rooms.py`: Room-based message routing
   - `channels.py`: Channel-based message routing
   - `client_registry.py`: Client connection management

4. **Command Layer** (`src/arqonbus/commands/`)
   - `executor.py`: Command execution and validation
   - `builtin.py`: Built-in system commands
   - `base.py`: Command base classes and interfaces

5. **Storage Layer** (`src/arqonbus/storage/`)
   - `interface.py`: Storage backend interface
   - `memory.py`: In-memory storage implementation
   - `redis_streams.py`: Redis Streams implementation

6. **Telemetry Layer** (`src/arqonbus/telemetry/`)
   - `server.py`: Real-time telemetry event broadcasting
   - `emitter.py`: Telemetry event emission
   - `handlers.py`: Telemetry event handlers

## Core Concepts

### Message Envelope

All messages in ArqonBus follow a standardized envelope format:

```python
from arqonbus.protocol.envelope import MessageEnvelope

envelope = MessageEnvelope(
    id="msg-12345",
    type="message",  # message, command, event
    timestamp=datetime.utcnow(),
    sender="client-123",
    channel="general",
    content={
        "text": "Hello World",
        "metadata": {}
    },
    metadata={
        "client_info": "web-client",
        "priority": "normal"
    }
)
```

### Channels and Rooms

**Channels**: Persistent communication channels that can be created, joined, and left.

**Rooms**: Temporary communication spaces for specific use cases.

```python
# Join a channel
command = {
    "type": "command",
    "command": "join_channel",
    "channel": "general"
}

# Create a temporary room
command = {
    "type": "command", 
    "command": "create_room",
    "room": "game-session-123",
    "ttl": 3600  # 1 hour
}
```

### Storage Backends

ArqonBus supports pluggable storage backends:

- **Memory**: In-memory storage for development
- **Redis Streams**: Persistent storage with message streaming

## API Reference

### Server API

#### Creating and Starting a Server

```python
import asyncio
from arqonbus.server import ArqonBusServer
from arqonbus.config.config import ArqonBusConfig

# Load configuration
config = ArqonBusConfig.from_environment()

# Create server
server = ArqonBusServer(config)

# Start server
await server.start()

# Server is now running and accepting connections
```

#### Configuration

```python
from arqonbus.config.config import ArqonBusConfig

config = ArqonBusConfig()

# Server configuration
config.server.host = "0.0.0.0"
config.server.port = 9100
config.server.max_connections = 1000

# Storage configuration
config.storage.backend = "redis"
config.storage.max_history_size = 10000
config.storage.enable_persistence = True

# Redis configuration
config.redis.host = "redis.example.com"
config.redis.port = 6379
config.redis.password = "secret-password"
config.redis.ssl = True

# Security configuration
config.security.enable_authentication = True
config.security.allowed_commands = ["status", "ping", "history"]

# Start server with custom config
server = ArqonBusServer(config)
await server.start()
```

### Client API

#### WebSocket Connection

```python
import asyncio
import websockets
import json

class ArqonBusClient:
    def __init__(self, uri, token=None):
        self.uri = uri
        self.token = token
        self.websocket = None
        
    async def connect(self):
        self.websocket = await websockets.connect(self.uri)
        
    async def send_message(self, channel, content, sender=None):
        message = {
            "type": "message",
            "channel": channel,
            "content": content,
            "sender": sender or "anonymous"
        }
        await self.websocket.send(json.dumps(message))
        
    async def send_command(self, command, **kwargs):
        cmd = {
            "type": "command",
            "command": command,
            **kwargs
        }
        await self.websocket.send(json.dumps(cmd))
        
    async def listen(self):
        async for message in self.websocket:
            data = json.loads(message)
            await self.handle_message(data)
            
    async def handle_message(self, message):
        print(f"Received: {message}")
```

#### Client with Async Context Manager

```python
import asyncio
import websockets
import json

class ArqonBusClient:
    def __init__(self, uri):
        self.uri = uri
        self.websocket = None
        
    async def __aenter__(self):
        self.websocket = await websockets.connect(self.uri)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.websocket.close()
        
    async def send(self, data):
        await self.websocket.send(json.dumps(data))
        
    async def receive(self):
        message = await self.websocket.recv()
        return json.loads(message)

# Usage
async def main():
    async with ArqonBusClient("ws://localhost:9100") as client:
        await client.send({
            "type": "message",
            "channel": "general",
            "content": "Hello from async client!"
        })
        
        response = await client.receive()
        print(f"Response: {response}")

asyncio.run(main())
```

## Message Protocol

### Message Types

1. **Message**: Standard communication
2. **Command**: Server commands and operations
3. **Event**: System and telemetry events

### Message Structure

```json
{
  "id": "msg-unique-id",
  "type": "message|command|event",
  "timestamp": "2025-12-01T02:50:13.918Z",
  "sender": "client-id",
  "channel": "channel-name",
  "room": "optional-room-id",
  "content": {
    // Message content or command data
  },
  "metadata": {
    // Additional metadata
  }
}
```

### Built-in Commands

```python
# Status command
{
    "type": "command",
    "command": "status"
}

# Channel management
{
    "type": "command",
    "command": "create_channel",
    "channel": "my-channel"
}

{
    "type": "command",
    "command": "join_channel", 
    "channel": "my-channel"
}

{
    "type": "command",
    "command": "leave_channel",
    "channel": "my-channel"
}

{
    "type": "command",
    "command": "list_channels"
}

# Room management
{
    "type": "command",
    "command": "create_room",
    "room": "room-id",
    "ttl": 3600
}

# Message history
{
    "type": "command",
    "command": "history",
    "channel": "my-channel",
    "limit": 50
}

# Ping/pong
{
    "type": "command",
    "command": "ping"
}
```

## Extensibility

### Custom Message Types

Extend the message envelope with custom types:

```python
from arqonbus.protocol.envelope import MessageEnvelope
from enum import Enum

class CustomMessageType(Enum):
    SENSOR_DATA = "sensor_data"
    USER_ACTION = "user_action"
    SYSTEM_ALERT = "system_alert"

class SensorMessageEnvelope(MessageEnvelope):
    def __init__(self, sensor_id, sensor_type, value, timestamp=None):
        super().__init__(
            type="message",
            content={
                "sensor_id": sensor_id,
                "sensor_type": sensor_type,
                "value": value,
                "unit": "celsius"  # or whatever unit
            }
        )
        self.content["message_type"] = CustomMessageType.SENSOR_DATA.value

# Usage
sensor_msg = SensorMessageEnvelope(
    sensor_id="temp-001",
    sensor_type="temperature",
    value=23.5
)
```

### Custom Storage Backend

Create a custom storage implementation:

```python
from arqonbus.storage.interface import StorageBackend
import asyncio

class CustomDatabaseStorage(StorageBackend):
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.db_connection = None
        
    async def initialize(self):
        # Initialize database connection
        self.db_connection = await self.connect_to_database()
        
    async def store_message(self, message):
        # Store message in database
        await self.db_connection.execute(
            "INSERT INTO messages (id, channel, content, timestamp) VALUES (?, ?, ?, ?)",
            message.id, message.channel, message.content, message.timestamp
        )
        
    async def retrieve_messages(self, channel, limit=100):
        # Retrieve messages from database
        cursor = await self.db_connection.execute(
            "SELECT * FROM messages WHERE channel = ? ORDER BY timestamp DESC LIMIT ?",
            channel, limit
        )
        return await cursor.fetchall()
        
    async def close(self):
        # Close database connection
        if self.db_connection:
            await self.db_connection.close()

# Register the custom backend
from arqonbus.storage.interface import StorageRegistry

StorageRegistry.register_backend("custom_db", CustomDatabaseStorage)
```

### Custom Commands

Add your own commands to the system:

```python
from arqonbus.commands.base import BaseCommand

class CustomAnalyticsCommand(BaseCommand):
    name = "analytics"
    description = "Get channel analytics"
    
    async def execute(self, client_id, channel=None, time_range="1h"):
        # Your custom logic here
        if not channel:
            return self.error_response("Channel parameter required")
            
        # Get analytics data
        analytics = await self.get_channel_analytics(channel, time_range)
        
        return {
            "type": "command_response",
            "command": "analytics",
            "success": True,
            "data": analytics
        }
        
    async def get_channel_analytics(self, channel, time_range):
        # Implement your analytics logic
        return {
            "message_count": 150,
            "unique_users": 25,
            "peak_hour": "14:00",
            "avg_message_length": 45
        }

# Register the command
from arqonbus.commands.executor import CommandExecutor

CommandExecutor.register_command(CustomAnalyticsCommand())
```

## Custom Storage Backends

### Storage Interface

All storage backends must implement the `StorageBackend` interface:

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Any

class StorageBackend(ABC):
    @abstractmethod
    async def initialize(self):
        """Initialize the storage backend."""
        pass
        
    @abstractmethod
    async def store_message(self, message):
        """Store a message."""
        pass
        
    @abstractmethod
    async def retrieve_messages(self, channel: str, limit: int = 100) -> List[Any]:
        """Retrieve messages from a channel."""
        pass
        
    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if storage backend is healthy."""
        pass
        
    @abstractmethod
    async def close(self):
        """Close storage backend connections."""
        pass
```

### Example: File-based Storage

```python
import json
import os
from datetime import datetime
from arqonbus.storage.interface import StorageBackend

class FileStorage(StorageBackend):
    def __init__(self, storage_dir="./data"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
    async def initialize(self):
        # Nothing to initialize for file storage
        pass
        
    async def store_message(self, message):
        # Store message in file
        channel_file = os.path.join(self.storage_dir, f"{message.channel}.json")
        
        message_data = {
            "id": message.id,
            "type": message.type,
            "timestamp": message.timestamp.isoformat(),
            "sender": message.sender,
            "content": message.content
        }
        
        # Append to channel file
        if os.path.exists(channel_file):
            with open(channel_file, 'r') as f:
                messages = json.load(f)
        else:
            messages = []
            
        messages.append(message_data)
        
        with open(channel_file, 'w') as f:
            json.dump(messages, f, indent=2)
            
    async def retrieve_messages(self, channel, limit=100):
        channel_file = os.path.join(self.storage_dir, f"{channel}.json")
        
        if not os.path.exists(channel_file):
            return []
            
        with open(channel_file, 'r') as f:
            messages = json.load(f)
            
        # Return last 'limit' messages
        return messages[-limit:]
        
    async def is_healthy(self):
        # File storage is always healthy if we can write
        return os.access(self.storage_dir, os.W_OK)
        
    async def close(self):
        # Nothing to close for file storage
        pass

# Register the backend
from arqonbus.storage.interface import StorageRegistry
StorageRegistry.register_backend("file", FileStorage)
```

## Custom Commands

### Command Base Class

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseCommand(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Command name."""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Command description."""
        pass
        
    @abstractmethod
    async def execute(self, client_id: str, **kwargs) -> Dict[str, Any]:
        """Execute the command."""
        pass
        
    def error_response(self, message: str) -> Dict[str, Any]:
        """Standard error response."""
        return {
            "type": "command_response",
            "command": self.name,
            "success": False,
            "error": message
        }
        
    def success_response(self, data: Any = None) -> Dict[str, Any]:
        """Standard success response."""
        return {
            "type": "command_response", 
            "command": self.name,
            "success": True,
            "data": data
        }
```

### Example: Game Score Command

```python
class GameScoreCommand(BaseCommand):
    @property
    def name(self):
        return "game_score"
        
    @property 
    def description(self):
        return "Get or update game scores"
        
    async def execute(self, client_id: str, action: str = "get", game: str = None, score: int = None):
        if action == "get":
            return await self.get_scores(game)
        elif action == "update":
            return await self.update_score(client_id, game, score)
        else:
            return self.error_response("Invalid action")
            
    async def get_scores(self, game):
        # Get scores from your game database
        scores = [
            {"player": "Alice", "score": 1250},
            {"player": "Bob", "score": 1100},
            {"player": "Charlie", "score": 950}
        ]
        
        return self.success_response({
            "game": game,
            "scores": scores
        })
        
    async def update_score(self, client_id: str, game: str, score: int):
        # Update score in your game database
        print(f"Updating score for {client_id}: {game} = {score}")
        
        return self.success_response({
            "message": "Score updated successfully",
            "player": client_id,
            "game": game,
            "score": score
        })
```

## Authentication & Security

### Token-based Authentication

```python
import jwt
from arqonbus.security.auth import AuthenticationProvider

class JWTProvider(AuthenticationProvider):
    def __init__(self, secret_key):
        self.secret_key = secret_key
        
    async def authenticate(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return {
                "valid": True,
                "user_id": payload["user_id"],
                "permissions": payload.get("permissions", [])
            }
        except jwt.InvalidTokenError:
            return {"valid": False}
            
    async def authorize(self, user: Dict[str, Any], command: str) -> bool:
        permissions = user.get("permissions", [])
        return command in permissions

# Configure authentication
config.security.enable_authentication = True
config.security.auth_provider = JWTProvider("your-secret-key")
```

### Custom Authentication

```python
class CustomAuthProvider:
    def __init__(self):
        self.users = {
            "user1": {"password": "hash1", "permissions": ["read", "write"]},
            "user2": {"password": "hash2", "permissions": ["read"]}
        }
        
    async def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        user = self.users.get(username)
        if user and user["password"] == self.hash_password(password):
            return {
                "valid": True,
                "user_id": username,
                "permissions": user["permissions"]
            }
        return {"valid": False}
        
    def hash_password(self, password: str) -> str:
        # Your password hashing logic
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
```

## Performance Tuning

### Connection Pooling

```python
# Optimize Redis connection pooling
config.redis.connection_pool_size = 20
config.redis.timeout = 5.0

# Optimize WebSocket settings
config.websocket.max_message_size = 2 * 1024 * 1024  # 2MB
config.websocket.compression = True
```

### Memory Management

```python
# Limit memory storage
config.storage.max_history_size = 5000
config.storage.retention_hours = 6

# Configure garbage collection
import gc
gc.set_threshold(700, 10, 10)
```

### Batch Operations

```python
# Enable batch message processing
class BatchMessageHandler:
    def __init__(self, batch_size=100):
        self.batch_size = batch_size
        self.pending_messages = []
        
    async def add_message(self, message):
        self.pending_messages.append(message)
        
        if len(self.pending_messages) >= self.batch_size:
            await self.flush_batch()
            
    async def flush_batch(self):
        if self.pending_messages:
            # Process batch
            await self.process_batch(self.pending_messages)
            self.pending_messages = []
```

## Testing Strategies

### Unit Tests

```python
import pytest
import asyncio
from arqonbus.server import ArqonBusServer
from arqonbus.config.config import ArqonBusConfig

@pytest.fixture
async def test_server():
    config = ArqonBusConfig()
    config.server.port = 9101  # Different port for testing
    config.storage.backend = "memory"
    
    server = ArqonBusServer(config)
    await server.start()
    yield server
    await server.stop()

@pytest.mark.asyncio
async def test_server_health(test_server):
    # Test server health endpoint
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:9101/health") as resp:
            data = await resp.json()
            assert data["status"] == "healthy"

@pytest.mark.asyncio  
async def test_message_routing(test_server):
    # Test message routing
    import websockets
    
    async with websockets.connect("ws://localhost:9101") as websocket:
        # Send a test message
        message = {
            "type": "message",
            "channel": "test",
            "content": "Hello test"
        }
        await websocket.send(json.dumps(message))
        
        # Receive and verify
        response = await websocket.recv()
        data = json.loads(response)
        assert data["channel"] == "test"
        assert data["content"] == "Hello test"
```

### Integration Tests

```python
@pytest.mark.integration
async def test_redis_integration():
    config = ArqonBusConfig()
    config.storage.backend = "redis"
    config.redis.host = "localhost"
    
    server = ArqonBusServer(config)
    await server.start()
    
    # Test Redis persistence
    # ... test code ...
    
    await server.stop()

@pytest.mark.integration
async def test_multiple_clients():
    # Test with multiple concurrent clients
    import asyncio
    
    async def client_task(client_id):
        async with websockets.connect("ws://localhost:9101") as websocket:
            # Client logic here
            pass
            
    # Create multiple clients
    tasks = [client_task(f"client_{i}") for i in range(10)]
    await asyncio.gather(*tasks)
```

### Performance Tests

```python
import time
import asyncio

async def test_message_throughput():
    async def send_messages(num_messages):
        start_time = time.time()
        async with websockets.connect("ws://localhost:9101") as websocket:
            for i in range(num_messages):
                message = {
                    "type": "message",
                    "channel": "perf_test",
                    "content": f"Message {i}"
                }
                await websocket.send(json.dumps(message))
                
        end_time = time.time()
        return num_messages / (end_time - start_time)
        
    throughput = await send_messages(1000)
    assert throughput > 500  # Expect at least 500 messages/second
```

## Contributing Guidelines

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/arqonbus.git
cd arqonbus

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

### Code Style

- Follow PEP 8 for Python code
- Use type hints where possible
- Write docstrings for all public methods
- Use async/await for all I/O operations

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes with tests
4. Run the test suite: `pytest`
5. Update documentation if needed
6. Commit your changes: `git commit -m 'Add amazing feature'`
7. Push to the branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

### Release Process

1. Update version in `__init__.py`
2. Update `CHANGELOG.md`
3. Create release PR
4. After merge, create GitHub release

## Advanced Configuration

### Multi-instance Deployment

```python
# Load balancer configuration
config.server.host = "0.0.0.0"
config.server.max_connections = 500  # Lower per instance

# Shared Redis for message coordination
config.redis.cluster_nodes = [
    "redis1.example.com:6379",
    "redis2.example.com:6379", 
    "redis3.example.com:6379"
]

# Instance identification
config.instance_id = "arqonbus-01"
config.coordination_channel = "arqonbus-coordination"
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: arqonbus
spec:
  replicas: 3
  selector:
    matchLabels:
      app: arqonbus
  template:
    metadata:
      labels:
        app: arqonbus
    spec:
      containers:
      - name: arqonbus
        image: arqonbus:latest
        env:
        - name: ARQONBUS_SERVER_HOST
          value: "0.0.0.0"
        - name: ARQONBUS_STORAGE_BACKEND
          value: "redis"
        - name: ARQONBUS_REDIS_HOST
          value: "redis-service"
        ports:
        - containerPort: 9100
---
apiVersion: v1
kind: Service
metadata:
  name: arqonbus-service
spec:
  selector:
    app: arqonbus
  ports:
  - port: 9100
    targetPort: 9100
  type: LoadBalancer
```

### Monitoring Integration

```python
# Prometheus metrics integration
from prometheus_client import Counter, Histogram, Gauge

# Define custom metrics
message_counter = Counter('arqonbus_messages_total', 'Total messages processed')
connection_gauge = Gauge('arqonbus_connections_active', 'Active connections')
processing_time = Histogram('arqonbus_processing_seconds', 'Message processing time')

# Custom metrics in message handler
@processing_time.time()
async def handle_message(message):
    message_counter.inc()
    connection_gauge.set(get_active_connections())
    
    # Message processing logic
    pass
```

## Integration Patterns

### Microservices Communication

```python
class MicroserviceBus:
    def __init__(self, service_name, bus_url):
        self.service_name = service_name
        self.client = ArqonBusClient(bus_url)
        
    async def register_service(self):
        await self.client.send_command(
            "join_channel",
            channel=f"services/{self.service_name}"
        )
        
    async def send_event(self, event_type, data):
        await self.client.send_message(
            channel="services/events",
            content={
                "service": self.service_name,
                "event": event_type,
                "data": data
            }
        )
        
    async def listen_for_events(self, callback):
        async for message in self.client.listen():
            if message["channel"] == "services/events":
                await callback(message)

# Usage
async def user_service():
    bus = MicroserviceBus("user-service", "ws://localhost:9100")
    await bus.register_service()
    
    async def handle_notification(event):
        # Handle service-to-service notification
        print(f"Received event: {event}")
        
    await bus.listen_for_events(handle_notification)
```

### Real-time Dashboard

```python
class DashboardClient:
    def __init__(self, bus_url):
        self.bus_url = bus_url
        self.metrics_data = {}
        
    async def connect(self):
        self.websocket = await websockets.connect(self.bus_url)
        
        # Subscribe to relevant channels
        await self.subscribe_to_metrics()
        
    async def subscribe_to_metrics(self):
        metrics_channels = [
            "metrics.system",
            "metrics.business",
            "metrics.performance"
        ]
        
        for channel in metrics_channels:
            await self.websocket.send(json.dumps({
                "type": "command",
                "command": "join_channel",
                "channel": channel
            }))
            
    async def update_dashboard(self, callback):
        async for message in self.websocket:
            data = json.loads(message)
            if data["type"] == "message":
                await callback(data["channel"], data["content"])

# Dashboard web interface
async def dashboard_app():
    client = DashboardClient("ws://localhost:9100")
    await client.connect()
    
    def update_ui(channel, content):
        # Update dashboard UI with new data
        print(f"Updating {channel}: {content}")
        
    await client.update_dashboard(update_ui)
```

This comprehensive developer guide covers all aspects of working with ArqonBus, from basic usage to advanced customization and deployment patterns. It serves as the definitive resource for developers building applications on or extending the ArqonBus platform.