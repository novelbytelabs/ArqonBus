# CASIL Best Practices

Production deployment strategies, security recommendations, performance optimization, and incident response procedures for CASIL.

## Overview

This guide covers proven practices for deploying CASIL in production environments, maximizing security while maintaining performance and reliability.

## Deployment Strategy

### 1. Phased Rollout Approach

#### Phase 1: Monitor Mode Deployment
```bash
# Start with comprehensive monitoring
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=monitor
export ARQONBUS_CASIL_SCOPE_INCLUDE="*"  # Monitor everything initially
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=false
export ARQONBUS_CASIL_DEFAULT_DECISION=allow
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=262144
```

**Duration**: 1-2 weeks
**Goals**: 
- Understand traffic patterns
- Identify false positives
- Calibrate patterns
- Establish baseline metrics

#### Phase 2: Limited Enforcement
```bash
# Enable enforcement for high-risk channels only
export ARQONBUS_CASIL_MODE=enforce
export ARQONBUS_CASIL_SCOPE_INCLUDE="payment-*,finance-*,secure-*"
export ARQONBUS_CASIL_SCOPE_EXCLUDE="payment:test-*,finance:debug-*"
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true
export ARQONBUS_CASIL_TRANSPORT_REDACTION=true
```

**Duration**: 2-4 weeks
**Goals**:
- Test enforcement in controlled scope
- Monitor client impact
- Adjust patterns based on feedback
- Validate error handling

#### Phase 3: Full Deployment
```bash
# Expand to all appropriate channels
export ARQONBUS_CASIL_SCOPE_INCLUDE="secure-*,pii-*,finance-*,user-*,account-*"
export ARQONBUS_CASIL_SCOPE_EXCLUDE="chat:public-*,broadcast:*,test-*"
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true
```

**Duration**: Ongoing
**Goals**:
- Comprehensive security coverage
- Continuous optimization
- Performance monitoring

### 2. Environment-Specific Configuration

#### Development Environment
```bash
# Safe monitoring for developers
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=monitor
export ARQONBUS_CASIL_SCOPE_INCLUDE="dev-*,test-*,staging-*"
export ARQONBUS_CASIL_REDACTION_PATHS="password,token,secret,api_key"
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="pii-*,test-*"
export ARQONBUS_CASIL_METADATA_TO_LOGS=true
export ARQONBUS_CASIL_METADATA_TO_TELEMETRY=true
```

**Benefits**:
- Developers see classification data
- No production impact
- Educational value
- Test environment safety

#### Staging Environment
```bash
# Production-like testing
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=enforce  # Test enforcement
export ARQONBUS_CASIL_SCOPE_INCLUDE="*"
export ARQONBUS_CASIL_SCOPE_EXCLUDE="staging-internal:*"
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true
export ARQONBUS_CASIL_REDACTION_PATHS="password,token,secret,api_key,credit_card,ssn"
export ARQONBUS_CASIL_TRANSPORT_REDACTION=true
```

**Benefits**:
- Production pattern validation
- Performance testing
- Client compatibility testing
- Incident drill environment

#### Production Environment
```bash
# Optimized for security and performance
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=enforce
export ARQONBUS_CASIL_SCOPE_INCLUDE="secure-*,pii-*,finance-*,user-*,account-*"
export ARQONBUS_CASIL_SCOPE_EXCLUDE="public-*,broadcast-*,system:*"
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=262144
export ARQONBUS_CASIL_MAX_INSPECT_BYTES=65536
export ARQONBUS_CASIL_TRANSPORT_REDACTION=true
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="pii-*,secure-*"
```

## Security Hardening

### 1. Pattern Security

#### Avoid Overly Broad Patterns
```bash
# ❌ BAD - Too broad, will match legitimate content
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)key,secret,password"

# ✅ GOOD - Specific patterns with context
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)api[_-]?key:\s*\S+,(?i)password:\s*\S+,(?i)secret[_-]?key:\s*\S+"
```

