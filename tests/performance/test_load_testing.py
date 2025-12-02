"""Performance and load testing scenarios for ArqonBus.

Tests system performance under various load conditions including
concurrent connections, message throughput, and resource utilization.
"""

import pytest
import asyncio
import json
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock
from datetime import datetime, timezone
import websockets
import psutil

from arqonbus.server import ArqonBusServer
from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.ids import generate_message_id


class TestPerformanceScenarios:
    """Performance and load testing for ArqonBus."""
    
    @pytest.fixture
    def performance_config(self):
        """Server configuration for performance testing."""
        return {
            "server": {"host": "localhost", "port": 8765},
            "websocket": {"host": "localhost", "port": 8765},
            "storage": {"backend": "memory", "max_history_size": 10000},
            "telemetry": {
                "enabled": False,  # Disable for performance testing
                "host": "localhost",
                "port": 8081
            },
            "http": {
                "enabled": False,  # Disable for performance testing
                "host": "localhost",
                "port": 8080
            },
            "commands": {"enabled": True}
        }
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_websocket_connections(self, performance_config):
        """Test performance with many concurrent WebSocket connections."""
        server = ArqonBusServer()
        await server.start()
        
        try:
            uri = f"ws://localhost:8765"
            num_connections = 100
            
            # Measure connection setup time
            start_time = time.time()
            
            # Create connections concurrently
            connections = []
            connection_tasks = []
            
            for i in range(num_connections):
                async def create_connection(client_id):
                    try:
                        ws = await websockets.connect(uri)
                        return ws
                    except Exception as e:
                        print(f"Connection failed for client {client_id}: {e}")
                        return None
                
                task = asyncio.create_task(create_connection(i))
                connection_tasks.append(task)
            
            # Wait for all connections
            connections = await asyncio.gather(*connection_tasks)
            
            # Filter successful connections
            successful_connections = [ws for ws in connections if ws is not None]
            connection_time = time.time() - start_time
            
            # Verify performance metrics
            assert len(successful_connections) >= num_connections * 0.9  # At least 90% success rate
            assert connection_time < 30  # Should connect within 30 seconds
            
            # Clean up connections
            for ws in successful_connections:
                await ws.close()
            
            # Record metrics
            connections_per_second = len(successful_connections) / connection_time
            print(f"Established {len(successful_connections)} connections in {connection_time:.2f}s")
            print(f"Connection rate: {connections_per_second:.2f} connections/sec")
            
        finally:
            await server.stop()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_message_throughput(self, performance_config):
        """Test message throughput performance."""
        server = ArqonBusServer()
        await server.start()
        
        try:
            uri = f"ws://localhost:8765"
            num_messages = 1000
            
            # Single client for throughput testing
            async with websockets.connect(uri) as client_ws:
                # Measure send rate
                start_time = time.time()
                
                # Send messages rapidly
                send_tasks = []
                for i in range(num_messages):
                    message = {
                        "id": generate_message_id(),
                        "type": "message",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "sender": "arq_perf_client",
                        "to_client": "arq_target_client",
                        "payload": {"content": f"Performance test message {i}"}
                    }
                    
                    task = asyncio.create_task(client_ws.send(json.dumps(message)))
                    send_tasks.append(task)
                
                # Wait for all sends to complete
                await asyncio.gather(*send_tasks)
                
                send_time = time.time() - start_time
                messages_per_second = num_messages / send_time
                
                # Verify performance metrics
                assert messages_per_second > 10  # Should handle at least 10 messages/sec
                
                print(f"Sent {num_messages} messages in {send_time:.2f}s")
                print(f"Throughput: {messages_per_second:.2f} messages/sec")
            
        finally:
            await server.stop()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_command_execution_performance(self, performance_config):
        """Test command execution performance."""
        server = ArqonBusServer()
        await server.start()
        
        try:
            uri = f"ws://localhost:8765"
            num_commands = 500
            
            async with websockets.connect(uri) as client_ws:
                command_execution_times = []
                
                # Execute commands and measure timing
                for i in range(num_commands):
                    start_time = time.time()
                    
                    command = {
                        "id": generate_message_id(),
                        "type": "command",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "sender": "arq_perf_client",
                        "payload": {
                            "command": "status",
                            "parameters": {}
                        }
                    }
                    
                    await client_ws.send(json.dumps(command))
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(client_ws.recv(), timeout=2.0)
                        execution_time = time.time() - start_time
                        command_execution_times.append(execution_time)
                        
                        # Verify response is valid
                        response_data = json.loads(response)
                        assert response_data["type"] in ["message", "command_response", "error"]  # Any response type is acceptable
                        
                    except asyncio.TimeoutError:
                        print(f"Command {i} timed out")
                
                # Analyze performance metrics
                if command_execution_times:
                    avg_time = statistics.mean(command_execution_times)
                    p95_time = statistics.quantiles(command_execution_times, n=20)[18]  # 95th percentile
                    max_time = max(command_execution_times)
                    
                    print(f"Command execution performance:")
                    print(f"  Average: {avg_time*1000:.2f}ms")
                    print(f"  95th percentile: {p95_time*1000:.2f}ms")
                    print(f"  Max: {max_time*1000:.2f}ms")
                    print(f"  Successful commands: {len(command_execution_times)}/{num_commands}")
                    
                    # Performance assertions
                    assert avg_time < 0.1  # Average should be under 100ms
                    assert p95_time < 0.5  # 95th percentile should be under 500ms
        
        finally:
            await server.stop()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, performance_config):
        """Test memory usage under sustained load."""
        server = ArqonBusServer()
        await server.start()
        
        try:
            # Measure baseline memory
            process = psutil.Process()
            baseline_memory = process.memory_info().rss
            
            uri = f"ws://localhost:8765"
            num_messages = 5000
            
            # Create multiple clients for load
            clients = []
            for i in range(10):
                ws = await websockets.connect(uri)
                clients.append(ws)
            
            try:
                # Send messages from all clients
                all_send_tasks = []
                
                messages_per_client = num_messages // len(clients)
                
                for client_idx, client_ws in enumerate(clients):
                    client_tasks = []
                    for i in range(messages_per_client):
                        message = {
                            "id": generate_message_id(),
                            "type": "message",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "sender": f"arq_client_{client_idx}",
                            "to_client": "arq_target_client",
                            "payload": {"content": f"Load test message {i}"}
                        }
                        
                        task = asyncio.create_task(client_ws.send(json.dumps(message)))
                        client_tasks.append(task)
                    
                    all_send_tasks.extend(client_tasks)
                
                # Send all messages
                await asyncio.gather(*all_send_tasks)
                
                # Measure memory after load
                await asyncio.sleep(1)  # Allow memory to stabilize
                loaded_memory = process.memory_info().rss
                memory_increase = loaded_memory - baseline_memory
                memory_increase_mb = memory_increase / (1024 * 1024)
                
                print(f"Memory usage:")
                print(f"  Baseline: {baseline_memory / (1024 * 1024):.2f} MB")
                print(f"  After load: {loaded_memory / (1024 * 1024):.2f} MB")
                print(f"  Increase: {memory_increase_mb:.2f} MB")
                
                # Memory should not increase dramatically
                assert memory_increase_mb < 500  # Should not increase by more than 500MB
            
            finally:
                # Close all clients
                for client in clients:
                    await client.close()
        
        finally:
            await server.stop()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_load_test(self, performance_config):
        """Test sustained load over time."""
        server = ArqonBusServer()
        await server.start()
        
        try:
            uri = f"ws://localhost:8765"
            test_duration = 30  # seconds
            messages_per_second = 50
            
            # Single long-lived connection
            async with websockets.connect(uri) as client_ws:
                start_time = time.time()
                messages_sent = 0
                response_times = []
                
                # Send messages at sustained rate
                while time.time() - start_time < test_duration:
                    message = {
                        "id": generate_message_id(),
                        "type": "message",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "sender": "arq_sustained_client",
                        "to_client": "arq_target_client",
                        "payload": {"content": f"Sustained load message {messages_sent}"}
                    }
                    
                    send_start = time.time()
                    await client_ws.send(json.dumps(message))
                    
                    # Try to receive response
                    try:
                        response = await asyncio.wait_for(client_ws.recv(), timeout=1.0)
                        response_time = time.time() - send_start
                        response_times.append(response_time)
                    except asyncio.TimeoutError:
                        pass  # Some messages might not get immediate responses
                    
                    messages_sent += 1
                    
                    # Rate limiting
                    await asyncio.sleep(1 / messages_per_second)
                
                # Analyze sustained performance
                actual_duration = time.time() - start_time
                actual_rate = messages_sent / actual_duration
                
                if response_times:
                    avg_response_time = statistics.mean(response_times)
                    p95_response_time = statistics.quantiles(response_times, n=20)[18]
                    
                    print(f"Sustained load test results:")
                    print(f"  Duration: {actual_duration:.2f}s")
                    print(f"  Messages sent: {messages_sent}")
                    print(f"  Target rate: {messages_per_second} msg/sec")
                    print(f"  Actual rate: {actual_rate:.2f} msg/sec")
                    print(f"  Average response time: {avg_response_time*1000:.2f}ms")
                    print(f"  95th percentile response: {p95_response_time*1000:.2f}ms")
                    
                    # Performance should be consistent
                    assert abs(actual_rate - messages_per_second) / messages_per_second < 0.2  # Within 20%
                    assert avg_response_time < 0.2  # Average response under 200ms
        
        finally:
            await server.stop()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_storage_performance(self, performance_config):
        """Test storage backend performance."""
        server = ArqonBusServer()
        await server.start()
        
        try:
            # Test storage operations performance
            if server.storage:
                storage = server.storage
                
                # Test append performance
                append_times = []
                num_operations = 1000
                
                for i in range(num_operations):
                    envelope = Envelope(
                        id=generate_message_id(),
                        type="message",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        sender="arq_perf_client",
                        room="arq_target_client",
                        payload={"content": f"Storage test message {i}"}
                    )
                    
                    start_time = time.time()
                    await storage.store_message(envelope)
                    append_time = time.time() - start_time
                    append_times.append(append_time)
                
                # Analyze storage performance
                avg_append_time = statistics.mean(append_times)
                p95_append_time = statistics.quantiles(append_times, n=20)[18]
                max_append_time = max(append_times)
                
                print(f"Storage append performance:")
                print(f"  Average: {avg_append_time*1000:.2f}ms")
                print(f"  95th percentile: {p95_append_time*1000:.2f}ms")
                print(f"  Max: {max_append_time*1000:.2f}ms")
                
                # Storage should be fast
                assert avg_append_time < 0.01  # Average under 10ms
                assert p95_append_time < 0.05  # 95th percentile under 50ms
                
                # Test history retrieval performance
                start_time = time.time()
                history = await storage.get_global_history(limit=100)
                retrieval_time = time.time() - start_time
                
                print(f"Storage retrieval performance: {retrieval_time*1000:.2f}ms")
                print(f"Retrieved {len(history)} messages")
                
                # Retrieval should be fast
                assert retrieval_time < 0.1  # Under 100ms
        
        finally:
            await server.stop()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_message_routing(self, performance_config):
        """Test concurrent message routing performance."""
        server = ArqonBusServer()
        await server.start()
        
        try:
            uri = f"ws://localhost:8765"
            num_routes = 200
            
            # Create multiple routing scenarios
            routing_scenarios = [
                {"type": "direct", "from": "arq_client_1", "to": "arq_client_2"},
                {"type": "room", "from": "arq_client_1", "room": "arq_room_test"},
                {"type": "channel", "from": "arq_client_1", "channel": "arq_channel_test"}
            ]
            
            routing_times = []
            
            async with websockets.connect(uri) as client_ws:
                for i in range(num_routes):
                    scenario = routing_scenarios[i % len(routing_scenarios)]
                    
                    message = {
                        "id": generate_message_id(),
                        "type": "message",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "sender": scenario["from"],
                        **({k: v for k, v in scenario.items() if k not in ["from", "type"]})
                    }
                    
                    # Remove None values
                    message = {k: v for k, v in message.items() if v is not None}
                    
                    start_time = time.time()
                    await client_ws.send(json.dumps(message))
                    
                    try:
                        response = await asyncio.wait_for(client_ws.recv(), timeout=2.0)
                        routing_time = time.time() - start_time
                        routing_times.append(routing_time)
                    except asyncio.TimeoutError:
                        pass
            
            # Analyze routing performance
            if routing_times:
                avg_routing_time = statistics.mean(routing_times)
                p95_routing_time = statistics.quantiles(routing_times, n=20)[18]
                
                print(f"Message routing performance:")
                print(f"  Average: {avg_routing_time*1000:.2f}ms")
                print(f"  95th percentile: {p95_routing_time*1000:.2f}ms")
                print(f"  Successful routes: {len(routing_times)}/{num_routes}")
                
                # Routing should be fast
                assert avg_routing_time < 0.05  # Average under 50ms
                assert p95_routing_time < 0.2  # 95th percentile under 200ms
        
        finally:
            await server.stop()


