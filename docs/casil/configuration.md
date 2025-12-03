# CASIL Configuration Guide

This guide covers all configuration options for CASIL, including environment variables, security policies, and performance tuning.

## Configuration Overview

CASIL configuration is managed through environment variables prefixed with `ARQONBUS_CASIL_`. All configurations support runtime updates and validation.

## Basic Configuration

### Enable/Disable CASIL

```bash
# Enable CASIL
export ARQONBUS_CASIL_ENABLED=true

# Disable CASIL (default)
export ARQONBUS_CASIL_ENABLED=false
```

**Impact**: When disabled, CASIL adds zero overhead to message processing.

### Operational Modes

#### Monitor Mode (Recommended for Initial Deployment)

```bash
export ARQONBUS_CASIL_MODE=monitor
```

**Behavior**:
- ✅ Inspects all scoped messages
- ✅ Emits telemetry and classification
- ✅ Applies redaction to logs/telemetry
- ❌ Never blocks messages
- ❌ Never redacts transport payloads
- 🎯 **Use Case**: Safe initial deployment, testing policies

#### Enforce Mode (Production Security)

```bash
export ARQONBUS_CASIL_MODE=enforce
```

**Behavior**:
- ✅ All monitor mode features
- ✅ Blocks messages that violate policies
- ✅ Redacts transport payloads when configured
- ✅ Returns structured errors to clients
- 🎯 **Use Case**: Production security enforcement

### Default Decision on Errors

```bash
# Fail-open (default) - allow messages if CASIL fails
export ARQONBUS_CASIL_DEFAULT_DECISION=allow

# Fail-closed - block messages if CASIL fails
export ARQONBUS_CASIL_DEFAULT_DECISION=block
```

## Scope Configuration

Scope determines which messages CASIL inspects. Use include/exclude patterns to target specific channels.

### Include Patterns

```bash
# Inspect specific channels
export ARQONBUS_CASIL_SCOPE_INCLUDE="secure-*,pii-*,finance-*"

# Multiple patterns
export ARQONBUS_CASIL_SCOPE_INCLUDE="api-*,service-*,internal-*"
```

### Exclude Patterns

```bash
# Exclude specific channels from inspection
export ARQONBUS_CASIL_SCOPE_EXCLUDE="secure-internal:logs,pii:debug"

# Combine with include
export ARQONBUS_CASIL_SCOPE_INCLUDE="*"
export ARQONBUS_CASIL_SCOPE_EXCLUDE="public-*,test-*"
```

### Pattern Syntax

- **Prefix matching**: `secure-*` matches `secure-chat`, `secure-payments`
- **Full matching**: `secure-chat` matches only `secure-chat`
- **Glob patterns**: Use `fnmatch` syntax for advanced matching

### Examples

```bash
# Financial application
export ARQONBUS_CASIL_SCOPE_INCLUDE="payment-*,billing-*,finance-*,account-*"
export ARQONBUS_CASIL_SCOPE_EXCLUDE="payment:test-*"

# Healthcare application  
export ARQONBUS_CASIL_SCOPE_INCLUDE="patient-*,medical-*,phi-*,hipaa-*"
export ARQONBUS_CASIL_SCOPE_EXCLUDE="medical:debug,patient:test-*"

# Multi-tenant SaaS
export ARQONBUS_CASIL_SCOPE_INCLUDE="tenant-*"
export ARQONBUS_CASIL_SCOPE_EXCLUDE="tenant-internal:*"
```

## Security Policies

### Payload Size Limits

```bash
# Maximum payload size (default: 262144 bytes = 256KB)
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=524288  # 512KB
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=1048576 # 1MB
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=51200   # 50KB (strict)
```

**Behavior**:
- Messages larger than limit are classified as `oversize_payload`
- Can be blocked or monitored depending on mode
- Helps prevent DoS attacks and memory issues

### Secret Detection and Blocking

```bash
# Enable blocking of probable secrets (default: false)
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true

# Disable blocking (monitor only)
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=false
```

**Default Secret Patterns**:
- `(?i)api[_-]?key` - API keys
- `(?i)secret` - Generic secrets
- `(?i)token` - Authentication tokens
- `(?i)password` - Passwords
- `(?i)bearer\s+[A-Za-z0-9\-\._]+` - Bearer tokens

### Custom Secret Patterns

```bash
# Add custom regex patterns for your secrets
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)credit_card:\s*\d{16},(?i)ssn:\s*\d{3}-\d{2}-\d{4},(?i)private_key:"

# Multiple patterns (comma-separated)
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)jwt:\s*[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+,(?i)api_secret:\s*[a-z0-9]{32,}"
```

