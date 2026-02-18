# ArqonBus Operations Runbook

## Overview

This runbook provides operational procedures for deploying, managing, and troubleshooting ArqonBus v1.0 Core Message Bus in production environments.

## Quick Reference

### System Information
- **Version**: v1.0.0
- **Protocol**: WebSocket-based real-time messaging
- **Storage**: Memory (development) or Redis Streams (production)
- **Monitoring**: HTTP endpoints + Prometheus metrics
- **Authentication**: Optional token-based authentication

### Environment Setup

```bash
# Required environment variables for production
export ARQONBUS_STORAGE_BACKEND=redis
export ARQONBUS_REDIS_HOST=your-redis-host.com
export ARQONBUS_REDIS_PORT=6379
export ARQONBUS_REDIS_SSL=true
export ARQONBUS_REDIS_PASSWORD=your-redis-password
export ARQONBUS_SERVER_HOST=0.0.0.0
export ARQONBUS_SERVER_PORT=9100
export ARQONBUS_MAX_CONNECTIONS=1000
export ARQONBUS_ENABLE_TELEMETRY=true
export ARQONBUS_ENABLE_AUTH=true
export ARQONBUS_AUTH_JWT_SECRET=replace-with-strong-secret
export ARQONBUS_AUTH_JWT_ALGORITHM=HS256
export ARQONBUS_DEBUG=false
```

## Deployment Procedures

### 1. Production Deployment

#### Prerequisites
- Redis instance (managed or self-hosted)
- SSL certificates (for HTTPS/WebSocket connections)
- System monitoring setup

#### Deployment Steps

1. **Configure Environment Variables**
   ```bash
   cp .env.production .env
   # Edit .env with your production values
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify Redis Connectivity**
   ```bash
   python test_redis_connection.py
   ```

4. **Start ArqonBus Server**
   ```bash
   # Using the Python module
   python -m arqonbus.main

   # Or using the run script
   ./run_arqonbus.sh start

   # With custom configuration
   ARQONBUS_STORAGE_BACKEND=redis python -m arqonbus.main --host 0.0.0.0 --port 9100
   ```

5. **Verify Health**
   ```bash
   curl http://localhost:9100/health
   curl http://localhost:9100/metrics
   ```

### 2. Development Deployment

```bash
# Quick start with memory storage
python -m arqonbus.main

# Start with development logging
export ARQONBUS_DEBUG=true
export ARQONBUS_LOG_LEVEL=DEBUG
python -m arqonbus.main
```

## Monitoring and Health Checks

### Health Endpoints

- **Health Check**: `GET /health`
- **Server Status**: `GET /status`
- **Metrics**: `GET /metrics`
- **Version**: `GET /version`

### CLI Quick Checks (`arqon`)

```bash
# HTTP health snapshots
arqon version --http-url http://127.0.0.1:8080
arqon status --http-url http://127.0.0.1:8080

# WebSocket stream tail (JWT optional unless auth is enabled)
arqon tail --ws-url ws://127.0.0.1:9100 --jwt "$ARQONBUS_AUTH_JWT" --raw --limit 1
```

### Epoch 2 Operator Pack Quick Checks

Command envelopes (send via WebSocket client or `wscat`) supported:

- `op.casil.get|reload` (admin-only reload)
- `op.webhook.register|list|unregister`
- `op.cron.schedule|list|cancel`
- `op.store.set|get|list|delete`

Tier-Omega experimental lane (feature-flagged):

- `op.omega.status`
- `op.omega.register_substrate|list_substrates|unregister_substrate` (admin-only registration/removal)
- `op.omega.emit_event` (admin-only event emission)
- `op.omega.list_events|clear_events` (`clear_events` is admin-only)

Tier-Omega flags:

```bash
export ARQONBUS_OMEGA_ENABLED=false
export ARQONBUS_OMEGA_LAB_ROOM=omega-lab
export ARQONBUS_OMEGA_LAB_CHANNEL=signals
export ARQONBUS_OMEGA_MAX_EVENTS=1000
export ARQONBUS_OMEGA_MAX_SUBSTRATES=128
```

CASIL hot reload example envelope:

```json
{
  "id": "arq_...generated...",
  "type": "command",
  "timestamp": "2026-02-18T00:00:00+00:00",
  "version": "1.0",
  "command": "op.casil.reload",
  "args": {
    "mode": "enforce",
    "block_on_probable_secret": true,
    "redaction_patterns": ["token", "secret"]
  }
}
```

Hello-world bot smoke:

```bash
ARQONBUS_WS_URL=ws://127.0.0.1:9100 python examples/python/hello_world_bot.py
```

### Epoch 1 Manual Gate Evidence (`wscat`)

Validated on 2026-02-18 in this sandbox:

```bash
# Reproducible one-shot validator
scripts/validate_epoch1_wscat.sh

