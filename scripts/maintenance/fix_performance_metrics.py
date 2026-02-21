#!/usr/bin/env python3
"""Fix the performance metrics test to add mock clients and flush batch."""

import re

# Read the file
with open('tests/integration/test_telemetry.py', 'r') as f:
    content = f.read()

# Find the performance metrics test and add the necessary lines
pattern = r'(            telemetry_server\.is_running = True  # For testing: simulate running server)'
replacement = r'\1\n            # Add mock clients to receive broadcasts\n            mock_clients = [AsyncMock()]\n            telemetry_server._telemetry_clients = set(mock_clients)\n            # Flush batch to ensure events are broadcast\n            await telemetry_server._flush_batch()'

content = re.sub(pattern, replacement, content)

# Write the file
with open('tests/integration/test_telemetry.py', 'w') as f:
    f.write(content)

print("Fixed performance metrics test")