#### Validate Pattern Security
```python
#!/usr/bin/env python3
"""Validate regex patterns for security and performance."""

import re
import time
import sys

def validate_pattern(pattern, test_cases):
    """Validate a regex pattern."""
    issues = []
    
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        issues.append(f"Regex compilation error: {e}")
        return issues
    
    # Test for catastrophic backtracking
    start_time = time.time()
    for _ in range(100):
        for test_case in test_cases:
            compiled.search(test_case)
    end_time = time.time()
    
    if end_time - start_time > 1.0:  # 1 second threshold
        issues.append("Potential catastrophic backtracking detected")
    
    # Test for false positives
    benign_cases = [
        "Hello world",
        "User message: hello",
        "Product name: Secret Squirrel",  # Should NOT match secret patterns
        "API documentation",             # Should NOT match API patterns
    ]
    
    matches = []
    for case in benign_cases:
        if compiled.search(case):
            matches.append(case)
    
    if matches:
        issues.append(f"Potential false positives: {matches}")
    
    return issues

def main():
    patterns = [
        r"(?i)api[_-]?key:\s*\S+",
        r"(?i)password:\s*\S+",
        r"(?i)secret:\s*\S+",
        r"(?i)token:\s*\S+"
    ]
    
    test_cases = [
        "api_key: sk-1234567890abcdef",
        "password: mypassword123",
        "secret: this_is_secret",
        "token: abc123xyz789"
    ]
    
    for pattern in patterns:
        issues = validate_pattern(pattern, test_cases + [
            "Hello world",
            "Public message",
            "Secret Squirrel",  # Should not match
            "API documentation"  # Should not match
        ])
        
        print(f"Pattern: {pattern}")
        if issues:
            for issue in issues:
                print(f"  ⚠️  {issue}")
        else:
            print(f"  ✅ Pattern validated")
        print()

if __name__ == "__main__":
    main()
```

### 2. Configuration Security

#### Secure Environment Variable Management
```bash
# ❌ BAD - Hardcoded in scripts
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true

# ✅ GOOD - Use secret management
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET="$(cat /run/secrets/casil_block_secrets)"
export ARQONBUS_CASIL_REDACTION_PATTERNS="$(cat /run/secrets/casil_patterns)"
```

#### Kubernetes Secrets Integration
```yaml
# casil-config.yaml
apiVersion: v1
kind: Secret
metadata:
  name: casil-config
type: Opaque
data:
  ARQONBUS_CASIL_REDACTION_PATTERNS: <base64-encoded-patterns>
  ARQONBUS_CASIL_REDACTION_PATHS: <base64-encoded-paths>
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: casil-settings
data:
  ARQONBUS_CASIL_ENABLED: "true"
  ARQONBUS_CASIL_MODE: "enforce"
  ARQONBUS_CASIL_SCOPE_INCLUDE: "secure-*,pii-*"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: arqonbus
spec:
  template:
    spec:
      containers:
      - name: arqonbus
        env:
        - name: ARQONBUS_CASIL_ENABLED
          valueFrom:
            configMapKeyRef:
              name: casil-settings
              key: ARQONBUS_CASIL_ENABLED
        envFrom:
        - secretRef:
            name: casil-config
```

### 3. Access Control

#### Restrict CASIL Configuration Access
```bash
# Create dedicated CASIL configuration group
sudo groupadd casil-admin

# Restrict configuration files
sudo chown -R :casil-admin /etc/arqonbus/
sudo chmod 750 /etc/arqonbus/

# Add users to configuration group
sudo usermod -a -G casil-admin devops-user
sudo usermod -a -G casil-admin security-user

# Prevent regular users from seeing CASIL patterns
sudo chmod 640 /etc/arqonbus/casil.conf
```

## Performance Optimization

### 1. Scope Optimization

#### Strategic Scope Selection
```bash
# ✅ GOOD - Specific, high-value targets
export ARQONBUS_CASIL_SCOPE_INCLUDE="payment-*,finance-*,secure-*,pii-*"

# ❌ BAD - Too broad, impacts performance
export ARQONBUS_CASIL_SCOPE_INCLUDE="*"

# ✅ GOOD - Exclude high-volume, low-risk channels
export ARQONBUS_CASIL_SCOPE_EXCLUDE="chat:public-*,broadcast:*,system:metrics"
```

