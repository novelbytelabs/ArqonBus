# CASIL API Reference

Complete technical reference for CASIL configuration, APIs, error codes, and integration patterns.

## Overview

This reference covers all CASIL APIs, configuration schemas, error handling, and integration examples for developers and system administrators.

## Configuration Schema

### Environment Variables

All CASIL configuration is managed through environment variables with the prefix `ARQONBUS_CASIL_`.

#### Core Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARQONBUS_CASIL_ENABLED` | boolean | `false` | Enable/disable CASIL |
| `ARQONBUS_CASIL_MODE` | string | `monitor` | Operational mode: `monitor` or `enforce` |
| `ARQONBUS_CASIL_DEFAULT_DECISION` | string | `allow` | Default decision on errors: `allow` or `block` |

#### Scope Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARQONBUS_CASIL_SCOPE_INCLUDE` | string | `""` | Comma-separated include patterns |
| `ARQONBUS_CASIL_SCOPE_EXCLUDE` | string | `""` | Comma-separated exclude patterns |

#### Limits and Performance

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARQONBUS_CASIL_MAX_INSPECT_BYTES` | integer | `65536` | Maximum bytes to inspect per message |
| `ARQONBUS_CASIL_MAX_PATTERNS` | integer | `32` | Maximum regex patterns to evaluate |

#### Security Policies

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARQONBUS_CASIL_MAX_PAYLOAD_BYTES` | integer | `262144` | Maximum allowed payload size |
| `ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET` | boolean | `false` | Block messages with probable secrets |

#### Redaction Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARQONBUS_CASIL_REDACTION_PATHS` | string | `"password,token,secret"` | Comma-separated field paths to redact |
| `ARQONBUS_CASIL_REDACTION_PATTERNS` | string | `""` | Comma-separated regex patterns |
| `ARQONBUS_CASIL_TRANSPORT_REDACTION` | boolean | `false` | Redact payloads in transport |
| `ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR` | string | `""` | Channel patterns for full payload redaction |

#### Metadata and Telemetry

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARQONBUS_CASIL_METADATA_TO_LOGS` | boolean | `true` | Include metadata in logs |
| `ARQONBUS_CASIL_METADATA_TO_TELEMETRY` | boolean | `true` | Include metadata in telemetry |
| `ARQONBUS_CASIL_METADATA_TO_ENVELOPE` | boolean | `false` | Include metadata in message envelopes |

### Configuration Object Schema

```python
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class CASILConfig:
    """CASIL configuration schema."""
    
    # Core settings
    enabled: bool = False
    mode: str = "monitor"  # monitor|enforce
    default_decision: str = "allow"  # allow|block
    
    # Scope configuration
    scope: "CASILScope" = field(default_factory=lambda: CASILScope())
    
    # Performance limits
    limits: "CASILLimits" = field(default_factory=lambda: CASILLimits())
    
    # Security policies
    policies: "CASILPolicies" = field(default_factory=lambda: CASILPolicies())
    
    # Metadata exposure
    metadata: "CASILMetadataExposure" = field(default_factory=lambda: CASILMetadataExposure())

@dataclass
class CASILScope:
    """Scope configuration for CASIL inspection."""
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)

@dataclass
class CASILLimits:
    """Boundaries for CASIL inspection."""
    max_inspect_bytes: int = 65536
    max_patterns: int = 32

@dataclass
class CASILRedactionConfig:
    """Redaction settings for CASIL."""
    paths: List[str] = field(default_factory=lambda: ["password", "token", "secret"])
    patterns: List[str] = field(default_factory=list)
    transport_redaction: bool = False
    never_log_payload_for: List[str] = field(default_factory=list)

@dataclass
class CASILMetadataExposure:
    """Where CASIL metadata can appear."""
    to_logs: bool = True
    to_telemetry: bool = True
    to_envelope: bool = False

@dataclass
class CASILPolicies:
    """Policy definitions for CASIL."""
    max_payload_bytes: int = 262144
    block_on_probable_secret: bool = False
    redaction: CASILRedactionConfig = field(default_factory=CASILRedactionConfig)