# 1) Unauthenticated handshake (expected 401)
wscat --no-color -c ws://127.0.0.1:47001 -w 1
# observed: error: Unexpected server response: 401

# 2) Authenticated handshake (expected connect + welcome envelope)
wscat --no-color -H "Authorization: Bearer <jwt>" -c ws://127.0.0.1:47001 -w 1
# observed: Connected (press CTRL+C to quit)
# observed: < {"type":"message","payload":{"welcome":"Connected to ArqonBus",...}}
```

### Key Metrics to Monitor

```bash
# System health
curl http://localhost:9100/health | jq

# Connection statistics
curl http://localhost:9100/status | jq '.websocket.connections'

# Storage backend health
curl http://localhost:9100/status | jq '.storage.health'
```

### Monitoring Alerts

Set up alerts for:
- Server health check failures
- High connection count (>80% of max_connections)
- Storage backend health failures
- Memory usage growth patterns
- WebSocket connection timeouts

### Prometheus Metrics

Available at `/metrics`:
- `arqonbus_connections_active`
- `arqonbus_messages_total`
- `arqonbus_storage_operations_total`
- `arqonbus_uptime_seconds`

## CASIL Operations (Feature 002)

### Defaults & Recommended Bounds
- `casil.enabled=false` (opt-in)
- `casil.mode=monitor` (no blocking)
- `casil.default_decision=allow` (fail-open on internal errors)
- `casil.limits.max_inspect_bytes=65536` (recommended upper bound: 262144)
- `casil.limits.max_patterns=32` (recommended upper bound: 64)
- `casil.policies.max_payload_bytes=262144` (tighten for sensitive channels)
- Metadata exposure: logs/telemetry on; envelope opt-in (`casil.metadata.to_envelope=false`)

### Enable / Tighten / Relax
1. **Enable in monitor mode (safe rollout)**  
   `ARQONBUS_CASIL_ENABLED=true`  
   `ARQONBUS_CASIL_MODE=monitor`  
   `ARQONBUS_CASIL_SCOPE_INCLUDE="secure-*"`

2. **Tighten during incident (enforce + stricter policies)**  
   `ARQONBUS_CASIL_MODE=enforce`  
   `ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true`  
   `ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=<lower>`  
   `ARQONBUS_CASIL_REDACTION_PATTERNS="token,secret,api_key"`  
   Restart or reload configuration to apply (server reload reinitializes CASIL).

3. **Relax / disable**  
   Switch back to `monitor` or set `ARQONBUS_CASIL_ENABLED=false` and restart.

### Incident Steps
- Switch monitor → enforce and lower size limits for affected channels.
- Confirm CASIL telemetry for reason codes (`CASIL_POLICY_BLOCKED_SECRET`, `CASIL_POLICY_OVERSIZE`).
- Verify blocked messages are not delivered/persisted (history stays unchanged).
- After containment, relax to monitor mode and review logs/telemetry for hotspots (room/channel/client).

### Performance Benchmarks
- Targets: CASIL disabled ≈ baseline throughput/latency (±1%); CASIL monitor mode adds <5ms p99 per inspected message at default `max_inspect_bytes`.
- Benchmarks: `pytest tests/performance/test_casil_benchmarks.py -m performance`
- Record results per environment (date, machine, baseline vs CASIL monitor) and update this section after each run.

## Operational Procedures

### Daily Operations

#### Server Status Check
```bash
# Check if server is running
ps aux | grep arqonbus

