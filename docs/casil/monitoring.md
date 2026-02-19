# CASIL Monitoring & Telemetry

Comprehensive guide to monitoring CASIL performance, security events, and integrating with observability systems.

## Overview

CASIL provides extensive telemetry for security monitoring, performance tracking, and compliance reporting. This guide covers metrics collection, alerting integration, and troubleshooting.

## Telemetry Data Sources

### 1. Structured Logs
CASIL emits structured logs for all security events:

```json
{
  "timestamp": "2025-12-03T00:13:16Z",
  "level": "INFO",
  "logger": "arqonbus.casil.engine",
  "event": "CASIL_INSPECTION",
  "message": "Message inspection completed",
  "data": {
    "room": "secure-payments",
    "channel": "transactions", 
    "decision": "BLOCK",
    "reason_code": "CASIL_POLICY_BLOCKED_SECRET",
    "classification": {
      "kind": "data",
      "risk_level": "high",
      "flags": {"contains_probable_secret": true}
    },
    "processing_time_ms": 2.3,
    "client_id": "client_123"
  }
}
```

### 2. Telemetry Channel Events
CASIL publishes summary events to the telemetry channel:

```json
{
  "type": "telemetry",
  "room": "arqonbus.telemetry", 
  "channel": "casil.metrics",
  "payload": {
    "event_type": "casil_summary",
    "timestamp": "2025-12-03T00:13:16Z",
    "window_start": "2025-12-03T00:08:16Z",
    "window_end": "2025-12-03T00:13:16Z",
    "metrics": {
      "total_inspected": 1247,
      "allowed": 1198,
      "blocked": 23,
      "redacted": 26,
      "by_room": {
        "secure-payments": {"inspected": 456, "blocked": 18, "redacted": 8},
        "pii-userdata": {"inspected": 234, "blocked": 2, "redacted": 15},
        "chat-general": {"inspected": 557, "blocked": 3, "redacted": 3}
      },
      "by_classification": {
        "data": {"count": 1123, "high_risk": 23},
        "control": {"count": 89, "high_risk": 0},
        "telemetry": {"count": 35, "high_risk": 0}
      },
      "top_violations": [
        {"pattern": "credit_card", "count": 12},
        {"pattern": "api_key", "count": 8},
        {"pattern": "password", "count": 3}
      ]
    }
  }
}
```

### 3. Metrics Integration
CASIL integrates with ArqonBus metrics system:

```python
# Example metrics names
"arqonbus.casil.messages.inspected"
"arqonbus.casil.messages.blocked" 
"arqonbus.casil.messages.redacted"
"arqonbus.casil.processing.time"
"arqonbus.casil.errors.total"
```

## Key Performance Indicators (KPIs)

### Security KPIs

#### Detection Rate
```bash
# Messages with security flags detected
grep "contains_probable_secret.*true" /var/log/arqonbus.log | wc -l
```

#### Block Rate
```bash
# Percentage of messages blocked
BLOCKED=$(grep "reason_code.*BLOCKED" /var/log/arqonbus.log | wc -l)
TOTAL=$(grep "CASIL_INSPECTION" /var/log/arqonbus.log | wc -l)
echo "Block rate: $(($BLOCKED * 100 / $TOTAL))%"
```

#### False Positive Rate
Monitor legitimate messages being flagged as secrets:
```bash
# Monitor for patterns that might be false positives
grep -E "password.*\b(123|password|admin)\b" /var/log/arqonbus.log
```

### Performance KPIs

#### Inspection Latency
```python
import time
import re
from collections import defaultdict

def analyze_performance():
    processing_times = []
    pattern = r"processing_time_ms.*?(\d+\.?\d*)"
    
    with open('/var/log/arqonbus.log') as f:
        for line in f:
            match = re.search(pattern, line)
            if match:
                processing_times.append(float(match.group(1)))
    
    if processing_times:
        avg = sum(processing_times) / len(processing_times)
        p95 = sorted(processing_times)[int(len(processing_times) * 0.95)]
        p99 = sorted(processing_times)[int(len(processing_times) * 0.99)]
        
        print(f"Average: {avg:.2f}ms")
        print(f"P95: {p95:.2f}ms") 
        print(f"P99: {p99:.2f}ms")

analyze_performance()
```

