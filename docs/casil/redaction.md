# CASIL Redaction & Safety

Understanding how CASIL protects your content through classification, pattern detection, and redaction.

## Overview

CASIL provides multiple layers of content protection:

1. **Classification**: Analyzes message types and risk levels
2. **Pattern Detection**: Identifies probable secrets and sensitive content
3. **Redaction**: Masks or removes sensitive information
4. **Policy Enforcement**: Applies blocking and alerting rules

## Content Classification

### Message Type Classification

CASIL automatically classifies messages by their envelope type:

```json
{
  "type": "message",     // → "data"
  "type": "command",     // → "control" 
  "type": "telemetry",   // → "telemetry"
  "type": "error"        // → "system"
}
```

**Classification Results**:
- `control`: Administrative commands, system operations
- `telemetry`: Metrics, monitoring, health checks
- `data`: User messages, application data, business logic
- `system`: Error messages, status updates

### Risk Level Assessment

CASIL assigns risk levels based on content analysis:

| Risk Level | Triggers | Action |
|------------|----------|---------|
| **Low** | Normal data messages | Pass through |
| **Medium** | Oversized payloads, warnings | Monitor/flag |
| **High** | Probable secrets, violations | Block/redact |

**Risk Escalation Example**:
```python
# Low risk → Medium risk
if context.get("oversize_payload"):
    classification.risk_level = "medium"

# Any secret detection → High risk  
if classification.flags.get("contains_probable_secret"):
    classification.risk_level = "high"
```

### Classification Flags

CASIL sets boolean flags for specific conditions:

- `contains_probable_secret`: Message likely contains sensitive data
- `oversize_payload`: Message exceeds configured size limits

## Pattern-Based Detection

### Default Secret Patterns

CASIL includes built-in patterns for common sensitive data:

```python
DEFAULT_SECRET_PATTERNS = [
    r"(?i)api[_-]?key",          # API keys (api_key, APIKey, api-key)
    r"(?i)secret",               # Generic secrets
    r"(?i)token",                # Authentication tokens  
    r"(?i)password",             # Passwords
    r"(?i)bearer\s+[A-Za-z0-9\-\._]+",  # Bearer tokens
]
```

### Pattern Matching Examples

| Pattern | Matches | Doesn't Match |
|---------|---------|---------------|
| `(?i)api[_-]?key` | `api_key`, `APIKey`, `api-key` | `api_key_old`, `myapi` |
| `(?i)secret` | `secret`, `Secret`, `SECRET` | `secretly`, `secret_santa` |
| `(?i)bearer\s+[A-Za-z0-9\-\._]+` | `Bearer abc123`, `bearer xyz-789` | `Bearer`, `bearer_token` |

### Custom Pattern Development

#### Financial Application Patterns

```bash
# Credit card numbers
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)credit_card:\s*\d{16}"

# Bank account numbers  
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)account_number:\s*\d{10,12}"

# Social Security Numbers
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)ssn:\s*\d{3}-\d{2}-\d{4}"
```

#### API Integration Patterns

```bash
# JWT tokens
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)jwt:\s*[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"

# Authorization headers
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)authorization:\s*bearer\s+[a-z0-9]{32,}"

# API keys with various formats
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)api_key:\s*[a-z0-9]{32,},(?i)x-api-key:\s*[a-z0-9]{32,}"
```

#### Healthcare Patterns (HIPAA)

```bash
# Medical Record Numbers
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)medical_record:\s*[A-Z]{2}\d{8}"

# Patient IDs
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)patient_id:\s*\d{8,10}"

# Insurance numbers
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)insurance_id:\s*[A-Z]{2}\d{8}"
```

### Pattern Testing and Validation

#### Test Patterns Manually

