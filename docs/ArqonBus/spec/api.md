# ArqonBus API Documentation

## Overview

ArqonBus provides a WebSocket-based message bus with REST endpoints for monitoring. This document covers the complete API surface including message protocols, commands, and monitoring endpoints.

## WebSocket Protocol

### Connection

Connect to the WebSocket endpoint:
```
ws://localhost:9100
```

### Message Envelope Format

All messages use a structured JSON envelope format:

```json
{
  "id": "arq_msg_1234567890",
  "type": "message|command",
  "timestamp": "2025-11-30T23:18:00Z",
  "from_client": "arq_client_123",
  "to_client": "arq_client_456",      // Optional: direct message
  "room": "arq_room_general",         // Optional: room message
  "channel": "arq_channel_tech",      // Optional: channel message
  "payload": {                        // Message content
    "content": "Hello world!"
  }
}
```

### Required Fields

- **id**: Unique message identifier (must start with `arq_`)
- **type**: Message type (`message` or `command`)
- **timestamp**: ISO 8601 timestamp
- **from_client**: Sender client ID (must start with `arq_`)
- **payload**: Message content object

### Target Specification

At least one target must be specified:
- **to_client**: Direct message to specific client
- **room**: Broadcast to room members
- **channel**: Broadcast to channel members

## Message Types

### Regular Messages

Send a regular message:

```json
{
  "id": "arq_msg_001",
  "type": "message",
  "timestamp": "2025-11-30T23:18:00Z",
  "from_client": "arq_client_alice",
  "to_client": "arq_client_bob",
  "payload": {
    "content": "Hello Bob!"
  }
}
```

### Room Messages

Send a message to a room:

```json
{
  "id": "arq_msg_002",
  "type": "message",
  "timestamp": "2025-11-30T23:18:00Z",
  "from_client": "arq_client_alice",
  "room": "arq_room_general",
  "payload": {
    "content": "Hello everyone in the general room!"
  }
}
```

### Channel Messages

Send a message to a channel:

```json
{
  "id": "arq_msg_003",
  "type": "message",
  "timestamp": "2025-11-30T23:18:00Z",
  "from_client": "arq_client_alice",
  "channel": "arq_channel_tech",
  "payload": {
    "content": "Technical discussion here"
  }
}
```

## Command System

Commands allow administrative and information functions.

### Command Format

```json
{
  "id": "arq_cmd_001",
  "type": "command",
  "timestamp": "2025-11-30T23:18:00Z",
  "from_client": "arq_client_admin",
  "payload": {
    "command": "status",
    "parameters": {}
  }
}
```

### Built-in Commands

#### Status Command

Get server status information:

```json
{
  "payload": {
    "command": "status",
    "parameters": {}
  }
}
```

**Response:**
```json
{
  "id": "arq_cmd_001_response",
  "type": "command_response",
  "timestamp": "2025-11-30T23:18:01Z",
  "command": "status",
  "result": {
    "server": {
      "status": "running",
      "version": "1.0.0",
      "uptime_seconds": 3600
    },
    "connections": {
      "active": 42,
      "total": 100
    },
    "messages": {
      "total": 1000,
      "rate_per_minute": 25
    }
  }
}
```

#### Ping Command

Test connectivity:

```json
{
  "payload": {
    "command": "ping",
    "parameters": {}
  }
}
```

**Response:**
```json
{
  "id": "arq_cmd_002_response",
  "type": "command_response",
  "command": "ping",
  "result": {
    "pong": true,
    "timestamp": "2025-11-30T23:18:01Z"
  }
}
```

#### Create Channel Command

Create a new channel:

```json
{
  "payload": {
    "command": "create_channel",
    "parameters": {
      "channel_id": "arq_channel_new",
      "description": "New channel for discussions"
    }
  }
}
```

**Response:**
```json
{
  "id": "arq_cmd_003_response",
  "type": "command_response",
  "command": "create_channel",
  "result": {
    "success": true,
    "channel_id": "arq_channel_new"
  }
}
```

#### Delete Channel Command

Delete a channel:

```json
{
  "payload": {
    "command": "delete_channel",
    "parameters": {
      "channel_id": "arq_channel_old"
    }
  }
}
```

#### Join Channel Command

Join a channel:

```json
{
  "payload": {
    "command": "join_channel",
    "parameters": {
      "channel_id": "arq_channel_tech"
    }
  }
}
```

#### Leave Channel Command

Leave a channel:

```json
{
  "payload": {
    "command": "leave_channel",
    "parameters": {
      "channel_id": "arq_channel_tech"
    }
  }
}
```

#### List Channels Command

List all available channels:

```json
{
  "payload": {
    "command": "list_channels",
    "parameters": {}
  }
}
```