```

## Core APIs

### CASIL Engine API

#### `CASILEngine.inspect()`

Main inspection method that processes messages through CASIL.

```python
from arqonbus.casil.engine import CASILEngine
from arqonbus.protocol.envelope import Envelope
from arqonbus.config.config import CASILConfig

def inspect_message_example():
    # Initialize CASIL engine
    config = CASILConfig()
    config.enabled = True
    config.mode = "enforce"
    config.scope.include = ["secure-*"]
    
    engine = CASILEngine(config)
    
    # Create test envelope
    envelope = Envelope(
        type="message",
        room="secure-chat",
        channel="general",
        payload={"message": "Hello", "password": "secret123"}
    )
    
    # Context information
    context = {
        "client_id": "client_123",
        "user_id": "user_456"
    }
    
    # Inspect message
    outcome = engine.inspect(envelope, context)
    
    # Handle outcome
    if outcome.should_block:
        print(f"Message blocked: {outcome.reason_code}")
    elif outcome.should_redact_transport:
        print(f"Message redacted: {outcome.redacted_payload}")
    else:
        print(f"Message allowed: {outcome.classification}")

inspect_message_example()
```

**Parameters**:
- `envelope: Envelope` - Message envelope to inspect
- `context: Dict[str, Any]` - Additional context information

**Returns**: `CASILOutcome` - Inspection result

**Raises**: `CASILException` - On configuration or processing errors

#### `CASILEngine.configure()`

Update CASIL configuration at runtime.

```python
def update_casil_config():
    new_config = CASILConfig()
    new_config.enabled = True
    new_config.mode = "enforce"
    new_config.scope.include = ["secure-*", "pii-*"]
    new_config.policies.redaction.patterns = [
        r"(?i)api[_-]?key:\s*\S+",
        r"(?i)password:\s*\S+"
    ]
    
    engine = CASILEngine(new_config)
    
    # Configuration is applied immediately
    print("CASIL configuration updated")

update_casil_config()
```

### Classification API

#### `classify()`

Classify a message without full policy evaluation.

```python
from arqonbus.casil.classifier import classify
from arqonbus.config.config import CASILConfig
from arqonbus.protocol.envelope import Envelope

def classification_example():
    config = CASILConfig()
    config.policies.redaction.patterns = [r"(?i)api.*key"]
    
    envelope = Envelope(
        type="message",
        room="api",
        channel="updates", 
        payload={"api_key": "sk-123456789", "data": "message"}
    )
    
    context = {"oversize_payload": False}
    
    classification = classify(envelope, config, context)
    
    print(f"Kind: {classification.kind}")
    print(f"Risk Level: {classification.risk_level}")
    print(f"Flags: {classification.flags}")
    
    # Example output:
    # Kind: data
    # Risk Level: high
    # Flags: {'contains_probable_secret': True}

classification_example()
```

**Parameters**:
- `envelope: Envelope` - Message envelope to classify
- `casil_config: CASILConfig` - CASIL configuration
- `context: Dict[str, Any]` - Additional context

**Returns**: `CASILClassification` - Classification result

### Redaction API

#### `redact_payload()`

Apply redaction to a payload for specific targets.

```python
from arqonbus.casil.redaction import redact_payload
from arqonbus.config.config import CASILConfig

def redaction_example():
    config = CASILConfig()
    config.policies.redaction.paths = ["password", "token"]
    config.policies.redaction.patterns = [r"(?i)api.*key"]
    
    payload = {
        "user": {
            "password": "secret123",
            "api_key": "sk-123456789",
            "profile": {
                "email": "user@example.com"
            }
        },
        "message": "Hello world"
    }
    
    # Redact for logs (never includes transport payloads)
    redacted_for_logs = redact_payload(
        payload, 
        config, 
        target="logs",
        room_channel="secure:chat"
    )
    
    # Redact for transport if enabled
    redacted_for_transport = redact_payload(
        payload,
        config,
        target="transport", 
        room_channel="secure:chat"
    )
    
    print("Original:")
    print(payload)
    print("\nRedacted for logs:")
    print(redacted_for_logs)
    print("\nRedacted for transport:")
    print(redacted_for_transport)