```python
import re

def test_pattern(pattern, test_strings):
    for text in test_strings:
        match = re.search(pattern, text)
        print(f"Pattern: {pattern}")
        print(f"Text: {text}")
        print(f"Match: {bool(match)}")
        if match:
            print(f"Found: {match.group()}")
        print("-" * 50)

# Test credit card pattern
pattern = r"(?i)credit_card:\s*\d{16}"
test_strings = [
    "credit_card: 1234567890123456",
    "CreditCard: 1234567890123456", 
    "credit_card_number: 1234567890123456",
    "credit_card: 1234-5678-9012-3456"  # Won't match (format difference)
]

test_pattern(pattern, test_strings)
```

#### Validate Pattern Performance

```python
import time
import re

def benchmark_pattern(pattern, test_text, iterations=1000):
    start_time = time.time()
    for _ in range(iterations):
        re.search(pattern, test_text)
    end_time = time.time()
    
    avg_time = (end_time - start_time) / iterations
    print(f"Pattern: {pattern}")
    print(f"Average time: {avg_time:.6f} seconds")
    print(f"Rate: {iterations/avg_time:.0f} matches/second")

# Benchmark pattern
pattern = r"(?i)api.*key|secret|token"
test_text = "some long text with api_key and secret_token scattered throughout"
benchmark_pattern(pattern, test_text)
```

## Path-Based Redaction

### Field Path Redaction

CASIL can redact specific JSON fields by their path names:

```bash
export ARQONBUS_CASIL_REDACTION_PATHS="password,token,secret,api_key"
```

#### How Path Redaction Works

**Input Message**:
```json
{
  "user": {
    "profile": {
      "password": "secret123",
      "email": "user@example.com"
    },
    "auth": {
      "token": "abc123xyz",
      "refresh_token": "def456uvw"
    }
  },
  "data": {
    "password": "different_secret",
    "api_key": "key_789"
  }
}
```

**After Redaction**:
```json
{
  "user": {
    "profile": {
      "password": "***REDACTED***",
      "email": "user@example.com"
    },
    "auth": {
      "token": "***REDACTED***",
      "refresh_token": "***REDACTED***"
    }
  },
  "data": {
    "password": "***REDACTED***",
    "api_key": "***REDACTED***"
  }
}
```

### Common Field Names to Redact

#### Authentication Fields
```bash
export ARQONBUS_CASIL_REDACTION_PATHS="password,token,access_token,refresh_token,auth_token,bearer_token,api_key,secret_key"
```

#### Financial Fields
```bash
export ARQONBUS_CASIL_REDACTION_PATHS="credit_card,account_number,routing_number,pin,cvv,ssn,tax_id"
```

#### Personal Information
```bash
export ARQONBUS_CASIL_REDACTION_PATHS="email,phone,address,ssn,dob,first_name,last_name,date_of_birth"
```

#### Healthcare Fields (HIPAA)
```bash
export ARQONBUS_CASIL_REDACTION_PATHS="patient_id,medical_record_number,insurance_id,diagnosis,treatment,prescription"
```

## Redaction Strategies

### Strategy 1: Logging-Only Redaction

Protect observability while preserving message delivery:

```bash
export ARQONBUS_CASIL_TRANSPORT_REDACTION=false
export ARQONBUS_CASIL_REDACTION_PATHS="password,token,secret"
export ARQONBUS_CASIL_METADATA_TO_LOGS=true
```

**Effect**:
- ✅ Clients receive original messages
- ✅ Logs contain redacted content
- ✅ Telemetry shows classification without exposing secrets

**Use Case**: Multi-tenant applications where tenants need their data intact.

### Strategy 2: Full Redaction

Protect all layers including message delivery:

```bash
export ARQONBUS_CASIL_TRANSPORT_REDACTION=true
export ARQONBUS_CASIL_REDACTION_PATHS="password,token,secret,api_key"
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="pii-*,secure-*"
```

**Effect**:
- ❌ Clients receive redacted messages
- ✅ No sensitive data in logs or telemetry
- ✅ Maximum security protection

**Use Case**: High-security environments, compliance requirements.

### Strategy 3: Channel-Specific Protection

Apply different rules to different channel types:

