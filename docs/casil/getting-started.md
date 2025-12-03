# Getting Started with CASIL

This guide will help you get CASIL up and running quickly. We'll cover basic installation, configuration, and common use cases.

## Prerequisites

- ArqonBus v1.0 or later
- Python 3.11+
- Understanding of your message structure and security requirements

## Quick Setup (5 Minutes)

### Step 1: Enable CASIL

Set the environment variable to enable CASIL:

```bash
export ARQONBUS_CASIL_ENABLED=true
```

### Step 2: Start in Monitor Mode

For your first run, use monitor mode which emits telemetry but never blocks messages:

```bash
export ARQONBUS_CASIL_MODE=monitor
```

### Step 3: Define Scope

Choose which channels to inspect. For example, to inspect all channels starting with `secure-` or `pii-`:

```bash
export ARQONBUS_CASIL_SCOPE_INCLUDE="secure-*,pii-*"
```

### Step 4: Test Your Setup

Send a test message to a scoped channel:

```bash
# This message will be inspected but not blocked
{"message": "Hello world", "user": "test"}
```

```bash
# This message contains a secret and will be flagged
{"message": "User data", "api_key": "sk-1234567890abcdef"}
```

## Common Use Cases

### Use Case 1: Protect Financial Data

Configure CASIL to block messages with probable financial secrets:

```bash
# Enable enforcement mode
export ARQONBUS_CASIL_MODE=enforce

# Block probable secrets
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true

# Target financial channels
export ARQONBUS_CASIL_SCOPE_INCLUDE="finance-*,payment-*,billing-*"

# Set payload size limit
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=524288  # 512KB
```

**Expected Behavior**:
- Messages in financial channels are inspected
- Messages with credit card numbers, bank accounts, or API keys are blocked
- Oversized messages (>512KB) are blocked
- All decisions are logged with classification metadata

### Use Case 2: Monitor PII in Development

For development environments, monitor PII without blocking:

```bash
# Use monitor mode
export ARQONBUS_CASIL_MODE=monitor

# Focus on PII channels
export ARQONBUS_CASIL_SCOPE_INCLUDE="pii-*,user-*,customer-*"

# Redact sensitive fields in logs
export ARQONBUS_CASIL_REDACTION_PATHS="password,token,secret,ssn,credit_card"

# Never log full payloads for PII channels
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="pii-*"
```

**Expected Behavior**:
- PII messages are inspected and classified
- Sensitive fields are redacted in logs
- No messages are blocked (monitor mode)
- Telemetry shows PII detection rates

### Use Case 3: API Security

Protect API communications from secret leakage:

```bash
# Enable strict mode for API channels
export ARQONBUS_CASIL_MODE=enforce

# Target API channels
export ARQONBUS_CASIL_SCOPE_INCLUDE="api-*,service-*,microservice-*"

# Add custom patterns for your API secrets
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)authorization:\s*bearer\s+[a-z0-9]{32,},(?i)x-api-key:\s*[a-z0-9]{32,}"

# Redact tokens in transport
export ARQONBUS_CASIL_TRANSPORT_REDACTION=true
```

**Expected Behavior**:
- API messages are strictly inspected
- Bearer tokens and API keys are detected and redacted
- Messages with secrets may be blocked or redacted depending on configuration
- Redacted payloads are delivered to maintain message flow

## Verification Steps

### 1. Check CASIL Status

Verify CASIL is running by checking logs for CASIL initialization:

```bash
grep "CASIL initialized" /var/log/arqonbus.log
```

Expected output:
```
CASIL initialized with mode=monitor, scope=[secure-*, pii-*]
```

### 2. Test Classification

Send test messages and verify classification in logs:

```bash
# Test message (should be classified as 'data', risk 'low')
{"message": "hello world"}

# Test secret (should be flagged)
{"token": "secret_key_123"}
```

Check logs for classification:
```bash
grep "CASIL classification" /var/log/arqonbus.log
```

### 3. Monitor Telemetry

Check CASIL telemetry emission:

```bash
# Monitor telemetry channel
tail -f /var/log/arqonbus.log | grep "arqonbus.telemetry"
```

### 4. Verify Scoping

Test that out-of-scope messages bypass CASIL:

```bash
# This should NOT be inspected
{"message": "public chat message"}
```

Verify in logs that public messages don't appear in CASIL telemetry.

## Configuration Validation

CASIL validates configuration at startup. Check for validation errors:

```bash
# Start ArqonBus and check for configuration errors
./arqonbus-server

# Look for validation messages in output
grep "CASIL configuration" /var/log/arqonbus.log
```

### Common Validation Errors

1. **Invalid mode**: Must be "monitor" or "enforce"
2. **Invalid scope patterns**: Check syntax of include/exclude patterns
3. **Invalid limits**: Ensure numeric values are positive
4. **Invalid default decision**: Must be "allow" or "block"

## Performance Check

Verify CASIL isn't impacting performance significantly:

### With CASIL Disabled
```bash
# Measure message throughput
ab -n 1000 -c 10 -p test_message.json http://localhost:9100/api/send
```

### With CASIL Enabled (Monitor Mode)
```bash
# Measure with same parameters
ab -n 1000 -c 10 -p test_message.json http://localhost:9100/api/send
```

**Expected**: < 5% performance degradation in monitor mode

## Troubleshooting

### CASIL Not Working

1. **Check enable flag**: Ensure `ARQONBUS_CASIL_ENABLED=true`
2. **Verify scope**: Check that your messages target scoped channels
3. **Check logs**: Look for CASIL initialization and error messages
4. **Test configuration**: Use validation tools (see [Configuration Guide](configuration.md))

### High False Positives

1. **Review patterns**: Check if secret detection patterns are too broad
2. **Adjust scope**: Narrow the inspection scope to relevant channels
3. **Custom patterns**: Add exclusions for your specific use case

### Performance Issues

1. **Reduce scope**: Limit inspection to fewer channels
2. **Lower limits**: Reduce `max_inspect_bytes` for smaller inspection sizes
3. **Monitor mode**: Use monitor mode during high-load periods

## Next Steps

- 📖 **[Configuration Guide](configuration.md)** - Detailed configuration options
- 🔒 **[Redaction & Safety](redaction.md)** - Understanding how CASIL protects content
- 📊 **[Monitoring & Telemetry](monitoring.md)** - Setting up observability
- 🎯 **[Best Practices](best-practices.md)** - Production deployment tips

---

**Tip**: Start with monitor mode to understand your traffic patterns before enabling enforcement.