#### Throughput Impact
```bash
# Compare throughput with/without CASIL
# Disable CASIL
export ARQONBUS_CASIL_ENABLED=false
ab -n 1000 -c 10 http://localhost:9100/api/send

# Enable CASIL  
export ARQONBUS_CASIL_ENABLED=true
export ARQONBUS_CASIL_MODE=monitor
export ARQONBUS_CASIL_SCOPE_INCLUDE="*"
ab -n 1000 -c 10 http://localhost:9100/api/send
```

## Alerting Configuration

### Prometheus Alerting Rules

Create alerts for suspicious CASIL activity:

```yaml
# /etc/prometheus/rules/casil.yml
groups:
  - name: casil.security
    rules:
      - alert: HighSecretDetectionRate
        expr: rate(arqonbus_casil_messages_blocked[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High rate of secret detection"
          description: "{{ $value }} messages/sec blocked for containing secrets"
      
      - alert: ExcessiveFalsePositives  
        expr: rate(arqonbus_casil_messages_blocked[10m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Potential false positive attack"
          description: "High block rate may indicate overly aggressive patterns"
      
      - alert: CASILPerformanceDegradation
        expr: arqonbus_casil_processing_time_p95 > 10
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "CASIL processing time degraded"
          description: "95th percentile processing time: {{ $value }}ms"
      
      - alert: CASILInternalErrors
        expr: rate(arqonbus_casil_errors_total[5m]) > 0.01
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "CASIL internal errors detected"
          description: "Error rate: {{ $value }} errors/sec"
```

### ELK Stack Integration

#### Logstash Configuration
```ruby
# /etc/logstash/conf.d/casil.conf
filter {
  if [logger] == "arqonbus.casil.engine" {
    json {
      source => "message"
    }
    
    # Extract CASIL fields
    if [data][classification] {
      mutate {
        add_field => {
          "casil_decision" => "%{data][decision]"
          "casil_risk_level" => "%{data][classification][risk_level]"
          "casil_flags" => "%{data][classification][flags]"
        }
      }
    }
    
    # Security scoring
    if [data][reason_code] == "CASIL_POLICY_BLOCKED_SECRET" {
      mutate {
        add_tag => ["security_violation"]
        add_field => {"security_score" => "100"}
      }
    }
  }
}
```

#### Elasticsearch Mapping
```json
{
  "mappings": {
    "casil_logs": {
      "properties": {
        "@timestamp": {"type": "date"},
        "casil_decision": {"type": "keyword"},
        "casil_risk_level": {"type": "keyword"},
        "security_score": {"type": "integer"},
        "processing_time_ms": {"type": "float"},
        "client_id": {"type": "keyword"},
        "room": {"type": "keyword"},
        "channel": {"type": "keyword"}
      }
    }
  }
}
```

#### Kibana Dashboards

**Security Overview Dashboard**:
- Block rate over time
- Top violating patterns
- Risk level distribution
- Room/channel heatmap

**Performance Dashboard**:
- Processing time percentiles
- Throughput comparison
- Error rate trends
- Pattern matching performance

### Grafana Dashboards

```json
{
  "dashboard": {
    "title": "CASIL Security Overview",
    "panels": [
      {
        "title": "Messages Blocked (Last 24h)",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(increase(arqonbus_casil_messages_blocked[24h]))"
          }
        ]
      },
      {
        "title": "Block Rate Trend",
        "type": "graph", 
        "targets": [
          {
            "expr": "rate(arqonbus_casil_messages_blocked[5m])"
          }
        ]
      },
      {
        "title": "Processing Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(arqonbus_casil_processing_time_bucket[5m]))"
          }
        ]
      }
    ]
  }
}
```

## Monitoring Scripts

### Security Event Monitor