redaction_example()
```

**Parameters**:
- `payload: Any` - Payload to redact
- `casil_config: CASILConfig` - CASIL configuration
- `target: str` - Redaction target: "logs" or "transport"
- `room_channel: str` - Room:channel for scope checking

**Returns**: `Any` - Redacted payload

### Policy Evaluation API

#### `evaluate_policies()`

Evaluate security policies on a message.

```python
from arqonbus.casil.policies import evaluate_policies
from arqonbus.config.config import CASILConfig
from arqonbus.protocol.envelope import Envelope

def policy_evaluation_example():
    config = CASILConfig()
    config.policies.max_payload_bytes = 1024
    config.policies.block_on_probable_secret = True
    config.policies.redaction.patterns = [r"(?i)password"]
    
    envelope = Envelope(
        type="message",
        room="test",
        channel="chat",
        payload={"password": "secret", "message": "hello"}
    )
    
    classification_flags = {"contains_probable_secret": True}
    
    result = evaluate_policies(envelope, config, classification_flags)
    
    print("Policy Evaluation Result:")
    print(f"Should Block: {result['should_block']}")
    print(f"Should Redact: {result['should_redact']}")
    print(f"Reason Code: {result['reason_code']}")
    print(f"Flags: {result['flags']}")

policy_evaluation_example()
```

**Parameters**:
- `envelope: Envelope` - Message envelope
- `casil_config: CASILConfig` - CASIL configuration
- `classification_flags: Dict[str, bool]` - Flags from classification

**Returns**: `Dict[str, Any]` - Policy evaluation result

## Error Codes and Exceptions

### CASIL Error Codes

| Error Code | Description | Action Required |
|------------|-------------|-----------------|
| `CASIL_POLICY_ALLOWED` | Message passed all checks | None |
| `CASIL_POLICY_REDACTED` | Message redacted but allowed | Review redacted content |
| `CASIL_POLICY_BLOCKED_SECRET` | Message blocked for containing secrets | Investigate source |
| `CASIL_POLICY_OVERSIZE` | Message blocked for exceeding size limit | Increase limit or reduce payload |
| `CASIL_INTERNAL_ERROR` | CASIL encountered an internal error | Check logs, restart if needed |
| `CASIL_OUT_OF_SCOPE` | Message not in inspection scope | Adjust scope configuration |
| `CASIL_DISABLED` | CASIL is disabled | Enable if needed |
| `CASIL_MONITOR_MODE` | Message would be blocked but monitor mode is active | Review monitoring data |

### Exception Classes

#### `CASILException`

Base exception for all CASIL errors.

```python
from arqonbus.casil.errors import CASILException, CASILReason

try:
    # CASIL operation
    result = engine.inspect(envelope, context)
except CASILException as e:
    print(f"CASIL error: {e}")
    print(f"Reason: {e.reason}")
    # Handle CASIL-specific errors
```

**Attributes**:
- `message: str` - Error message
- `reason: str` - Machine-readable reason code

#### `CASILReason`

Structured reason metadata.

```python
from arqonbus.casil.errors import CASILReason

reason = CASILReason(
    code="CASIL_POLICY_BLOCKED_SECRET",
    detail="Probable API key detected in payload"
)
```

**Attributes**:
- `code: str` - Reason code
- `detail: Optional[str]` - Additional detail

## Integration Patterns

### WebSocket Integration

#### Basic WebSocket Integration

```python
import asyncio
import websockets
import json
from arqonbus.casil.engine import CASILEngine
from arqonbus.config.config import CASILConfig
from arqonbus.protocol.envelope import Envelope