#### Performance Monitoring
```python
#!/usr/bin/env python3
"""Monitor CASIL performance impact."""

import time
import statistics
from collections import deque

class CASILPerformanceOptimizer:
    def __init__(self):
        self.processing_times = deque(maxlen=10000)
        self.throughput_before = 0
        self.throughput_after = 0
        
    def measure_throughput_impact(self, duration=60):
        """Measure message throughput with/without CASIL."""
        import subprocess
        import re
        
        # Measure baseline (CASIL disabled)
        print("Measuring baseline throughput (CASIL disabled)...")
        
        # This is a simplified example - adapt for your environment
        baseline_results = []
        for i in range(3):
            start_time = time.time()
            # Send test messages
            # subprocess.run(['ab', '-n', '1000', '-c', '10', 'http://localhost:9100/test'])
            end_time = time.time()
            baseline_results.append(1000 / (end_time - start_time))
            time.sleep(1)
        
        baseline_throughput = statistics.mean(baseline_results)
        
        # Measure with CASIL
        print("Measuring throughput with CASIL...")
        casil_results = []
        for i in range(3):
            start_time = time.time()
            # Send same test messages with CASIL enabled
            # subprocess.run(['ab', '-n', '1000', '-c', '10', 'http://localhost:9100/test'])
            end_time = time.time()
            casil_results.append(1000 / (end_time - start_time))
            time.sleep(1)
        
        casil_throughput = statistics.mean(casil_results)
        
        impact_percent = ((baseline_throughput - casil_throughput) / baseline_throughput) * 100
        
        print(f"Baseline throughput: {baseline_throughput:.1f} msg/sec")
        print(f"CASIL throughput: {casil_throughput:.1f} msg/sec")
        print(f"Performance impact: {impact_percent:.1f}%")
        
        if impact_percent > 5:
            print("⚠️  Performance impact exceeds 5% - consider scope optimization")
        
        return impact_percent
    
    def analyze_bottlenecks(self):
        """Analyze processing time bottlenecks."""
        if len(self.processing_times) < 100:
            print("Need more data for bottleneck analysis")
            return
        
        recent_times = list(self.processing_times)[-1000:]
        
        p50 = statistics.median(recent_times)
        p95 = statistics.quantiles(recent_times, n=20)[18]
        p99 = statistics.quantiles(recent_times, n=100)[98]
        
        print(f"Processing time analysis:")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {p99:.2f}ms")
        
        if p95 > 10:
            print("⚠️  High processing time - consider:")
            print("    - Reducing max_inspect_bytes")
            print("    - Limiting regex patterns")
            print("    - Narrowing inspection scope")

if __name__ == "__main__":
    optimizer = CASILPerformanceOptimizer()
    optimizer.measure_throughput_impact()
```

### 2. Resource Optimization

#### Memory Management
```bash
# Optimize for memory-constrained environments
export ARQONBUS_CASIL_MAX_INSPECT_BYTES=32768   # 32KB instead of 64KB
export ARQONBUS_CASIL_MAX_PATTERNS=16          # Limit regex patterns
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=131072 # 128KB payload limit
```

#### CPU Optimization
```bash
# Optimize for CPU-constrained environments  
export ARQONBUS_CASIL_SCOPE_INCLUDE="secure-*,pii-*"
export ARQONBUS_CASIL_MAX_INSPECT_BYTES=16384   # 16KB for fast processing
export ARQONBUS_CASIL_MAX_PATTERNS=8           # Minimal patterns
```

### 3. Caching Strategies

#### Pattern Compilation Caching
```python
# casil/cache.py
import re
import threading
from functools import lru_cache

class PatternCache:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._cache = {}
        return cls._instance
    
    @lru_cache(maxsize=100)
    def get_compiled_pattern(self, pattern_str):
        """Get cached compiled pattern."""
        if pattern_str not in self._cache:
            try:
                self._cache[pattern_str] = re.compile(pattern_str)
            except re.error as e:
                raise ValueError(f"Invalid pattern {pattern_str}: {e}")
        return self._cache[pattern_str]
    
    def clear_cache(self):
        """Clear pattern cache."""
        self._cache.clear()

# Usage in classifier
from casil.cache import PatternCache

cache = PatternCache()
def classify_with_cache(pattern, text):
    compiled_pattern = cache.get_compiled_pattern(pattern)
    return compiled_pattern.search(text)
```

## Incident Response

### 1. Security Incident Response

#### Immediate Response (0-15 minutes)
```bash
# 1. Switch to monitor mode to prevent blocking
export ARQONBUS_CASIL_MODE=monitor

# 2. Increase logging verbosity
export ARQONBUS_LOG_LEVEL=DEBUG

# 3. Expand scope to catch all violations
export ARQONBUS_CASIL_SCOPE_INCLUDE="*"

# 4. Alert security team
curl -X POST https://alerts.company.com/security \
  -H "Content-Type: application/json" \
  -d '{"severity":"critical","message":"CASIL security incident detected"}'
```

#### Investigation (15-60 minutes)
```bash
# Collect incident data
./scripts/collect-casil-incident-data.sh

# Analyze recent violations
grep "CASIL_POLICY_BLOCKED_SECRET" /var/log/arqonbus.log | \
  tail -100 > incident_violations.log

# Check for patterns causing issues
grep "false_positive" /var/log/arqonbus.log | \
  tail -50 > false_positives.log

# Review client impact
grep "CASIL_INTERNAL_ERROR" /var/log/arqonbus.log | \
  tail -20 > internal_errors.log
```