**Response:**
```json
{
  "id": "arq_cmd_004_response",
  "type": "command_response",
  "command": "list_channels",
  "result": {
    "channels": [
      {
        "id": "arq_channel_general",
        "description": "General discussion channel",
        "member_count": 15,
        "created_at": "2025-11-30T20:00:00Z"
      },
      {
        "id": "arq_channel_tech",
        "description": "Technical discussions",
        "member_count": 8,
        "created_at": "2025-11-30T20:15:00Z"
      }
    ]
  }
}
```

#### Channel Info Command

Get detailed channel information:

```json
{
  "payload": {
    "command": "channel_info",
    "parameters": {
      "channel_id": "arq_channel_tech"
    }
  }
}
```

**Response:**
```json
{
  "id": "arq_cmd_005_response",
  "type": "command_response",
  "command": "channel_info",
  "result": {
    "channel": {
      "id": "arq_channel_tech",
      "description": "Technical discussions",
      "member_count": 8,
      "created_at": "2025-11-30T20:15:00Z",
      "members": [
        {
          "client_id": "arq_client_alice",
          "joined_at": "2025-11-30T20:16:00Z"
        },
        {
          "client_id": "arq_client_bob",
          "joined_at": "2025-11-30T20:17:00Z"
        }
      ]
    }
  }
}
```

#### History Commands

ArqonBus exposes explicit command-lane history APIs for time semantics:

- `op.history.get` (alias: `history.get`)
- `op.history.replay` (alias: `history.replay`)

`op.history.get` request:

```json
{
  "id": "arq_cmd_history_get_001",
  "type": "command",
  "timestamp": "2026-02-20T10:00:00Z",
  "version": "1.0",
  "command": "op.history.get",
  "args": {
    "room": "ops",
    "channel": "events",
    "limit": 100,
    "since": "2026-02-20T00:00:00Z",
    "until": "2026-02-20T12:00:00Z"
  }
}
```

`op.history.replay` request:

```json
{
  "id": "arq_cmd_history_replay_001",
  "type": "command",
  "timestamp": "2026-02-20T10:00:00Z",
  "version": "1.0",
  "command": "op.history.replay",
  "args": {
    "room": "ops",
    "channel": "events",
    "from_ts": "2026-02-20T00:00:00Z",
    "to_ts": "2026-02-20T12:00:00Z",
    "strict_sequence": true,
    "limit": 1000
  }
}
```

Response envelope (`type=response`):

```json
{
  "type": "response",
  "status": "success",
  "request_id": "arq_cmd_history_replay_001",
  "payload": {
    "message": "History replay window retrieved",
    "data": {
      "count": 2,
      "entries": [
        {
          "envelope": {
            "id": "arq_1700000000000000000_7_c0ffee",
            "type": "message",
            "timestamp": "2026-02-20T10:00:01+00:00",
            "payload": {"idx": 1},
            "metadata": {"sequence": 1}
          },
          "stored_at": "2026-02-20T10:00:01.123456+00:00",
          "storage_metadata": {"backend": "memory"}
        }
      ]
    }
  }
}
```

Authorization constraints:

- Non-admin clients must provide `room`; global history access is admin-only.
- `op.history.replay` enforces bounded replay windows and optional strict sequence monotonicity checks.

#### Help Command

Get available commands:

```json
{
  "payload": {
    "command": "help",
    "parameters": {}
  }
}
```

**Response:**
```json
{
  "id": "arq_cmd_007_response",
  "type": "command_response",
  "command": "help",
  "result": {
    "commands": [
      {
        "name": "status",
        "description": "Get server status information",
        "parameters": {}
      },
      {
        "name": "ping",
        "description": "Test connectivity",
        "parameters": {}
      },
      {
        "name": "create_channel",
        "description": "Create a new channel",
        "parameters": {
          "channel_id": "string (required)",
          "description": "string (optional)"
        }
      }
    ]
  }
}
```

## HTTP Monitoring Endpoints

### Base URL

```
http://localhost:8080
```

### Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-30T23:18:00Z",
  "service": "arqonbus"
}
```

### Detailed Status

**Endpoint:** `GET /status`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-30T23:18:00Z",
  "service": "arqonbus",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "endpoints": {
    "http": true,
    "websocket": true,
    "storage": true,
    "telemetry": true
  },
  "requests": {
    "total_requests": 1500,
    "average_response_time_ms": 25.5,
    "error_count": 2
  }
}
```

### Metrics Collection

**Endpoint:** `GET /metrics`

**Response:**
```json
{
  "system": {
    "uptime_seconds": 3600,
    "active_connections": 42,
    "total_messages": 1500,
    "total_commands": 250,
    "error_rate": 0.013
  },
  "commands": {
    "status": {
      "executions": 100,
      "successes": 98,
      "failures": 2,
      "success_rate": 0.98,
      "average_duration": 0.025
    }
  },
  "performance": {
    "message_routing_latency": {
      "count": 1500,
      "min": 0.005,
      "max": 0.150,
      "avg": 0.025
    }
  }
}
```