**Pattern Guidelines**:
- Use regex syntax
- Case-insensitive matching recommended with `(?i)`
- Test patterns thoroughly before production
- Limit to 32 patterns maximum (configurable)

## Redaction Configuration

### Field Path Redaction

```bash
# Redact specific JSON fields (default: password,token,secret)
export ARQONBUS_CASIL_REDACTION_PATHS="password,token,secret,api_key,private_key,ssn,credit_card"

# Custom field combinations
export ARQONBUS_CASIL_REDACTION_PATHS="auth_token,refresh_token,access_key,secret_key,bearer_token"
```

**How it works**:
- Recursively searches JSON structures
- Redacts matching field names at any nesting level
- Replaces with `"***REDACTED***"`

### Transport Redaction

```bash
# Enable transport-level redaction (default: false)
export ARQONBUS_CASIL_TRANSPORT_REDACTION=true

# Disable transport redaction (logs only)
export ARQONBUS_CASIL_TRANSPORT_REDACTION=false
```

**Behavior**:
- **Disabled**: Original payload delivered, logs redacted
- **Enabled**: Both delivered payload and logs are redacted

### Full Payload Protection

```bash
# Never log full payloads for specific channel patterns
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="pii-*,patient-*,financial-*"

# Multiple patterns
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="secure-*,confidential-*,internal-*"
```

**Effect**: Messages to matching channels show `"***REDACTED***"` in logs and telemetry while preserving transport delivery.

## Performance Tuning

### Inspection Limits

```bash
# Maximum bytes to inspect per message (default: 65536 = 64KB)
export ARQONBUS_CASIL_MAX_INSPECT_BYTES=32768   # 32KB (faster)
export ARQONBUS_CASIL_MAX_INSPECT_BYTES=131072  # 128KB (thorough)
```

**Trade-offs**:
- **Lower values**: Faster processing, less thorough inspection
- **Higher values**: More thorough inspection, slightly slower

### Pattern Limits

```bash
# Maximum regex patterns to evaluate (default: 32)
export ARQONBUS_CASIL_MAX_PATTERNS=16  # Performance-focused
export ARQONBUS_CASIL_MAX_PATTERNS=64  # Comprehensive coverage
```

**Considerations**:
- More patterns = more thorough detection
- More patterns = higher CPU usage
- Monitor pattern evaluation time in production

## Metadata Exposure

Control where CASIL metadata appears:

```bash
# Include CASIL metadata in logs (default: true)
export ARQONBUS_CASIL_METADATA_TO_LOGS=true

# Include CASIL metadata in telemetry (default: true)
export ARQONBUS_CASIL_METADATA_TO_TELEMETRY=true

# Include CASIL metadata in message envelopes (default: false)
export ARQONBUS_CASIL_METADATA_TO_ENVELOPE=true
```

**Envelope Metadata Example**:
```json
{
  "type": "message",
  "room": "secure-chat",
  "channel": "general",
  "payload": {...},
  "casil_metadata": {
    "classification": {
      "kind": "data",
      "risk_level": "low",
      "flags": {}
    },
    "decision": "ALLOW",
    "reason_code": "CASIL_POLICY_ALLOWED"
  }
}
```

## Complete Configuration Examples

### Development Environment

```bash
# Safe monitoring in development
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=monitor
export ARQONBUS_CASIL_SCOPE_INCLUDE="dev-*,test-*,staging-*"
export ARQONBUS_CASIL_DEFAULT_DECISION=allow
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=false
export ARQONBUS_CASIL_REDACTION_PATHS="password,token,secret"
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="pii-*,test-*"
```

### Production Financial Application

```bash
# Strict security for financial data
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=enforce
export ARQONBUS_CASIL_SCOPE_INCLUDE="payment-*,billing-*,finance-*,account-*"
export ARQONBUS_CASIL_SCOPE_EXCLUDE="payment:test-*,finance:debug"
export ARQONBUS_CASIL_DEFAULT_DECISION=block
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=524288
export ARQONBUS_CASIL_REDACTION_PATHS="password,token,secret,api_key,credit_card,ssn"
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)credit_card:\s*\d{16},(?i)ssn:\s*\d{3}-\d{2}-\d{4}"
export ARQONBUS_CASIL_TRANSPORT_REDACTION=true
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="payment-*,finance-*"
```

### Healthcare Application (HIPAA)