```bash
# Redact PII in logs only
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="pii-*"
export ARQONBUS_CASIL_REDACTION_PATHS="password,token,ssn"

# Full redaction for sensitive finance channels
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="payment-*,finance-*"
export ARQONBUS_CASIL_REDACTION_PATHS="credit_card,account_number,routing_number"
```

## Safety Policies

### Oversize Payload Protection

Prevent denial-of-service through large payloads:

```bash
# Set size limits per use case
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=262144        # Standard (256KB)
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=1048576       # Media files (1MB)  
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=51200         # Strict API (50KB)
```

**Size Limit Guidelines**:

| Use Case | Recommended Limit | Rationale |
|----------|-------------------|-----------|
| Real-time chat | 50KB | Prevent spam, maintain performance |
| File sharing | 1MB | Allow small document sharing |
| API calls | 100KB | Balance functionality vs security |
| Medical images | 5MB+ | Required for healthcare applications |

### Secret Blocking Policies

Control how probable secrets are handled:

#### Monitor-Only Policy
```bash
export ARQONBUS_CASIL_MODE=monitor
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=false
```
- ⚠️ Flags secrets in telemetry
- 📊 Provides audit trail
- 🚫 Never blocks messages

#### Blocking Policy
```bash
export ARQONBUS_CASIL_MODE=enforce
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true
```
- 🛡️ Blocks messages with probable secrets
- 📋 Returns structured error to client
- 🔒 Maximum security protection

#### Selective Blocking
```bash
# Block only in high-risk channels
export ARQONBUS_CASIL_SCOPE_INCLUDE="payment-*,finance-*,secure-*"
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true
export ARQONBUS_CASIL_SCOPE_INCLUDE="chat-*,social-*"
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=false
```

## Policy Outcomes

### Decision Types

CASIL produces three possible outcomes:

#### ALLOW
```json
{
  "decision": "ALLOW",
  "reason_code": "CASIL_POLICY_ALLOWED",
  "classification": {
    "kind": "data",
    "risk_level": "low",
    "flags": {}
  }
}
```

**When**: Message passes all checks, no sensitive content detected.

#### ALLOW_WITH_REDACTION
```json
{
  "decision": "ALLOW_WITH_REDACTION", 
  "reason_code": "CASIL_POLICY_REDACTED",
  "classification": {
    "kind": "data",
    "risk_level": "medium",
    "flags": {"contains_probable_secret": true}
  },
  "redacted_payload": {
    "password": "***REDACTED***",
    "api_key": "***REDACTED***"
  }
}
```

**When**: Sensitive content detected but not blocked (monitor mode or selective policy).

#### BLOCK
```json
{
  "decision": "BLOCK",
  "reason_code": "CASIL_POLICY_BLOCKED_SECRET",
  "classification": {
    "kind": "data", 
    "risk_level": "high",
    "flags": {"contains_probable_secret": true}
  }
}
```

**When**: Content violates security policies in enforce mode.

### Error Handling

#### Internal Errors
```json
{
  "decision": "ALLOW",  // or BLOCK based on default_decision
  "reason_code": "CASIL_INTERNAL_ERROR",
  "internal_error": "Regex pattern compilation failed"
}
```

#### Out of Scope
```json
{
  "decision": "ALLOW",
  "reason_code": "CASIL_OUT_OF_SCOPE"
}
```

#### Disabled
```json
{
  "decision": "ALLOW",
  "reason_code": "CASIL_DISABLED"
}
```

## Advanced Redaction Techniques

### Nested Field Redaction

Handle complex nested structures:

```json
{
  "user": {
    "profile": {
      "password": "secret",
      "settings": {
        "api_key": "key123"
      }
    }
  },
  "metadata": {
    "auth": {
      "token": "token456"
    }
  }
}
```

CASIL automatically handles any nesting level up to the maximum depth limit.

### Array Processing

Redact sensitive data within arrays:

```json
{
  "users": [
    {"name": "Alice", "password": "secret1"},
    {"name": "Bob", "password": "secret2"}
  ],
  "tokens": ["abc123", "def456", "ghi789"]
}
```

