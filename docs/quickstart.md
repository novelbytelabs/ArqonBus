# ArqonBus Quick Start Guide

Welcome to ArqonBus! This guide will get you up and running with the ArqonBus message bus in just a few minutes.

## What You'll Learn

- How to set up ArqonBus for development and production
- Basic server configuration
- How to connect clients using WebSocket
- How to send and receive messages
- How to use built-in commands

## Prerequisites

- Python 3.10 or higher
- pip for package installation
- Optional: Redis for production deployment

## Installation

### Option 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/your-org/arqonbus.git
cd arqonbus

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m arqonbus.main --version
```

### Option 2: pip install (when published)

```bash
pip install arqonbus
```

## Quick Start (Development Mode)

Start ArqonBus immediately for development:

```bash
# Start server with memory storage (no external dependencies)
python -m arqonbus.main
```

You should see output like:
```
INFO: ArqonBus server started successfully on 127.0.0.1:9100
INFO: Storage backend: memory
INFO: Server is ready for connections
```

🎉 **That's it!** Your message bus is running.

## Connect Your First Client

Create a simple Python client:

```python
import asyncio
import websockets
import json

async def simple_client():
    uri = "ws://localhost:9100"
    
    async with websockets.connect(uri) as websocket:
        # Send a test message
        message = {
            "type": "message",
            "channel": "general",
            "content": "Hello ArqonBus!",
            "sender": "test-client"
        }
        await websocket.send(json.dumps(message))
        
        # Receive response
        response = await websocket.recv()
        print(f"Received: {response}")

# Run the client
asyncio.run(simple_client())
```

## Quick Commands

While connected, you can send these commands:

```python
# Get server status
status_command = {
    "type": "command",
    "command": "status"
}

# List available channels
channels_command = {
    "type": "command", 
    "command": "list_channels"
}

# Create a new channel
create_channel_command = {
    "type": "command",
    "command": "create_channel",
    "channel": "my-channel"
}
```

## Connect Using JavaScript/Web Browser

```javascript
// Browser-based client
const ws = new WebSocket('ws://localhost:9100');