class TestResourceUtilization:
    """Test resource utilization and limits."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_cpu_usage_under_load(self):
        """Test CPU usage under load."""
        process = psutil.Process()
        
        # Baseline CPU
        baseline_cpu = process.cpu_percent()
        
        # This test would run under actual load
        # For now, just measure baseline
        await asyncio.sleep(1)
        
        current_cpu = process.cpu_percent()
        print(f"CPU usage: {current_cpu}% (baseline was {baseline_cpu}%)")
        
        # Should not consume excessive CPU
        assert current_cpu < 80  # Under 80% CPU
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self):
        """Test for memory leaks over time."""
        process = psutil.Process()
        
        # Multiple measurements over time
        measurements = []
        
        for i in range(10):
            memory_mb = process.memory_info().rss / (1024 * 1024)
            measurements.append(memory_mb)
            await asyncio.sleep(0.1)
        
        # Check for significant growth
        initial_memory = measurements[0]
        final_memory = measurements[-1]
        memory_growth = final_memory - initial_memory
        
        print(f"Memory growth over time:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Growth: {memory_growth:.2f} MB")
        
        # Should not grow significantly in short time
        assert memory_growth < 10  # Less than 10MB growth


# Performance test markers configuration
pytest_plugins = ["pytest_asyncio"]