# Check logs
tail -f logs/arqonbus.log

# Check health endpoints
curl -s http://localhost:9100/health
```

#### Log Analysis
```bash
# Recent errors
grep ERROR logs/arqonbus.log | tail -20

# Connection statistics
grep "connection" logs/arqonbus.log | tail -10

# Memory usage growth
grep "memory" logs/arqonbus.log | tail -10
```

### Weekly Operations

#### Capacity Planning
1. Review connection statistics over the past week
2. Analyze message throughput patterns
3. Check Redis memory usage if using Redis backend
4. Review WebSocket connection durations

#### Performance Review
1. Check average response times
2. Review failed connection attempts
3. Analyze storage backend performance
4. Check for any memory leaks

### Monthly Operations

#### Security Review
1. Review authentication logs
2. Check for unusual connection patterns
3. Verify SSL certificate expiration
4. Update dependencies if needed

#### Backup and Recovery
1. Test Redis backup procedures
2. Verify log rotation is working
3. Test disaster recovery procedures

## Troubleshooting Guide

### Common Issues

#### 1. Server Won't Start

**Symptoms**: Server fails to start or crashes immediately

**Diagnosis**:
```bash
# Check if port is already in use
netstat -tulpn | grep 9100

# Check logs for errors
tail -50 logs/arqonbus.log

# Verify Redis connectivity
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping
```

**Solutions**:
- Change server port if conflict exists
- Fix Redis connection parameters
- Check configuration file syntax

#### 2. High Memory Usage

**Symptoms**: Server consuming excessive memory

**Diagnosis**:
```bash
# Check process memory usage
ps aux | grep arqonbus

# Analyze memory storage size
curl http://localhost:9100/status | jq '.storage.memory_usage'

# Check for memory leaks in logs
grep "memory" logs/arqonbus.log | tail -20
```

**Solutions**:
- Switch to Redis backend for persistence
- Reduce max_history_size configuration
- Implement regular restart schedule

#### 3. Connection Timeouts

**Symptoms**: Clients experiencing connection timeouts

**Diagnosis**:
```bash
# Check WebSocket statistics
curl http://localhost:9100/status | jq '.websocket'

# Review connection logs
grep "timeout" logs/arqonbus.log | tail -10

# Check system resources
top -p $(pgrep -f arqonbus)
```

**Solutions**:
- Increase connection_timeout configuration
- Check network connectivity
- Review firewall settings

#### 4. Redis Connection Failures

**Symptoms**: Storage backend health check failures

**Diagnosis**:
```bash
# Test Redis connection directly
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping

# Check Redis logs
tail -20 /var/log/redis/redis-server.log

# Test with password
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping
```

**Solutions**:
- Verify Redis credentials
- Check network connectivity
- Switch to memory storage temporarily

### Emergency Procedures

#### Immediate Server Restart

```bash
# Stop current server
pkill -f arqonbus

# Clear any stuck processes
fuser -k 9100/tcp