ws.onopen = function() {
    console.log('Connected to ArqonBus');
    
    // Send a message
    ws.send(JSON.stringify({
        type: 'message',
        channel: 'general',
        content: 'Hello from browser!',
        sender: 'browser-client'
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};
```

## Production Setup with Redis

For production deployments with persistence:

### 1. Set up Redis

```bash
# Using Docker (recommended)
docker run -d -p 6379:6379 redis:alpine

# Or install Redis locally
# Ubuntu: sudo apt install redis-server
# macOS: brew install redis
```

### 2. Configure ArqonBus

```bash
export ARQONBUS_STORAGE_BACKEND=redis
export ARQONBUS_REDIS_HOST=localhost
export ARQONBUS_REDIS_PORT=6379
export ARQONBUS_SERVER_HOST=0.0.0.0
export ARQONBUS_SERVER_PORT=9100
export ARQONBUS_MAX_CONNECTIONS=1000
```

### 3. Start Production Server

```bash
python -m arqonbus.main
```

## Environment Configuration

Create a `.env` file for persistent configuration:

```bash
# Server settings
ARQONBUS_SERVER_HOST=127.0.0.1
ARQONBUS_SERVER_PORT=9100
ARQONBUS_MAX_CONNECTIONS=1000

# Storage backend
ARQONBUS_STORAGE_BACKEND=memory  # or 'redis'
ARQONBUS_REDIS_HOST=localhost
ARQONBUS_REDIS_PORT=6379
ARQONBUS_REDIS_SSL=false

# Features
ARQONBUS_ENABLE_TELEMETRY=true
ARQONBUS_COMPRESSION=true
ARQONBUS_DEBUG=false

# Security (optional)
ARQONBUS_ENABLE_AUTH=false
ARQONBUS_AUTH_TOKEN=your-secret-token
```

## Common Use Cases

### 1. Real-time Chat

```python
async def chat_client(username):
    uri = "ws://localhost:9100"
    
    async with websockets.connect(uri) as websocket:
        # Join the general channel
        await websocket.send(json.dumps({
            "type": "command",
            "command": "join_channel",
            "channel": "general"
        }))
        
        # Listen for messages
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            if data["type"] == "message":
                print(f"[{data['channel']}] {data['sender']}: {data['content']}")
```

### 2. IoT Device Communication

```python
async def iot_device(device_id):
    uri = "ws://localhost:9100"
    
    async with websockets.connect(uri) as websocket:
        # Register device
        await websocket.send(json.dumps({
            "type": "command",
            "command": "join_channel", 
            "channel": f"devices/{device_id}"
        }))
        
        # Send sensor data
        while True:
            sensor_data = {
                "type": "message",
                "channel": f"devices/{device_id}",
                "content": {
                    "temperature": 23.5,
                    "humidity": 65.2,
                    "timestamp": time.time()
                },
                "sender": device_id
            }
            await websocket.send(json.dumps(sensor_data))
            await asyncio.sleep(30)  # Send every 30 seconds
```

### 3. Notification System

```python
async def notification_client():
    uri = "ws://localhost:9100"
    
    async with websockets.connect(uri) as websocket:
        # Join notifications channel
        await websocket.send(json.dumps({
            "type": "command",
            "command": "join_channel",
            "channel": "notifications"
        }))
        
        # Handle incoming notifications
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            if data["type"] == "message":
                notification = data["content"]
                print(f"Notification: {notification['title']}")
                # Handle notification display, push notification, etc.
```

## Testing Your Setup

### 1. Health Check

```bash
curl http://localhost:9100/health
```

Expected response:
```json
{
    "status": "healthy",
    "timestamp": "2025-12-01T02:49:41.212Z",
    "components": {
        "websocket": {"status": "healthy"},
        "storage": {"status": "healthy"}
    }
}
```

### 2. Server Status

```bash
curl http://localhost:9100/status
```

### 3. Run Integration Tests

```bash
# Run the Redis connectivity test
python test_redis_connection.py

# Run comprehensive tests
python -m pytest tests/integration/ -v
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 9100
lsof -i :9100

# Kill the process
kill -9 <PID>
```

### Redis Connection Issues

```bash
# Test Redis connection
redis-cli -h localhost -p 6379 ping

# Check Redis logs
tail -f /var/log/redis/redis-server.log
```

### Connection Refused

1. Verify server is running: `ps aux | grep arqonbus`
2. Check firewall settings
3. Ensure WebSocket port is accessible

## Next Steps

- 📖 **Read the full [API Documentation](api.md)**
- 🏗️ **Learn about [Architecture](architecture.md)**
- 👨‍💻 **See [Developer Guide](developers_guide.md)**
- 📚 **Follow the [Tutorial](tutorial.md)**
- 🔧 **Check [Operations Runbook](runbook.md)**

## Support

- **Issues**: Report on GitHub Issues
- **Documentation**: This repository
- **Community**: Join our Discord/Slack
- **Email**: support@arqonbus.com

## Performance Tips

1. **Use Memory Storage for Development**: No external dependencies
2. **Use Redis for Production**: Better performance and persistence
3. **Enable Compression**: Reduces network traffic
4. **Monitor Connections**: Use the built-in metrics
5. **Scale Horizontally**: Run multiple instances behind a load balancer

## Security Best Practices

1. **Use HTTPS/WSS in Production**: Secure WebSocket connections
2. **Enable Authentication**: Set up token-based auth
3. **Rate Limiting**: Prevent abuse
4. **Firewall Rules**: Restrict access to necessary ports only
5. **Regular Updates**: Keep dependencies current

---

**🎉 Congratulations!** You've successfully set up ArqonBus. You're ready to build real-time applications with ease.

For more advanced usage and detailed information, check out our other documentation files.