```python
#!/usr/bin/env python3
"""Monitor CASIL security events in real-time."""

import re
import time
import json
from collections import deque, defaultdict

class CASILSecurityMonitor:
    def __init__(self, log_file='/var/log/arqonbus.log'):
        self.log_file = log_file
        self.events = deque(maxlen=1000)
        self.pattern_counts = defaultdict(int)
        self.room_violations = defaultdict(int)
        
    def parse_log_line(self, line):
        """Parse CASIL log line and extract security events."""
        # Extract JSON from log line
        json_match = re.search(r'"event": "CASIL_INSPECTION".*?"data": ({.*?})', line)
        if not json_match:
            return None
            
        try:
            data = json.loads(json_match.group(1))
            return data
        except json.JSONDecodeError:
            return None
    
    def analyze_event(self, data):
        """Analyze a CASIL event for security implications."""
        if data.get('decision') == 'BLOCK':
            self.pattern_counts[data.get('reason_code', 'UNKNOWN')] += 1
            
            room = data.get('room', 'unknown')
            self.room_violations[room] += 1
            
        return data
    
    def generate_alerts(self):
        """Generate alerts based on current state."""
        alerts = []
        
        # High violation rate in last 5 minutes
        recent_violations = sum(1 for event in self.events 
                              if event.get('decision') == 'BLOCK' 
                              and time.time() - event.get('timestamp', 0) < 300)
        
        if recent_violations > 10:
            alerts.append({
                'severity': 'WARNING',
                'message': f'High violation rate: {recent_violations} blocks in 5 minutes'
            })
        
        # Single room violations
        for room, count in self.room_violations.items():
            if count > 5:
                alerts.append({
                    'severity': 'CRITICAL',
                    'message': f'Room {room} has {count} violations'
                })
        
        return alerts
    
    def monitor(self):
        """Monitor log file for CASIL events."""
        with open(self.log_file) as f:
            # Seek to end of file
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                
                data = self.parse_log_line(line)
                if data:
                    data['timestamp'] = time.time()
                    event = self.analyze_event(data)
                    self.events.append(event)
                    
                    # Check for alerts
                    alerts = self.generate_alerts()
                    for alert in alerts:
                        print(f"[{alert['severity']}] {alert['message']}")

if __name__ == "__main__":
    monitor = CASILSecurityMonitor()
    monitor.monitor()
```

### Performance Monitor

```python
#!/usr/bin/env python3
"""Monitor CASIL performance metrics."""

import re
import time
import statistics
from collections import deque

class CASILPerformanceMonitor:
    def __init__(self, log_file='/var/log/arqonbus.log'):
        self.log_file = log_file
        self.processing_times = deque(maxlen=10000)
        self.error_times = deque(maxlen=1000)
        
    def extract_processing_time(self, line):
        """Extract processing time from log line."""
        match = re.search(r'processing_time_ms.*?(\d+\.?\d*)', line)
        if match:
            return float(match.group(1))
        return None
    
    def is_error_line(self, line):
        """Check if line contains an error."""
        return any(error_type in line for error_type in [
            'CASIL_INTERNAL_ERROR',
            'Exception',
            'Error',
            'Failed'
        ])
    
    def analyze_performance(self):
        """Analyze current performance metrics."""
        if not self.processing_times:
            return None
            
        recent_times = list(self.processing_times)[-1000:]  # Last 1000 measurements
        
        return {
            'avg_ms': statistics.mean(recent_times),
            'median_ms': statistics.median(recent_times),
            'p95_ms': statistics.quantiles(recent_times, n=20)[18],  # 95th percentile
            'p99_ms': statistics.quantiles(recent_times, n=100)[98],  # 99th percentile
            'max_ms': max(recent_times),
            'error_rate': len(self.error_times) / len(self.processing_times) * 100
        }
    
    def monitor(self):
        """Monitor performance in real-time."""
        with open(self.log_file) as f:
            f.seek(0, 2)
            
            last_report = time.time()
            
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                
                # Extract processing time
                proc_time = self.extract_processing_time(line)
                if proc_time:
                    self.processing_times.append(proc_time)
                
                # Track errors
                if self.is_error_line(line):
                    self.error_times.append(time.time())
                
                # Report every 30 seconds
                if time.time() - last_report > 30:
                    metrics = self.analyze_performance()
                    if metrics:
                        print(f"CASIL Performance Report:")
                        print(f"  Average: {metrics['avg_ms']:.2f}ms")
                        print(f"  P95: {metrics['p95_ms']:.2f}ms")
                        print(f"  P99: {metrics['p99_ms']:.2f}ms")
                        print(f"  Max: {metrics['max_ms']:.2f}ms")
                        print(f"  Error rate: {metrics['error_rate']:.2f}%")
                        
                        # Performance alerts
                        if metrics['p95_ms'] > 10:
                            print(f"  ⚠️  High processing time: P95 = {metrics['p95_ms']:.2f}ms")
                        
                        if metrics['error_rate'] > 1:
                            print(f"  🚨 High error rate: {metrics['error_rate']:.2f}%")
                    
                    last_report = time.time()

if __name__ == "__main__":
    monitor = CASILPerformanceMonitor()
    monitor.monitor()
```