#### Recovery (60+ minutes)
```bash
# 1. Fix problematic patterns
export ARQONBUS_CASIL_REDACTION_PATTERNS="fixed_patterns"

# 2. Gradually restore enforcement
export ARQONBUS_CASIL_MODE=monitor  # Monitor for 30 minutes
export ARQONBUS_CASIL_MODE=enforce  # Then enforce

# 3. Verify system stability
./scripts/verify-casil-health.sh

# 4. Document incident
./scripts/generate-incident-report.sh
```

### 2. Performance Incident Response

#### High Latency Response
```bash
# 1. Temporarily reduce scope
export ARQONBUS_CASIL_SCOPE_INCLUDE="secure-*,payment-*"

# 2. Reduce inspection size
export ARQONBUS_CASIL_MAX_INSPECT_BYTES=16384

# 3. Limit patterns
export ARQONBUS_CASIL_MAX_PATTERNS=8

# 4. Monitor recovery
./scripts/monitor-casil-performance.sh
```

#### False Positive Response
```bash
# 1. Switch to monitor mode
export ARQONBUS_CASIL_MODE=monitor

# 2. Add exclusions for problematic patterns
export ARQONBUS_CASIL_SCOPE_EXCLUDE="client-app:specific-channel"

# 3. Refine patterns
export ARQONBUS_CASIL_REDACTION_PATTERNS="improved_patterns"

# 4. Test in staging first
```

### 3. Incident Response Scripts

#### Automated Incident Response
```bash
#!/usr/bin/env python3
#!/usr/bin/env python3
"""CASIL incident response automation."""

import os
import sys
import time
import json
import subprocess
from datetime import datetime

class CASILIncidentResponse:
    def __init__(self):
        self.incident_start = datetime.now()
        self.actions_taken = []
    
    def log_action(self, action):
        """Log response action."""
        timestamp = datetime.now().isoformat()
        self.actions_taken.append({
            'timestamp': timestamp,
            'action': action
        })
        print(f"[{timestamp}] {action}")
    
    def switch_to_monitor_mode(self):
        """Switch CASIL to monitor mode."""
        os.environ['ARQONBUS_CASIL_MODE'] = 'monitor'
        self.log_action("Switched to monitor mode")
        
        # Reload configuration
        subprocess.run(['systemctl', 'reload', 'arqonbus'])
        time.sleep(5)  # Wait for reload
    
    def expand_scope(self):
        """Expand CASIL scope for investigation."""
        os.environ['ARQONBUS_CASIL_SCOPE_INCLUDE'] = '*'
        self.log_action("Expanded scope to all channels")
        
        subprocess.run(['systemctl', 'reload', 'arqonbus'])
        time.sleep(5)
    
    def enable_debug_logging(self):
        """Enable debug logging."""
        os.environ['ARQONBUS_LOG_LEVEL'] = 'DEBUG'
        self.log_action("Enabled debug logging")
        
        subprocess.run(['systemctl', 'reload', 'arqonbus'])
    
    def collect_incident_data(self):
        """Collect data for incident investigation."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        incident_file = f"casil_incident_{timestamp}.json"
        
        # Collect logs
        result = subprocess.run([
            'grep', 'CASIL', '/var/log/arqonbus.log'
        ], capture_output=True, text=True)
        
        incident_data = {
            'incident_start': self.incident_start.isoformat(),
            'actions_taken': self.actions_taken,
            'recent_casil_logs': result.stdout,
            'system_state': {
                'mode': os.environ.get('ARQONBUS_CASIL_MODE'),
                'scope': os.environ.get('ARQONBUS_CASIL_SCOPE_INCLUDE'),
                'block_on_secret': os.environ.get('ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET')
            }
        }
        
        with open(incident_file, 'w') as f:
            json.dump(incident_data, f, indent=2)
        
        self.log_action(f"Collected incident data to {incident_file}")
        return incident_file
    
    def recover_from_incident(self, incident_type):
        """Execute recovery based on incident type."""
        if incident_type == "security":
            self.recover_from_security_incident()
        elif incident_type == "performance":
            self.recover_from_performance_incident()
        elif incident_type == "false_positive":
            self.recover_from_false_positive()
        else:
            self.log_action(f"Unknown incident type: {incident_type}")
    
    def recover_from_security_incident(self):
        """Recover from security incident."""
        self.log_action("Starting security incident recovery")
        
        # Restore normal configuration
        os.environ['ARQONBUS_CASIL_MODE'] = 'enforce'
        os.environ['ARQONBUS_CASIL_SCOPE_INCLUDE'] = 'secure-*,pii-*'
        os.environ['ARQONBUS_LOG_LEVEL'] = 'INFO'
        
        subprocess.run(['systemctl', 'reload', 'arqonbus'])
        self.log_action("Restored normal configuration")
    
    def recover_from_performance_incident(self):
        """Recover from performance incident."""
        self.log_action("Starting performance incident recovery")
        
        # Optimize for performance
        os.environ['ARQONBUS_CASIL_MAX_INSPECT_BYTES'] = '32768'
        os.environ['ARQONBUS_CASIL_MAX_PATTERNS'] = '16'
        os.environ['ARQONBUS_CASIL_SCOPE_INCLUDE'] = 'secure-*'
        
        subprocess.run(['systemctl', 'reload', 'arqonbus'])
        self.log_action("Applied performance optimization")
    
    def recover_from_false_positive(self):
        """Recover from false positive incident."""
        self.log_action("Starting false positive recovery")
        
        # Exclude problematic patterns
        scope_exclude = os.environ.get('ARQONBUS_CASIL_SCOPE_EXCLUDE', '')
        os.environ['ARQONBUS_CASIL_SCOPE_EXCLUDE'] = scope_exclude + ",problematic-channel:*"
        
        subprocess.run(['systemctl', 'reload', 'arqonbus'])
        self.log_action("Added exclusions for false positive patterns")

def main():
    if len(sys.argv) < 2:
        print("Usage: casil-incident-response <incident_type>")
        print("Incident types: security, performance, false_positive")
        sys.exit(1)
    
    incident_type = sys.argv[1]
    
    response = CASILIncidentResponse()
    
    # Execute immediate response
    response.switch_to_monitor_mode()
    response.expand_scope()
    response.enable_debug_logging()
    
    # Collect data for investigation
    incident_file = response.collect_incident_data()
    
    print(f"\nIncident response initiated.")
    print(f"Data collected in: {incident_file}")
    print("Review the data and run recovery when ready.")
    print(f"To recover: {sys.argv[0]} recover {incident_type}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "recover":
        incident_type = sys.argv[2]
        response = CASILIncidentResponse()
        response.recover_from_incident(incident_type)
    else:
        main()
```

