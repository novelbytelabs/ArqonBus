# CASIL Manual - Content-Aware Safety & Inspection Layer

**CASIL** (Content-Aware Safety & Inspection Layer) is an optional, configurable security layer in ArqonBus that inspects messages, applies safety policies, redacts sensitive content, and provides comprehensive telemetry. CASIL is designed for production deployments that require content security and compliance monitoring.

## Quick Start

- **Enable CASIL**: Set `ARQONBUS_CASIL_ENABLED=true`
- **Start in Monitor Mode**: `ARQONBUS_CASIL_MODE=monitor`
- **Basic Scoping**: `ARQONBUS_CASIL_SCOPE_INCLUDE=secure-*,pii-*`

## Documentation Structure

### 🚀 [Getting Started](getting-started.md)
- Installation and basic setup
- First configuration
- Common use cases

### ⚙️ [Configuration Guide](configuration.md)
- Environment variables
- Configuration patterns
- Security policies
- Performance tuning

### 🔒 [Redaction & Safety](redaction.md)
- Content classification
- Pattern-based redaction
- Path-based field masking
- Transport vs observability redaction

### 📊 [Monitoring & Telemetry](monitoring.md)
- Metrics and observability
- Alert integration
- Performance monitoring
- Troubleshooting

### 🎯 [Best Practices](best-practices.md)
- Security recommendations
- Performance optimization
- Production deployment
- Incident response

### 📖 [API Reference](api-reference.md)
- Configuration schema
- Policy definitions
- Error codes
- Integration examples

## Core Features

### Content Classification
CASIL automatically classifies messages by type and risk level:
- **Message Types**: `control`, `telemetry`, `data`, `system`
- **Risk Levels**: `low`, `medium`, `high`
- **Detection Flags**: `contains_probable_secret`, `oversize_payload`

### Safety Policies
- **Size Limits**: Prevent oversized payloads (default: 256KB)
- **Secret Detection**: Block or redact probable secrets
- **Custom Patterns**: User-defined regex patterns
- **Field Masking**: Redact specific JSON fields

### Redaction Capabilities
- **Path-based**: Target specific JSON field paths
- **Pattern-based**: Regex matching for sensitive content
- **Full payload**: Complete message redaction for sensitive channels
- **Dual-layer**: Transport vs observability redaction

### Operational Modes
- **Monitor**: Emits telemetry but never blocks messages
- **Enforce**: Applies full blocking and redaction policies

### Performance Features
- **Negligible overhead** when disabled (near 0% impact)
- **Scope-based filtering** for targeted inspection
- **Bounded processing** with configurable limits
- **Deterministic classification** for predictable behavior

## Key Benefits

- 🔒 **Security**: Prevent sensitive data leakage
- 📊 **Compliance**: Audit trails and content classification
- 🎯 **Precision**: Target specific channels and content types
- 🚀 **Performance**: Minimal overhead with smart scoping
- 🔧 **Flexibility**: Configurable policies without code changes
- 📈 **Observability**: Comprehensive monitoring and metrics

## When to Use CASIL

CASIL is recommended for:

- ✅ Production deployments with sensitive data
- ✅ Compliance requirements (PCI-DSS, HIPAA, GDPR)
- ✅ Multi-tenant applications
- ✅ Financial or healthcare applications
- ✅ Systems requiring audit trails
- ✅ Organizations with strict data governance

CASIL is not needed for:

- ❌ Development/test environments
- ❌ Public chat applications
- ❌ Low-risk internal tools
- ❌ Performance-critical applications with minimal security requirements

## Version Information

- **CASIL Version**: 1.0
- **Compatibility**: ArqonBus v1.0+
- **Python Version**: 3.11+
- **Last Updated**: 2025-12-03

---

*This manual covers CASIL v1.0. For the latest updates and examples, see the [ArqonBus repository](https://github.com/arqonbus/arqonbus).*