## Compliance Reporting

### GDPR Compliance Report

```python
#!/usr/bin/env python3
"""Generate GDPR compliance report for CASIL."""

import json
import re
from datetime import datetime, timedelta
from collections import defaultdict

def generate_gdpr_report(log_file, start_date, end_date):
    """Generate GDPR-focused CASIL report."""
    
    report = {
        "report_period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "data_protection_summary": {},
        "redaction_statistics": {},
        "access_logs": [],
        "compliance_score": 0
    }
    
    pii_patterns = [
        r"(?i)email.*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        r"(?i)phone.*\d{3}[-.]?\d{3}[-.]?\d{4}",
        r"(?i)ssn.*\d{3}[-.]?\d{2}[-.]?\d{4}",
        r"(?i)address.*\d+.*[a-zA-Z\s]+"
    ]
    
    redacted_counts = defaultdict(int)
    total_inspections = 0
    
    with open(log_file) as f:
        for line in f:
            # Extract timestamp and check date range
            timestamp_match = re.search(r'"timestamp":\s*"([^"]+)"', line)
            if not timestamp_match:
                continue
            
            try:
                event_time = datetime.fromisoformat(timestamp_match.group(1))
                if event_time < start_date or event_time > end_date:
                    continue
            except ValueError:
                continue
            
            total_inspections += 1
            
            # Check for redaction events
            if '"decision": "ALLOW_WITH_REDACTION"' in line:
                redacted_counts['messages_redacted'] += 1
            
            # Extract room/channel for audit
            room_match = re.search(r'"room":\s*"([^"]+)"', line)
            channel_match = re.search(r'"channel":\s*"([^"]+)"', line)
            
            if room_match and channel_match:
                room_channel = f"{room_match.group(1)}:{channel_match.group(1)}"
                
                # Check for PII-related rooms
                if any(pattern in room_channel.lower() for pattern in ['pii', 'user', 'customer', 'personal']):
                    report["access_logs"].append({
                        "timestamp": timestamp_match.group(1),
                        "room_channel": room_channel,
                        "event": "pii_data_processing"
                    })
    
    # Calculate compliance metrics
    report["data_protection_summary"] = {
        "total_messages_inspected": total_inspections,
        "messages_with_potential_pii": len(report["access_logs"]),
        "redaction_rate": (redacted_counts['messages_redacted'] / total_inspections * 100) if total_inspections > 0 else 0
    }
    
    report["redaction_statistics"] = dict(redacted_counts)
    
    # Compliance score (0-100)
    compliance_score = min(100, (
        report["data_protection_summary"]["redaction_rate"] * 0.4 +
        (100 - len(report["access_logs"]) / max(1, total_inspections) * 100) * 0.6
    ))
    report["compliance_score"] = round(compliance_score, 2)
    
    return report

# Generate report
if __name__ == "__main__":
    start = datetime.now() - timedelta(days=30)
    end = datetime.now()
    
    report = generate_gdpr_report('/var/log/arqonbus.log', start, end)
    
    print(json.dumps(report, indent=2))
    
    # Save report
    with open(f'casil_gdpr_report_{end.strftime("%Y%m%d")}.json', 'w') as f:
        json.dump(report, f, indent=2)
```