class CASILWebSocketHandler:
    def __init__(self):
        self.casil_config = CASILConfig()
        self.casil_config.enabled = True
        self.casil_config.mode = "enforce"
        self.casil_config.scope.include = ["secure-*"]
        
        self.casil_engine = CASILEngine(self.casil_config)
    
    async def handle_message(self, websocket, path):
        """Handle incoming WebSocket messages."""
        try:
            async for message in websocket:
                # Parse incoming message
                data = json.loads(message)
                
                # Create envelope
                envelope = Envelope(
                    type=data.get("type", "message"),
                    room=data.get("room"),
                    channel=data.get("channel"),
                    payload=data.get("payload", {})
                )
                
                # CASIL inspection
                context = {
                    "client_id": websocket.client_id,
                    "user_id": data.get("user_id")
                }
                
                outcome = self.casil_engine.inspect(envelope, context)
                
                # Handle CASIL outcome
                if outcome.should_block:
                    error_response = {
                        "type": "error",
                        "error": {
                            "code": outcome.reason_code,
                            "message": "Message blocked by CASIL security policy",
                            "classification": outcome.classification.__dict__
                        }
                    }
                    await websocket.send(json.dumps(error_response))
                    
                elif outcome.should_redact_transport:
                    # Send redacted message
                    redacted_envelope = envelope
                    redacted_envelope.payload = outcome.redacted_payload
                    
                    response = {
                        "type": "message",
                        "envelope": redacted_envelope.__dict__,
                        "casil_metadata": {
                            "decision": outcome.decision,
                            "reason_code": outcome.reason_code,
                            "classification": outcome.classification.__dict__
                        }
                    }
                    await websocket.send(json.dumps(response))
                    
                else:
                    # Normal message delivery
                    response = {
                        "type": "message", 
                        "envelope": envelope.__dict__,
                        "casil_metadata": {
                            "decision": outcome.decision,
                            "reason_code": outcome.reason_code,
                            "classification": outcome.classification.__dict__
                        } if self.casil_config.metadata.to_envelope else None
                    }
                    await websocket.send(json.dumps(response))
                    
        except Exception as e:
            print(f"WebSocket error: {e}")
    
    async def start_server(self, host="localhost", port=8765):
        """Start WebSocket server with CASIL integration."""
        server = await websockets.serve(
            self.handle_message,
            host,
            port
        )
        print(f"CASIL-enabled WebSocket server started on {host}:{port}")
        return server

# Usage
async def main():
    handler = CASILWebSocketHandler()
    await handler.start_server()
    
    # Keep server running
    await asyncio.Future()  # Run forever

asyncio.run(main())
```

#### Advanced WebSocket Integration with Room Management

```python
class AdvancedCASILWebSocketHandler:
    def __init__(self):
        self.rooms = {}  # Track rooms and their CASIL configurations
        self.casil_engine = CASILEngine(self._load_dynamic_config())
    
    def _load_dynamic_config(self):
        """Load CASIL configuration that can change at runtime."""
        config = CASILConfig()
        config.enabled = True
        config.mode = "enforce"
        
        # Load from database or configuration service
        # This is where you'd implement dynamic config loading
        return config
    
    async def handle_join_room(self, websocket, room_name):
        """Handle room joining with CASIL validation."""
        # Check if room is CASIL-protected
        if self._is_casil_protected_room(room_name):
            # Apply room-specific CASIL configuration
            room_config = self._get_room_casil_config(room_name)
            self.casil_engine.config = room_config
            
            # Send configuration to client
            config_response = {
                "type": "casil_config",
                "room": room_name,
                "config": {
                    "inspection_enabled": True,
                    "mode": room_config.mode,
                    "redaction_enabled": room_config.policies.redaction.transport_redaction
                }
            }
            await websocket.send(json.dumps(config_response))
    
    def _is_casil_protected_room(self, room_name):
        """Check if a room requires CASIL protection."""
        protected_patterns = ["secure-*", "pii-*", "finance-*"]
        return any(
            room_name.startswith(pattern[:-1]) if pattern.endswith("*") 
            else room_name == pattern
            for pattern in protected_patterns
        )
    
    async def handle_message_with_context(self, websocket, envelope):
        """Handle message with full CASIL context integration."""
        context = {
            "client_id": websocket.client_id,
            "room_members": self.rooms.get(envelope.room, set()),
            "message_history": await self._get_recent_messages(envelope.room, envelope.channel),
            "user_permissions": await self._get_user_permissions(websocket.user_id),
            "rate_limit_info": await self._get_rate_limit_info(websocket.client_id)
        }
        
        # Extended CASIL inspection
        outcome = self._extended_casil_inspection(envelope, context)
        
        # Log security events
        if outcome.should_block or "contains_probable_secret" in outcome.classification.flags:
            await self._log_security_event(envelope, outcome, context)
        
        return outcome
    
    def _extended_casil_inspection(self, envelope, context):
        """Extended CASIL inspection with additional context."""
        # Apply rate limiting context
        if context["rate_limit_info"]["is_rate_limited"]:
            envelope.payload["__rate_limited"] = True
        
        # Apply user permission context
        if not context["user_permissions"]["can_send_secrets"]:
            # Override normal patterns for restricted users
            original_patterns = self.casil_engine.config.policies.redaction.patterns
            self.casil_engine.config.policies.redaction.patterns = [
                *original_patterns,
                r"(?i)confidential.*"  # Block all confidential messages
            ]
        
        # Perform inspection
        outcome = self.casil_engine.inspect(envelope, context)
        
        # Restore original configuration
        if "original_patterns" in locals():
            self.casil_engine.config.policies.redaction.patterns = original_patterns
        
        return outcome