## Compliance and Auditing

### 1. Audit Trail Management

#### Compliance Logging
```python
#!/usr/bin/env python3
"""CASIL compliance audit trail generator."""

import json
import time
from datetime import datetime, timedelta
from collections import defaultdict

class CASILAuditTrail:
    def __init__(self, log_file='/var/log/arqonbus.log'):
        self.log_file = log_file
        
    def generate_compliance_report(self, start_date, end_date):
        """Generate compliance report for audit."""
        report = {
            'audit_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'security_controls': {},
            'data_protection': {},
            'access_controls': {},
            'compliance_score': 0
        }
        
        # Analyze security events
        security_events = self._analyze_security_events(start_date, end_date)
        report['security_controls'] = security_events
        
        # Analyze data protection measures
        data_protection = self._analyze_data_protection(start_date, end_date)
        report['data_protection'] = data_protection
        
        # Calculate compliance score
        score = self._calculate_compliance_score(security_events, data_protection)
        report['compliance_score'] = score
        
        return report
    
    def _analyze_security_events(self, start_date, end_date):
        """Analyze security events for compliance."""
        events = {
            'total_inspections': 0,
            'blocked_messages': 0,
            'redacted_messages': 0,
            'secret_detections': 0,
            'policy_violations': defaultdict(int)
        }
        
        with open(self.log_file) as f:
            for line in f:
                # Parse timestamp and filter by date range
                # This is simplified - implement proper date parsing
                if 'CASIL_INSPECTION' in line:
                    events['total_inspections'] += 1
                    
                    if 'decision.*BLOCK' in line:
                        events['blocked_messages'] += 1
                    elif 'decision.*ALLOW_WITH_REDACTION' in line:
                        events['redacted_messages'] += 1
                    
                    if 'contains_probable_secret.*true' in line:
                        events['secret_detections'] += 1
        
        return events
    
    def _analyze_data_protection(self, start_date, end_date):
        """Analyze data protection measures."""
        protection = {
            'payloads_redacted': 0,
            'patterns_applied': 0,
            'channels_protected': set(),
            'redaction_effectiveness': 0
        }
        
        # Implementation for data protection analysis
        # ... (similar to _analyze_security_events)
        
        return protection
    
    def _calculate_compliance_score(self, security_events, data_protection):
        """Calculate overall compliance score."""
        score = 0
        
        # Block rate (higher = better security)
        if security_events['total_inspections'] > 0:
            block_rate = security_events['blocked_messages'] / security_events['total_inspections']
            score += min(30, block_rate * 100)  # Max 30 points
        
        # Redaction effectiveness
        redaction_rate = data_protection.get('redaction_effectiveness', 0)
        score += min(40, redaction_rate)  # Max 40 points
        
        # Coverage (channels protected)
        coverage = len(data_protection.get('channels_protected', set()))
        score += min(30, coverage)  # Max 30 points
        
        return min(100, score)

# Generate audit report
if __name__ == "__main__":
    audit = CASILAuditTrail()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    report = audit.generate_compliance_report(start_date, end_date)
    
    # Save report
    with open(f'casil_audit_report_{end_date.strftime("%Y%m%d")}.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Compliance score: {report['compliance_score']:.1f}/100")
    print("Audit report generated successfully.")
```