# Start with memory storage as fallback
python -m arqonbus.main --storage-backend memory
```

#### Disaster Recovery

1. **Switch to Memory Mode**
   ```bash
   export ARQONBUS_STORAGE_BACKEND=memory
   python -m arqonbus.main
   ```

2. **Restore from Backup**
   ```bash
   # If using Redis with backups
   redis-cli --rdb /path/to/backup.rdb
   ```

3. **Scale Temporarily**
   - Use multiple ArqonBus instances
   - Implement client-side load balancing

## Configuration Management

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ARQONBUS_SERVER_HOST` | 127.0.0.1 | Server bind address |
| `ARQONBUS_SERVER_PORT` | 9100 | Server port |
| `ARQONBUS_MAX_CONNECTIONS` | 1000 | Maximum concurrent connections |
| `ARQONBUS_STORAGE_BACKEND` | memory | Storage backend (memory/redis) |
| `ARQONBUS_REDIS_HOST` | localhost | Redis host |
| `ARQONBUS_REDIS_PORT` | 6379 | Redis port |
| `ARQONBUS_REDIS_PASSWORD` | None | Redis password |
| `ARQONBUS_REDIS_SSL` | false | Enable SSL for Redis |
| `ARQONBUS_MAX_MESSAGE_SIZE` | 1048576 | Maximum WebSocket message size |
| `ARQONBUS_COMPRESSION` | true | Enable message compression |
| `ARQONBUS_ENABLE_TELEMETRY` | true | Enable telemetry events |
| `ARQONBUS_ENABLE_AUTH` | false | Require JWT auth at WebSocket handshake |
| `ARQONBUS_AUTH_JWT_SECRET` | None | Shared secret for HS256 JWT verification |
| `ARQONBUS_AUTH_JWT_ALGORITHM` | HS256 | Supported JWT algorithm (HS256) |
| `ARQONBUS_LOG_LEVEL` | INFO | Logging level |
| `ARQONBUS_DEBUG` | false | Enable debug mode |

### Configuration Validation

```bash
# Validate current configuration
python -c "
from arqonbus.config.config import get_config, validate_config
config = get_config()
errors = validate_config()
if errors:
    print('Configuration errors:')
    for error in errors:
        print(f'  - {error}')
else:
    print('Configuration is valid')
"
```

## Performance Tuning

### Throughput Optimization

1. **Increase Connection Limits**
   ```bash
   export ARQONBUS_MAX_CONNECTIONS=2000
   export ARQONBUS_MAX_MESSAGE_SIZE=2097152
   ```

2. **Optimize Redis Settings**
   ```bash
   # In redis.conf
   maxmemory-policy allkeys-lru
   tcp-keepalive 60
   save 60 1000
   ```

3. **Enable Compression**
   ```bash
   export ARQONBUS_COMPRESSION=true
   ```

### Memory Optimization

1. **Limit Memory Storage**
   ```bash
   export ARQONBUS_MAX_HISTORY_SIZE=5000
   ```

2. **Use Redis for Persistence**
   ```bash
   export ARQONBUS_STORAGE_BACKEND=redis
   export ARQONBUS_ENABLE_PERSISTENCE=true
   ```

## Security Considerations

### Network Security

1. **Use HTTPS/WSS in Production**
   - Configure SSL certificates
   - Use WSS protocol for WebSocket connections

2. **Firewall Configuration**
   ```bash
   # Allow only necessary ports
   ufw allow 9100/tcp
   ufw deny 6379/tcp  # If Redis is external
   ```

3. **Redis Security**
   - Use strong passwords
   - Enable SSL for Redis connections
   - Restrict Redis network access

### Authentication

1. **Enable Token Authentication**
   ```bash
   export ARQONBUS_ENABLE_AUTH=true
   export ARQONBUS_AUTH_TOKEN=your-secure-token
   ```

2. **Rate Limiting**
   ```bash
   export ARQONBUS_RATE_LIMIT_PER_MINUTE=60
   ```

## Contact Information

For operational support:
- **Technical Issues**: Check logs and this runbook first
- **Escalation**: Contact the development team
- **Documentation**: See developers_guide.md for detailed API information

## Additional Resources

- **API Documentation**: See api.md
- **Architecture Guide**: See architecture.md
- **Developer Guide**: See developers_guide.md
- **Tutorial**: See tutorial.md