```bash
# HIPAA-compliant configuration
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=enforce
export ARQONBUS_CASIL_SCOPE_INCLUDE="patient-*,medical-*,phi-*,hipaa-*"
export ARQONBUS_CASIL_SCOPE_EXCLUDE="patient:test-*,medical:debug"
export ARQONBUS_CASIL_DEFAULT_DECISION=block
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=1048576  # 1MB for medical images
export ARQONBUS_CASIL_REDACTION_PATHS="ssn,dob,medical_record_number,patient_id,insurance_id"
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)ssn:\s*\d{3}-\d{2}-\d{4},(?i)medical_record:\s*[A-Z]{2}\d{8}"
export ARQONBUS_CASIL_TRANSPORT_REDACTION=true
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="patient-*,phi-*"
```

### Multi-tenant SaaS

```bash
# Tenant-isolated security
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=enforce
export ARQONBUS_CASIL_SCOPE_INCLUDE="tenant-*"
export ARQONBUS_CASIL_SCOPE_EXCLUDE="tenant-internal:*,tenant:test-*"
export ARQONBUS_CASIL_DEFAULT_DECISION=allow
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=262144
export ARQONBUS_CASIL_REDACTION_PATHS="api_key,secret_token,auth_token,refresh_token"
export ARQONBUS_CASIL_TRANSPORT_REDACTION=false  # Preserve tenant data
export ARQONBUS_CASIL_METADATA_TO_ENVELOPE=true  # Help tenants audit
```

## Configuration Validation

### Manual Validation

```python
from arqonbus.config.config import load_config

# Load and validate configuration
config = load_config()
errors = config.validate()

if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Configuration is valid!")
```

### Runtime Validation

CASIL validates configuration at startup and logs results:

```bash
# Check startup logs for validation
grep "CASIL configuration" /var/log/arqonbus.log

# Example successful validation:
# CASIL configuration loaded: mode=monitor, scope=[secure-*], limits=65536
```

## Environment-Specific Configurations

### Docker/Kubernetes

```yaml
# docker-compose.yml
services:
  arqonbus:
    environment:
      - ARQONBUS_CASIL_ENABLED=true
      - ARQONBUS_CASIL_MODE=${CASIL_MODE:-monitor}
      - ARQONBUS_CASIL_SCOPE_INCLUDE=${CASIL_SCOPE:-secure-*}
      - ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=${CASIL_STRICT:-false}
```

### Systemd Service

```ini
# /etc/systemd/system/arqonbus.service
[Service]
Environment=ARQONBUS_CASIL_ENABLED=true
Environment=ARQONBUS_CASIL_MODE=enforce
Environment=ARQONBUS_CASIL_SCOPE_INCLUDE=secure-*,pii-*
```

### CI/CD Pipeline

```yaml
# GitHub Actions
- name: Deploy with CASIL
  env:
    ARQONBUS_CASIL_ENABLED: ${{ secrets.CASIL_ENABLED }}
    ARQONBUS_CASIL_MODE: ${{ secrets.CASIL_MODE }}
    ARQONBUS_CASIL_SCOPE_INCLUDE: ${{ secrets.CASIL_SCOPE }}
  run: ./deploy.sh
```

## Configuration Management Best Practices

1. **Start with Monitor Mode**: Always test policies in monitor mode first
2. **Use Environment Variables**: Avoid hardcoding sensitive patterns
3. **Validate Regularly**: Test configuration changes in staging
4. **Document Patterns**: Comment your custom regex patterns
5. **Monitor Performance**: Watch for impacts on message throughput
6. **Version Control**: Track configuration changes in git
7. **Backup Configs**: Keep working configurations as backups

## Troubleshooting Configuration

### Common Issues

1. **Patterns Not Matching**: Test regex patterns manually
2. **Scope Too Broad**: Narrow include patterns to reduce overhead
3. **Performance Issues**: Lower inspection limits and pattern counts
4. **False Positives**: Refine patterns or adjust scope
5. **Missing Metadata**: Check metadata exposure settings

### Debug Commands

```bash
# Test pattern matching
python -c "
import re
pattern = r'(?i)api.*key'
test_string = 'my API key is secret'
print(bool(re.search(pattern, test_string)))
"

# Check configuration
python -c "
from arqonbus.config.config import load_config
config = load_config()
print(config.to_dict())
"
```

---

**Next**: Learn about [Redaction & Safety](redaction.md) mechanisms, or see [Best Practices](best-practices.md) for production deployment.