### 2. Regulatory Compliance

#### GDPR Compliance
```bash
# GDPR-focused CASIL configuration
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=enforce
export ARQONBUS_CASIL_SCOPE_INCLUDE="pii-*,user-*,customer-*"
export ARQONBUS_CASIL_REDACTION_PATHS="email,phone,address,ssn,dob,first_name,last_name"
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)email:\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="pii-*,user-*"
export ARQONBUS_CASIL_TRANSPORT_REDACTION=true
```

#### HIPAA Compliance
```bash
# HIPAA-focused CASIL configuration
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=enforce
export ARQONBUS_CASIL_SCOPE_INCLUDE="patient-*,medical-*,phi-*,hipaa-*"
export ARQONBUS_CASIL_REDACTION_PATHS="patient_id,medical_record_number,ssn,dob,diagnosis,treatment"
export ARQONBUS_CASIL_MAX_PAYLOAD_BYTES=5242880  # 5MB for medical images
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="patient-*,phi-*"
export ARQONBUS_CASIL_METADATA_TO_LOGS=false  # Minimize PHI exposure
```

#### PCI-DSS Compliance
```bash
# PCI-DSS focused CASIL configuration
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=enforce
export ARQONBUS_CASIL_SCOPE_INCLUDE="payment-*,card-*,transaction-*"
export ARQONBUS_CASIL_BLOCK_ON_PROBABLE_SECRET=true
export ARQONBUS_CASIL_REDACTION_PATHS="credit_card,cvv,pin,account_number"
export ARQONBUS_CASIL_REDACTION_PATTERNS="(?i)credit_card:\s*\d{16},(?i)cvv:\s*\d{3,4}"
export ARQONBUS_CASIL_NEVER_LOG_PAYLOAD_FOR="payment-*"
export ARQONBUS_CASIL_TRANSPORT_REDACTION=true
```

## Testing and Validation

### 1. Automated Testing