```

### HTTP API Integration

#### REST API Integration

```python
from flask import Flask, request, jsonify
from arqonbus.casil.integration import CasilIntegration
from arqonbus.protocol.envelope import Envelope

app = Flask(__name__)

# Initialize CASIL integration
casil = CasilIntegration(enabled=True, mode="enforce")

@app.route("/api/messages", methods=["POST"])
async def send_message():
    """Send message through CASIL-enabled API."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(key in data for key in ["room", "channel", "payload"]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Create envelope
        envelope = Envelope(
            type=data.get("type", "message"),
            room=data["room"],
            channel=data["channel"],
            payload=data["payload"]
        )
        
        # CASIL inspection
        context = {
            "user_id": data.get("user_id"),
            "client_id": request.headers.get("X-Client-ID"),
            "api_key": request.headers.get("X-API-Key")
        }
        
        outcome = await casil.process(envelope, context)
        
        # Format response based on CASIL outcome
        if outcome.should_block:
            return jsonify({
                "success": False,
                "error": {
                    "code": outcome.reason_code,
                    "message": "Message blocked by security policy",
                    "classification": outcome.classification.__dict__
                }
            }), 403
        
        elif outcome.should_redact_transport:
            return jsonify({
                "success": True,
                "message": "Message sent with redactions",
                "original_payload": envelope.payload,
                "redacted_payload": outcome.redacted_payload,
                "casil_decision": outcome.decision,
                "casil_metadata": {
                    "classification": outcome.classification.__dict__,
                    "reason_code": outcome.reason_code
                }
            })
        
        else:
            return jsonify({
                "success": True,
                "message": "Message sent successfully",
                "envelope": envelope.__dict__,
                "casil_decision": outcome.decision,
                "casil_metadata": {
                    "classification": outcome.classification.__dict__,
                    "reason_code": outcome.reason_code
                } if casil.config.metadata.to_envelope else None
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }), 500

@app.route("/api/casil/status", methods=["GET"])
def casil_status():
    """Get CASIL status and configuration."""
    return jsonify({
        "enabled": casil.config.enabled,
        "mode": casil.config.mode,
        "scope": {
            "include": casil.config.scope.include,
            "exclude": casil.config.scope.exclude
        },
        "policies": {
            "max_payload_bytes": casil.config.policies.max_payload_bytes,
            "block_on_probable_secret": casil.config.policies.block_on_probable_secret
        },
        "stats": {
            "messages_processed": getattr(casil, "messages_processed", 0),
            "messages_blocked": getattr(casil, "messages_blocked", 0),
            "messages_redacted": getattr(casil, "messages_redacted", 0)
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### Custom Middleware Integration

#### FastAPI Middleware

```python
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import json
from arqonbus.casil.engine import CASILEngine
from arqonbus.config.config import CASILConfig

class CASILMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, config: CASILConfig):
        super().__init__(app)
        self.casil_engine = CASILEngine(config)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Only process certain endpoints
        if not self._should_inspect_request(request):
            response = await call_next(request)
            return response
        
        try:
            # Extract message data from request
            if request.method == "POST":
                body = await request.body()
                data = json.loads(body) if body else {}
                
                envelope = self._create_envelope_from_request(request, data)
                context = self._create_context_from_request(request)
                
                # CASIL inspection
                outcome = self.casil_engine.inspect(envelope, context)
                
                # Handle blocking
                if outcome.should_block:
                    return Response(
                        content=json.dumps({
                            "error": {
                                "code": outcome.reason_code,
                                "message": "Request blocked by CASIL",
                                "classification": outcome.classification.__dict__
                            }
                        }),
                        status_code=403,
                        media_type="application/json"
                    )
                
                # Add CASIL headers
                headers = {
                    "X-CASIL-Decision": outcome.decision,
                    "X-CASIL-Reason": outcome.reason_code,
                    "X-CASIL-Risk-Level": outcome.classification.risk_level,
                    "X-CASIL-Processing-Time": f"{(time.time() - start_time) * 1000:.2f}ms"
                }
                
                response = await call_next(request)
                
                # Add headers to response
                for header, value in headers.items():
                    response.headers[header] = value
                
                return response
                
        except Exception as e:
            # Log CASIL errors but don't block the request
            print(f"CASIL middleware error: {e}")
            response = await call_next(request)
            return response
        
        response = await call_next(request)
        processing_time = (time.time() - start_time) * 1000
        response.headers["X-Processing-Time"] = f"{processing_time:.2f}ms"
        
        return response
    
    def _should_inspect_request(self, request: Request) -> bool:
        """Determine if request should be inspected by CASIL."""
        # Inspect POST requests to message endpoints
        if request.method == "POST" and "/api/" in request.url.path:
            return True
        return False
    
    def _create_envelope_from_request(self, request: Request, data: dict):
        """Create CASIL envelope from HTTP request."""
        return Envelope(
            type=data.get("type", "message"),
            room=data.get("room"),
            channel=data.get("channel"),
            payload=data.get("payload", {})
        )
    
    def _create_context_from_request(self, request: Request) -> dict:
        """Create CASIL context from HTTP request."""
        return {
            "client_id": request.headers.get("X-Client-ID"),
            "user_id": request.headers.get("X-User-ID"),
            "api_key": request.headers.get("X-API-Key"),
            "source_ip": request.client.host,
            "user_agent": request.headers.get("User-Agent")
        }

# Initialize FastAPI with CASIL middleware
app = FastAPI()

# CASIL configuration
casil_config = CASILConfig()
casil_config.enabled = True
casil_config.mode = "enforce"
casil_config.scope.include = ["secure-*", "api-*"]

# Add CASIL middleware
app.add_middleware(CASILMiddleware, config=casil_config)

@app.post("/api/messages")
async def send_message(message_data: dict):
    """Endpoint protected by CASIL middleware."""
    # Message processing logic
    return {"status": "message processed", "data": message_data}

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
```

## Testing and Validation APIs

### Configuration Validation

```python
from arqonbus.config.config import ArqonBusConfig

def validate_casil_configuration():
    """Validate CASIL configuration programmatically."""
    config = ArqonBusConfig()
    
    # Set CASIL configuration
    config.casil.enabled = True
    config.casil.mode = "enforce"
    config.casil.scope.include = ["secure-*"]
    config.casil.policies.redaction.patterns = ["(?i)api.*key"]
    
    # Validate configuration
    errors = config.validate()
    
    if errors:
        print("Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print("Configuration validation passed")
        return True

# Test configuration
is_valid = validate_casil_configuration()
```

### Pattern Testing API

```python
import re
from arqonbus.casil.redaction import redact_payload
from arqonbus.config.config import CASILConfig

def test_redaction_patterns():
    """Test redaction patterns with sample data."""
    config = CASILConfig()
    config.policies.redaction.patterns = [
        r"(?i)api[_-]?key:\s*\S+",
        r"(?i)password:\s*\S+"
    ]
    
    test_cases = [
        {
            "input": "My API key is api_key: sk-1234567890",
            "should_match": True,
            "expected_redaction": "My API key is ***REDACTED***"
        },
        {
            "input": "Password: password123",
            "should_match": True, 
            "expected_redaction": "***REDACTED***"
        },
        {
            "input": "Just a normal message",
            "should_match": False,
            "expected_redaction": "Just a normal message"
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_cases):
        payload = {"message": test_case["input"]}
        redacted = redact_payload(payload, config, "logs", "test:channel")
        
        matches_pattern = any(
            re.search(pattern, test_case["input"])
            for pattern in config.policies.redaction.patterns
        )
        
        result = {
            "test_case": i + 1,
            "input": test_case["input"],
            "expected_match": test_case["should_match"],
            "actual_match": matches_pattern,
            "match_correct": matches_pattern == test_case["should_match"],
            "expected_redaction": test_case["expected_redaction"],
            "actual_redaction": redacted.get("message", str(redacted))
        }
        results.append(result)
    
    return results

# Run pattern tests
test_results = test_redaction_patterns()
for result in test_results:
    status = "✅" if result["match_correct"] else "❌"
    print(f"{status} Test {result['test_case']}: {result['input']}")
    if not result["match_correct"]:
        print(f"  Expected match: {result['expected_match']}")
        print(f"  Actual match: {result['actual_match']}")
```

## Metrics and Monitoring APIs

### Custom Metrics Collection

```python
import time
from collections import defaultdict, deque
from arqonbus.casil.outcome import CASILDecision

class CASILMetricsCollector:
    def __init__(self):
        self.processing_times = deque(maxlen=10000)
        self.decision_counts = defaultdict(int)
        self.pattern_hits = defaultdict(int)
        self.room_violations = defaultdict(int)
        self.error_counts = defaultdict(int)
    
    def record_inspection(self, outcome, processing_time_ms):
        """Record inspection metrics."""
        self.processing_times.append(processing_time_ms)
        self.decision_counts[outcome.decision] += 1
        
        # Record classification flags
        for flag, value in outcome.classification.flags.items():
            if value:
                self.pattern_hits[flag] += 1
        
        # Record room-specific violations
        if outcome.should_block:
            room = outcome.metadata.get("room", "unknown")
            self.room_violations[room] += 1
    
    def record_error(self, error_type, error_message):
        """Record error metrics."""
        self.error_counts[error_type] += 1
    
    def get_metrics_summary(self):
        """Get current metrics summary."""
        if not self.processing_times:
            return {"status": "no_data"}
        
        times = list(self.processing_times)
        
        return {
            "processing_times": {
                "average_ms": sum(times) / len(times),
                "median_ms": sorted(times)[len(times) // 2],
                "p95_ms": sorted(times)[int(len(times) * 0.95)],
                "p99_ms": sorted(times)[int(len(times) * 0.99)],
                "max_ms": max(times),
                "min_ms": min(times)
            },
            "decision_distribution": dict(self.decision_counts),
            "pattern_hits": dict(self.pattern_hits),
            "room_violations": dict(self.room_violations),
            "error_counts": dict(self.error_counts),
            "total_inspections": sum(self.decision_counts.values())
        }
    
    def export_metrics(self, format="json"):
        """Export metrics in specified format."""
        metrics = self.get_metrics_summary()
        
        if format == "json":
            import json
            return json.dumps(metrics, indent=2)
        elif format == "prometheus":
            return self._format_prometheus_metrics(metrics)
        elif format == "influxdb":
            return self._format_influxdb_metrics(metrics)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _format_prometheus_metrics(self, metrics):
        """Format metrics for Prometheus."""
        lines = []
        
        # Processing time metrics
        pt = metrics.get("processing_times", {})
        for metric, value in pt.items():
            lines.append(f"arqonbus_casil_processing_time_{metric} {value}")
        
        # Decision counts
        for decision, count in metrics.get("decision_distribution", {}).items():
            lines.append(f"arqonbus_casil_decisions_total{{decision=\"{decision}\"}} {count}")
        
        # Pattern hits
        for pattern, count in metrics.get("pattern_hits", {}).items():
            lines.append(f"arqonbus_casil_pattern_hits_total{{pattern=\"{pattern}\"}} {count}")
        
        return "\n".join(lines)

# Usage example
metrics_collector = CASILMetricsCollector()

# In your CASIL inspection loop
outcome = casil_engine.inspect(envelope, context)
processing_time = (time.time() - start_time) * 1000

metrics_collector.record_inspection(outcome, processing_time)

# Export metrics
prometheus_metrics = metrics_collector.export_metrics("prometheus")
print(prometheus_metrics)
```

This completes the comprehensive CASIL API Reference. The documentation covers all major integration patterns, configuration options, error handling, and monitoring capabilities needed for production deployment of CASIL.

---

**Return to**: [CASIL Manual Index](index.md) | [Getting Started](getting-started.md) | [Best Practices](best-practices.md)