### Prometheus Metrics

**Endpoint:** `GET /metrics/prometheus`

**Response:** Plain text in Prometheus format
```text
# Generated at 2025-11-30T23:18:00Z
# ArqonBus Prometheus Metrics

# HELP arqonbus_uptime_seconds Number of seconds the ArqonBus server has been running
# TYPE arqonbus_uptime_seconds gauge
arqonbus_uptime_seconds 3600

# HELP arqonbus_active_connections Number of currently active WebSocket connections
# TYPE arqonbus_active_connections gauge
arqonbus_active_connections 42

# HELP arqonbus_command_executions_total Total number of command executions
# TYPE arqonbus_command_executions_total counter
arqonbus_command_executions_total{command="status"} 100
arqonbus_command_executions_total{command="ping"} 50
```

### Storage History

**Endpoint:** `GET /storage/history`

**Query Parameters:**
- `client_id` (optional): Get history for specific client
- `room` (optional): Get history for specific room
- `channel` (optional): Get history for specific channel
- `limit` (optional): Maximum number of messages (default: 50)

**Example:** `GET /storage/history?client_id=arq_client_alice&limit=10`

**Response:**
```json
{
  "history": [
    {
      "id": "arq_msg_001",
      "type": "message",
      "timestamp": "2025-11-30T23:15:00Z",
      "from_client": "arq_client_alice",
      "to_client": "arq_client_bob",
      "payload": {
        "content": "Hello Bob!"
      }
    }
  ],
  "count": 1,
  "query": {
    "client_id": "arq_client_alice",
    "limit": 10
  }
}
```

### Storage Statistics

**Endpoint:** `GET /storage/stats`

**Response:**
```json
{
  "backend_type": "memory",
  "redis_available": false,
  "configuration": {
    "redis_url": "redis://localhost:6379/0",
    "stream_prefix": "arqonbus",
    "history_limit": 1000,
    "key_ttl": 3600
  },
  "stats": {
    "redis_operations": 0,
    "fallback_operations": 1500,
    "connection_failures": 0,
    "last_redis_error": null
  }
}
```

### System Information

**Endpoint:** `GET /system/info`

**Response:**
```json
{
  "service": "arqonbus",
  "version": "1.0.0",
  "description": "ArqonBus Core Message Bus",
  "architecture": {
    "transport": "WebSocket",
    "protocol": "Protobuf Envelope (infra), JSON adapters (human-facing)",
    "storage": "Memory (optional Redis Streams)",
    "telemetry": "WebSocket",
    "monitoring": "HTTP Endpoints"
  },
  "features": {
    "real_time_messaging": true,
    "room_routing": true,
    "channel_routing": true,
    "message_history": true,
    "command_system": true,
    "telemetry": true,
    "persistence": true
  },
  "endpoints": {
    "websocket": "ws://localhost:9100",
    "http": "http://localhost:8080",
    "telemetry": "ws://localhost:8081"
  }
}
```

### System Configuration

**Endpoint:** `GET /system/config`

**Response:**
```json
{
  "server": {
    "host": "localhost",
    "port": 9100,
    "enabled": true
  },
  "storage": {
    "type": "memory",
    "available": true
  },
  "telemetry": {
    "enabled": true,
    "host": "localhost",
    "port": 8081
  },
  "features": {
    "cors": ["*"],
    "rate_limiting": true
  }
}
```

### Telemetry Events

**Endpoint:** `GET /telemetry/events`

**Response:**
```json
{
  "events_broadcast_total": 1500,
  "events_buffered": 0,
  "active_connections": 2,
  "average_broadcast_time_ms": 5.2,
  "total_clients_connected": 45,
  "failed_broadcasts": 0,
  "buffer_size": 0,
  "server_running": true,
  "uptime_seconds": 3600
}
```

### Telemetry Statistics

**Endpoint:** `GET /telemetry/stats`

**Response:**
```json
{
  "status": "healthy",
  "enabled": true,
  "host": "localhost",
  "port": 8081,
  "active_connections": 2,
  "events_broadcast_total": 1500,
  "timestamp": "2025-11-30T23:18:00Z"
}
```

## Error Responses

### WebSocket Errors

When a message cannot be processed, the server sends an error response:

```json
{
  "id": "arq_error_001",
  "type": "error",
  "timestamp": "2025-11-30T23:18:00Z",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Message ID must start with 'arq_'",
    "field": "id"
  },
  "original_message_id": "invalid_msg_id"
}
```

### Common Error Codes