#### Pattern Testing Suite
```python
#!/usr/bin/env python3
"""CASIL pattern testing and validation suite."""

import unittest
import json
import time
from unittest.mock import patch, MagicMock

class TestCASILPatterns(unittest.TestCase):
    def setUp(self):
        # Setup test configuration
        self.config = CASILConfig()
        self.config.policies.redaction.patterns = [
            r"(?i)api[_-]?key:\s*\S+",
            r"(?i)password:\s*\S+",
            r"(?i)credit_card:\s*\d{16}"
        ]
    
    def test_legitimate_secret_detection(self):
        """Test detection of actual secrets."""
        test_cases = [
            ("api_key: sk-1234567890abcdef", True),
            ("password: mypassword123", True),
            ("credit_card: 1234567890123456", True),
            ("api_key invalid", False),  # No value after colon
            ("API-KEY: ", False),        # Empty value
        ]
        
        for payload, should_detect in test_cases:
            with self.subTest(payload=payload):
                envelope = Envelope(
                    type="message",
                    room="test",
                    channel="chat",
                    payload=payload
                )
                result = classify(envelope, self.config, {})
                self.assertEqual(
                    bool(result.flags.get("contains_probable_secret")),
                    should_detect,
                    f"Pattern detection failed for: {payload}"
                )
    
    def test_false_positive_prevention(self):
        """Test that legitimate content is not flagged."""
        false_positive_cases = [
            "Hello world",
            "API documentation for developers",
            "Secret recipe for cookies",  # Should not match secret patterns
            "Password requirements: 8 chars",
            "Credit card sized image"
        ]
        
        for payload in false_positive_cases:
            with self.subTest(payload=payload):
                envelope = Envelope(
                    type="message",
                    room="test",
                    channel="chat",
                    payload=payload
                )
                result = classify(envelope, self.config, {})
                self.assertFalse(
                    result.flags.get("contains_probable_secret", False),
                    f"False positive detected for: {payload}"
                )
    
    def test_performance_under_load(self):
        """Test pattern performance under load."""
        large_payload = "x" * 100000  # 100KB payload
        envelope = Envelope(
            type="message",
            room="test",
            channel="chat",
            payload=large_payload
        )
        
        start_time = time.time()
        result = classify(envelope, self.config, {})
        end_time = time.time()
        
        processing_time = (end_time - start_time) * 1000  # Convert to ms
        self.assertLess(processing_time, 100, "Pattern processing too slow")
        self.assertEqual(result.kind, "data")  # Should still classify

def run_pattern_validation():
    """Run comprehensive pattern validation."""
    # Test individual patterns
    patterns = [
        r"(?i)api[_-]?key:\s*\S+",
        r"(?i)password:\s*\S+", 
        r"(?i)credit_card:\s*\d{16}"
    ]
    
    validation_results = []
    
    for pattern in patterns:
        result = validate_pattern_security(pattern)
        validation_results.append({
            'pattern': pattern,
            'validation_passed': not result['issues'],
            'issues': result['issues']
        })
    
    # Generate report
    report = {
        'timestamp': time.time(),
        'total_patterns': len(patterns),
        'valid_patterns': sum(1 for r in validation_results if r['validation_passed']),
        'results': validation_results
    }
    
    print(json.dumps(report, indent=2))
    
    if report['valid_patterns'] != report['total_patterns']:
        print("❌ Pattern validation failed!")
        return False
    else:
        print("✅ All patterns validated successfully!")
        return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        run_pattern_validation()
    else:
        unittest.main()
```

### 2. Load Testing