## Integration with SIEM

### Splunk Integration

```python
# splunk_casil.py
import json
import re
import time

def parse_casil_events(log_lines):
    """Parse CASIL events for Splunk ingestion."""
    events = []
    
    for line in log_lines:
        # Parse JSON log line
        try:
            log_data = json.loads(line)
            
            # Extract CASIL-specific fields
            if log_data.get('event') == 'CASIL_INSPECTION':
                event = {
                    'time': log_data.get('timestamp'),
                    'source': 'arqonbus-casil',
                    'sourcetype': 'arqonbus:casil',
                    'index': 'security',
                    'event': {
                        'decision': log_data.get('data', {}).get('decision'),
                        'room': log_data.get('data', {}).get('room'),
                        'channel': log_data.get('data', {}).get('channel'),
                        'risk_level': log_data.get('data', {}).get('classification', {}).get('risk_level'),
                        'contains_secret': log_data.get('data', {}).get('classification', {}).get('flags', {}).get('contains_probable_secret'),
                        'processing_time': log_data.get('data', {}).get('processing_time_ms')
                    }
                }
                events.append(event)
                
        except json.JSONDecodeError:
            continue
    
    return events

# Example usage
events = parse_casil_events(log_lines)
# Send to Splunk HEC endpoint
```

### QRadar Integration

```python
# qradar_casil.py
import json
import requests

def send_to_qradar(events, qradar_url, api_token):
    """Send CASIL events to IBM QRadar."""
    
    headers = {
        'SEC': api_token,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    batch_size = 100
    for i in range(0, len(events), batch_size):
        batch = events[i:i + batch_size]
        
        payload = {
            'events': batch
        }
        
        response = requests.post(
            f'{qradar_url}/api/event_manager/events',
            headers=headers,
            json=payload,
            verify=False  # Set to True in production with proper certs
        )
        
        if response.status_code != 201:
            print(f"Failed to send batch: {response.status_code}")
```

## Troubleshooting Monitoring

### Common Issues

#### Missing Telemetry Data
```bash
# Check if CASIL telemetry is enabled
grep "CASIL telemetry" /var/log/arqonbus.log

# Verify telemetry channel
export ARQONBUS_CASIL_METADATA_TO_TELEMETRY=true

# Restart service
sudo systemctl restart arqonbus
```

#### High Log Volume
```bash
# Reduce log level for non-security events
export ARQONBUS_LOG_LEVEL=ERROR

# Filter CASIL logs
grep "CASIL_" /var/log/arqonbus.log

# Archive old logs
sudo logrotate -f /etc/logrotate.d/arqonbus
```

#### Performance Impact from Monitoring
```bash
# Disable detailed telemetry in high-load scenarios
export ARQONBUS_CASIL_METADATA_TO_ENVELOPE=false
export ARQONBUS_CASIL_METADATA_TO_LOGS=false

# Use sampling for high-volume channels
export ARQONBUS_CASIL_SCOPE_INCLUDE="secure-*,pii-*,finance-*"
export ARQONBUS_CASIL_SCOPE_EXCLUDE="chat-*,broadcast-*"
```

### Debug Commands

```bash
# Check CASIL status
curl -s http://localhost:9100/status | jq '.casil'

# Monitor CASIL events in real-time
tail -f /var/log/arqonbus.log | grep CASIL

# Check telemetry emission
tail -f /var/log/arqonbus.log | grep "arqonbus.telemetry"

# Test pattern matching
python -c "
from arqonbus.casil.classifier import classify
from arqonbus.config.config import CASILConfig
from arqonbus.protocol.envelope import Envelope

config = CASILConfig()
envelope = Envelope(type='message', room='test', channel='chat', payload={'password': 'secret'})
result = classify(envelope, config, {})
print(f'Classification: {result.kind}, Risk: {result.risk_level}')
"
```

---

**Next**: Learn about [Best Practices](best-practices.md) for production deployment and [API Reference](api-reference.md) for detailed technical documentation.