- `VALIDATION_ERROR`: Message format or content validation failed
- `AUTHENTICATION_FAILED`: Client authentication failed
- `AUTHORIZATION_DENIED`: Client lacks permission for requested action
- `RATE_LIMIT_EXCEEDED`: Client exceeded rate limits
- `TARGET_NOT_FOUND`: Specified target (client/room/channel) does not exist
- `COMMAND_NOT_FOUND`: Unknown command name
- `COMMAND_VALIDATION_ERROR`: Command parameters are invalid
- `INTERNAL_ERROR`: Server internal error

### HTTP Error Responses

HTTP endpoints return standard HTTP status codes:

- `200 OK`: Success
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Permission denied
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error response format:
```json
{
  "error": "Error description",
  "details": "Additional error details"
}
```

## Connection Management

### WebSocket Connection

1. Establish WebSocket connection to `ws://localhost:9100`
2. Send messages using the envelope format
3. Receive responses and events
4. Handle connection close gracefully

### Reconnection Strategy

Implement exponential backoff for reconnections:
1. Wait 1 second, then reconnect
2. Wait 2 seconds, then reconnect
3. Wait 4 seconds, then reconnect
4. Maximum wait time: 30 seconds

### Heartbeat

The server may send ping messages. Clients should respond with pong messages:

```json
{
  "type": "ping",
  "timestamp": "2025-11-30T23:18:00Z"
}
```

Response:
```json
{
  "type": "pong",
  "timestamp": "2025-11-30T23:18:00Z"
}
```

## Client Libraries

### JavaScript/TypeScript Example

```javascript
import WebSocket from 'ws';

class ArqonBusClient {
  constructor(url = 'ws://localhost:9100') {
    this.url = url;
    this.ws = null;
    this.reconnectDelay = 1000;
  }

  connect() {
    this.ws = new WebSocket(this.url);
    
    this.ws.on('open', () => {
      console.log('Connected to ArqonBus');
    });
    
    this.ws.on('message', (data) => {
      const message = JSON.parse(data);
      this.handleMessage(message);
    });
    
    this.ws.on('close', () => {
      console.log('Disconnected from ArqonBus');
      setTimeout(() => this.connect(), this.reconnectDelay);
    });
  }

  sendMessage(message) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  handleMessage(message) {
    switch (message.type) {
      case 'message_response':
        console.log('Message delivered:', message);
        break;
      case 'command_response':
        console.log('Command result:', message.result);
        break;
      case 'error':
        console.error('Error:', message.error);
        break;
      default:
        console.log('Unknown message type:', message);
    }
  }
}
```

### Python Example

```python
import asyncio
import websockets
import json

class ArqonBusClient:
    def __init__(self, url='ws://localhost:9100'):
        self.url = url
        self.websocket = None
        
    async def connect(self):
        self.websocket = await websockets.connect(self.url)
        print("Connected to ArqonBus")
        
        # Start listening for messages
        await self.listen()
    
    async def listen(self):
        async for message in self.websocket:
            data = json.loads(message)
            await self.handle_message(data)
    
    async def send_message(self, message):
        if self.websocket:
            await self.websocket.send(json.dumps(message))
    
    async def handle_message(self, message):
        message_type = message.get('type')
        
        if message_type == 'message_response':
            print(f"Message delivered: {message}")
        elif message_type == 'command_response':
            print(f"Command result: {message['result']}")
        elif message_type == 'error':
            print(f"Error: {message['error']}")
        else:
            print(f"Unknown message type: {message}")

# Usage
async def main():
    client = ArqonBusClient()
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())
```

## Rate Limiting

Clients are subject to rate limiting:

- **Messages**: 100 messages per minute per client
- **Commands**: 30 commands per minute per client
- **Connections**: 10 connection attempts per minute per IP

Rate limit exceeded responses include:
```json
{
  "type": "error",
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "retry_after": 60
  }
}
```

## Best Practices

### Message Design
- Keep messages small (< 1KB)
- Use meaningful message IDs
- Include timestamps for all messages
- Validate messages before sending

### Error Handling
- Handle all error types gracefully
- Implement exponential backoff for reconnection
- Log errors for debugging
- Provide user feedback for validation errors

### Performance
- Batch messages when possible
- Use appropriate message targets (direct vs room vs channel)
- Monitor message rates to avoid rate limiting
- Close connections when not in use

### Security
- Validate all incoming messages
- Use secure WebSocket (WSS) in production
- Implement proper authentication
- Sanitize user input in message content

## Versioning

The current API version is 1.0.0. Future versions will maintain backward compatibility or be clearly marked as breaking changes.

### Version Detection

The server includes version information in status responses:
```json
{
  "server": {
    "version": "1.0.0"
  }
}
```

## Support

For API support and questions:
- Check the [Architecture Documentation](architecture.md)
- Review the [Configuration Guide](configuration.md)
- See example implementations in the `examples/` directory