All array elements are processed recursively.

### Non-JSON Payload Handling

CASIL handles non-JSON payloads through pattern matching:

```bash
# For text payloads
export ARQONBUS_CASIL_REDACTION_PATTERNS="password\s*=\s*\S+,token\s*=\s*\S+"
```

## Redaction Testing

### Test Cases

```python
import json
from arqonbus.casil.redaction import redact_payload
from arqonbus.config.config import CASILConfig

def test_redaction():
    config = CASILConfig()
    config.policies.redaction.paths = ["password", "token"]
    
    # Test nested redaction
    payload = {
        "user": {
            "password": "secret123",
            "profile": {
                "token": "abc789"
            }
        },
        "data": "some text with password=secret and token=xyz"
    }
    
    redacted = redact_payload(payload, config, "logs", "test:channel")
    print(json.dumps(redacted, indent=2))

test_redaction()
```

### Pattern Validation Script

```python
#!/usr/bin/env python3
"""Validate CASIL patterns against test data."""

import re
import json
import sys

def validate_patterns():
    patterns = [
        r"(?i)api[_-]?key",
        r"(?i)secret", 
        r"(?i)token",
        r"(?i)password"
    ]
    
    test_cases = [
        {"text": "My API key is secret123", "should_match": True},
        {"text": "Hello world", "should_match": False},
        {"text": "api_key: abc123", "should_match": True},
        {"text": "Secret message", "should_match": True},
    ]
    
    for i, test in enumerate(test_cases):
        matches = []
        for pattern in patterns:
            if re.search(pattern, test["text"]):
                matches.append(pattern)
        
        expected = test["should_match"]
        actual = len(matches) > 0
        
        status = "✓" if actual == expected else "✗"
        print(f"{status} Test {i+1}: {test['text']}")
        
        if matches:
            print(f"  Matched patterns: {matches}")
        
        if actual != expected:
            print(f"  ERROR: Expected {expected}, got {actual}")

if __name__ == "__main__":
    validate_patterns()
```

## Performance Considerations

### Pattern Limit Impact

```python
# Performance test for pattern limits
def performance_test():
    import time
    
    test_text = "x" * 10000  # 10KB of text
    pattern_counts = [1, 8, 16, 32, 64]
    
    for count in pattern_counts:
        patterns = [r"(?i)secret"] * count
        
        start = time.time()
        for _ in range(1000):
            for pattern in patterns:
                re.search(pattern, test_text)
        end = time.time()
        
        print(f"{count} patterns: {(end-start)*1000:.1f}ms")

performance_test()
```

### Inspection Size Trade-offs

| max_inspect_bytes | Inspection Depth | Performance Impact |
|-------------------|------------------|-------------------|
| 32KB | Surface level | ~1ms per message |
| 64KB | Standard | ~2ms per message |
| 128KB | Deep inspection | ~4ms per message |

## Troubleshooting Redaction

### Common Issues

#### Patterns Not Matching
- Check regex syntax
- Verify case sensitivity flags
- Test with simple examples first

#### False Positives
- Narrow scope patterns
- Add negative lookahead assertions
- Use more specific patterns

#### Performance Issues
- Reduce pattern count
- Lower inspection size limits
- Use monitor mode during high load

### Debug Commands

```bash
# Test pattern matching
echo "api_key=secret123" | grep -E "(?i)api[_-]?key"

# Validate JSON structure
echo '{"password": "secret"}' | python -m json.tool

# Test CASIL classification
python -c "
from arqonbus.casil.classifier import classify
from arqonbus.config.config import CASILConfig
from arqonbus.protocol.envelope import Envelope

config = CASILConfig()
envelope = Envelope(type='message', room='test', channel='chat', payload={'password': 'secret'})
result = classify(envelope, config, {})
print(f'Classification: {result.kind}, Risk: {result.risk_level}')
print(f'Flags: {result.flags}')
"
```

---

**Next**: Learn about [Monitoring & Telemetry](monitoring.md) or [Best Practices](best-practices.md) for production deployment.