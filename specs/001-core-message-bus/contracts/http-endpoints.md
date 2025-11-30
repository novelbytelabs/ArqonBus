# HTTP Endpoints Contract: ArqonBus v1.0

**Feature**: 001-core-message-bus  
**Created**: 2025-11-30  
**Protocol Version**: 1.0

## Overview

ArqonBus exposes minimal HTTP endpoints for health monitoring, version information, and metrics collection. These endpoints provide operational visibility for monitoring systems.

## Endpoints

### 1. Health Check Endpoint

**Endpoint**: `GET /health`  
**Purpose**: Liveness check for container orchestration and monitoring  
**Response**: JSON

**Success Response** (200 OK):
```json
{
  "status": "ok",
  "timestamp": "2025-01-01T12:00:00.000Z",
  "uptime_seconds": 3600,
  "version": "1.0.0"
}
```

**Failure Response** (500 Internal Server Error):
```json
{
  "status": "error",
  "timestamp": "2025-01-01T12:00:00.000Z",
  "error": "Service unavailable",
  "details": "Internal server error description"
}
```

### 2. Version Information Endpoint

**Endpoint**: `GET /version`  
**Purpose**: Provide version information for compatibility checking  
**Response**: JSON

**Response** (200 OK):
```json
{
  "name": "ArqonBus",
  "version": "1.0.0",
  "protocol": "1.0",
  "build": {
    "git_commit": "abc123def456",
    "build_date": "2025-01-01T10:00:00.000Z"
  }
}
```

### 3. Metrics Endpoint

**Endpoint**: `GET /metrics`  
**Purpose**: Prometheus-format metrics for monitoring systems  
**Response**: Plain text (Prometheus format)  
**Content-Type**: `text/plain; version=0.0.4; charset=utf-8`

**Response** (200 OK):
```
# HELP arqonbus_active_clients Number of currently connected clients
# TYPE arqonbus_active_clients gauge
arqonbus_active_clients 25

# HELP arqonbus_messages_sent_total Total number of messages sent
# TYPE arqonbus_messages_sent_total counter
arqonbus_messages_sent_total 1543

# HELP arqonbus_messages_received_total Total number of messages received
# TYPE arqonbus_messages_received_total counter
arqonbus_messages_received_total 1621

# HELP arqonbus_errors_total Total number of errors encountered
# TYPE arqonbus_errors_total counter
arqonbus_errors_total 3

# HELP arqonbus_rooms_total Total number of active rooms
# TYPE arqonbus_rooms_total gauge
arqonbus_rooms_total 5

# HELP arqonbus_channels_total Total number of active channels
# TYPE arqonbus_channels_total gauge
arqonbus_channels_total 12

# HELP arqonbus_uptime_seconds Server uptime in seconds
# TYPE arqonbus_uptime_seconds counter
arqonbus_uptime_seconds 3600

# HELP arqonbus_memory_usage_bytes Current memory usage in bytes
# TYPE arqonbus_memory_usage_bytes gauge
arqonbus_memory_usage_bytes 53687091

# HELP arqonbus_websocket_connections Active WebSocket connections
# TYPE arqonbus_websocket_connections gauge
arqonbus_websocket_connections 25

# HELP arqonbus_telemetry_connections Active telemetry connections
# TYPE arqonbus_telemetry_connections gauge
arqonbus_telemetry_connections 2
```

## Security Considerations

### Authentication
- No authentication required for health endpoints
- Suitable for internal monitoring systems only
- For production use, place behind reverse proxy with authentication

### Rate Limiting
- Endpoints are designed for monitoring systems
- Rate limiting applies to prevent abuse
- Suitable polling frequency: once per 30 seconds

### CORS
- CORS headers configured for browser-based monitoring tools
- Allows cross-origin requests from monitoring dashboards

## Performance Requirements

### Response Time
- Health endpoint: < 50ms
- Version endpoint: < 100ms
- Metrics endpoint: < 200ms (depends on data size)

### Availability
- 99.9% uptime requirement
- Must remain available during WebSocket overload
- Graceful degradation under resource constraints

### Scalability
- Endpoints must scale with number of clients/rooms
- Metrics calculation optimized for large datasets
- Memory-efficient metric collection

## Integration Examples

### Kubernetes Liveness Probe
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### Prometheus Configuration
```yaml
scrape_configs:
  - job_name: 'arqonbus'
    static_configs:
      - targets: ['arqonbus:8080']
    scrape_interval: 30s
    metrics_path: /metrics
```

### Health Check with curl
```bash
curl -X GET http://localhost:8080/health
```

### Metrics Collection
```bash
curl -X GET http://localhost:8080/metrics