#### CASIL Load Testing Script
```python
#!/usr/bin/env python3
"""CASIL load testing and performance validation."""

import asyncio
import aiohttp
import time
import statistics
import json
from concurrent.futures import ThreadPoolExecutor

class CASILLoadTester:
    def __init__(self, base_url="http://localhost:9100"):
        self.base_url = base_url
        self.results = []
        
    async def send_test_message(self, session, message_id, payload):
        """Send a single test message."""
        start_time = time.time()
        
        try:
            async with session.post(
                f"{self.base_url}/api/send",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # ms
                
                result = {
                    'message_id': message_id,
                    'response_time_ms': response_time,
                    'status_code': response.status_code,
                    'success': response.status_code == 200,
                    'timestamp': end_time
                }
                
                if response.status_code != 200:
                    result['error'] = await response.text()
                
                return result
                
        except Exception as e:
            end_time = time.time()
            return {
                'message_id': message_id,
                'response_time_ms': (end_time - start_time) * 1000,
                'success': False,
                'error': str(e),
                'timestamp': end_time
            }
    
    async def run_load_test(self, num_messages=1000, concurrent=10, payload_type="normal"):
        """Run load test with specified parameters."""
        
        # Generate test payloads
        payloads = self._generate_test_payloads(num_messages, payload_type)
        
        async with aiohttp.ClientSession() as session:
            # Create semaphore to limit concurrency
            semaphore = asyncio.Semaphore(concurrent)
            
            async def bounded_send(args):
                async with semaphore:
                    return await self.send_test_message(session, *args)
            
            # Execute load test
            tasks = [
                bounded_send((i, payload)) 
                for i, payload in enumerate(payloads)
            ]
            
            print(f"Starting load test: {num_messages} messages, {concurrent} concurrent")
            start_time = time.time()
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            # Analyze results
            self._analyze_results(results, total_duration)
            
            return results
    
    def _generate_test_payloads(self, count, payload_type):
        """Generate test payloads based on type."""
        payloads = []
        
        if payload_type == "normal":
            for i in range(count):
                payloads.append({
                    "type": "message",
                    "room": "test",
                    "channel": "chat",
                    "payload": {
                        "message": f"Test message {i}",
                        "user": f"user{i % 100}",
                        "timestamp": time.time()
                    }
                })
        
        elif payload_type == "secret":
            for i in range(count):
                payloads.append({
                    "type": "message",
                    "room": "secure",
                    "channel": "api",
                    "payload": {
                        "api_key": f"sk-secret-{i}",
                        "password": f"password-{i}",
                        "data": f"message {i}"
                    }
                })
        
        elif payload_type == "large":
            for i in range(count):
                large_data = "x" * (1024 * 50)  # 50KB messages
                payloads.append({
                    "type": "message",
                    "room": "test",
                    "channel": "data",
                    "payload": {
                        "data": large_data,
                        "index": i
                    }
                })
        
        return payloads
    
    def _analyze_results(self, results, total_duration):
        """Analyze load test results."""
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]
        
        if not successful_results:
            print("❌ All requests failed!")
            return
        
        response_times = [r['response_time_ms'] for r in successful_results]
        
        print(f"\n📊 Load Test Results:")
        print(f"  Total duration: {total_duration:.2f}s")
        print(f"  Total messages: {len(results)}")
        print(f"  Successful: {len(successful_results)}")
        print(f"  Failed: {len(failed_results)}")
        print(f"  Success rate: {len(successful_results)/len(results)*100:.1f}%")
        print(f"  Throughput: {len(results)/total_duration:.1f} msg/sec")
        
        print(f"\n⏱️ Response Time Statistics:")
        print(f"  Average: {statistics.mean(response_times):.2f}ms")
        print(f"  Median: {statistics.median(response_times):.2f}ms")
        print(f"  P95: {statistics.quantiles(response_times, n=20)[18]:.2f}ms")
        print(f"  P99: {statistics.quantiles(response_times, n=100)[98]:.2f}ms")
        print(f"  Min: {min(response_times):.2f}ms")
        print(f"  Max: {max(response_times):.2f}ms")
        
        # Performance thresholds
        avg_time = statistics.mean(response_times)
        p99_time = statistics.quantiles(response_times, n=100)[98]
        
        if avg_time > 100:
            print("⚠️  High average response time")
        if p99_time > 500:
            print("⚠️  High P99 response time")
        if len(failed_results) > len(results) * 0.01:
            print("⚠️  High failure rate")
        
        # Save detailed results
        with open(f'casil_load_test_{int(time.time())}.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_duration': total_duration,
                    'total_messages': len(results),
                    'successful': len(successful_results),
                    'failed': len(failed_results),
                    'success_rate': len(successful_results)/len(results),
                    'throughput': len(results)/total_duration
                },
                'response_times': {
                    'average': avg_time,
                    'median': statistics.median(response_times),
                    'p95': statistics.quantiles(response_times, n=20)[18],
                    'p99': statistics.quantiles(response_times, n=100)[98],
                    'min': min(response_times),
                    'max': max(response_times)
                },
                'detailed_results': results
            }, f, indent=2)

async def main():
    tester = CASILLoadTester()
    
    print("CASIL Load Testing Suite")
    print("=" * 50)
    
    # Test scenarios
    test_scenarios = [
        {"name": "Normal Traffic", "num_messages": 1000, "concurrent": 10, "payload_type": "normal"},
        {"name": "Secret-Heavy Traffic", "num_messages": 1000, "concurrent": 10, "payload_type": "secret"},
        {"name": "Large Payload Test", "num_messages": 500, "concurrent": 5, "payload_type": "large"},
        {"name": "High Concurrency", "num_messages": 2000, "concurrent": 50, "payload_type": "normal"},
    ]
    
    for scenario in test_scenarios:
        print(f"\n🧪 Running: {scenario['name']}")
        await tester.run_load_test(**scenario)

if __name__ == "__main__":
    asyncio.run(main())
```

## Conclusion

This best practices guide provides a comprehensive framework for deploying and maintaining CASIL in production environments. Key takeaways:

### Deployment Strategy
- **Phased Rollout**: Start with monitor mode, gradually expand to enforcement
- **Environment-Specific**: Different configurations for dev/staging/prod
- **Scope Optimization**: Target high-value channels for security

### Security Hardening
- **Pattern Validation**: Thoroughly test regex patterns for false positives
- **Access Control**: Restrict configuration access to authorized personnel
- **Secret Management**: Use secure configuration management systems

### Performance Optimization
- **Strategic Scoping**: Inspect only necessary channels
- **Resource Management**: Tune limits based on available resources
- **Caching**: Optimize pattern compilation and reuse

### Incident Response
- **Automated Response**: Scripts for common incident types
- **Monitoring**: Real-time alerting for security events
- **Recovery Procedures**: Documented steps for different scenarios

### Compliance
- **Audit Trails**: Comprehensive logging for compliance reporting
- **Regulatory Focus**: Specific configurations for GDPR, HIPAA, PCI-DSS
- **Regular Validation**: Automated testing and validation procedures

Following these best practices will help ensure CASIL provides robust security protection while maintaining system performance and regulatory compliance.

---

**Next**: Review the [API Reference](api-reference.md) for detailed technical documentation, or return to the [CASIL Manual Index](index.md).