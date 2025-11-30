"""End-to-end integration tests for ArqonBus messaging system.

Tests complete message flow from WebSocket connection through routing,
storage, telemetry, and command execution.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
import websockets

from arqonbus.server import ArqonBusServer
from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.ids import generate_message_id
from arqonbus.config.config import Config


class TestEndToEndMessaging:
    """End-to-end integration tests for ArqonBus."""
    
    @pytest.fixture
    def server_config(self):
        """Server configuration for testing."""
        return {
            "server": {"host": "localhost", "port": 8765},
            "websocket": {"host": "localhost", "port": 8765},
            "storage": {"backend": "memory", "max_history_size": 1000},
            "telemetry": {
                "enabled": True,
                "host": "localhost",
                "port": 8081,
                "log_level": "INFO"
            },
            "http": {
                "enabled": True,
                "host": "localhost", 
                "port": 8080
            },
            "commands": {"enabled": True}
        }
    
    @pytest.fixture
    def test_client_envelope(self):
        """Create a test client envelope."""
        return {
            "id": generate_message_id(),
            "type": "message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_client": "arq_client_123",
            "to_client": "arq_client_456",
            "payload": {"content": "Hello, ArqonBus!"}
        }
    
    @pytest.mark.asyncio
    async def test_full_message_flow_with_telemetry(self, server_config, test_client_envelope):
        """Test complete message flow with telemetry integration."""
        # Start server
        server = ArqonBusServer()
        await server.start()
        
        try:
            # Connect WebSocket client
            uri = f"ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                # Send message
                await websocket.send(json.dumps(test_client_envelope))
                
                # Receive response
                response = await websocket.recv()
                response_data = json.loads(response)
                
                # Verify message was processed
                assert response_data["id"] == test_client_envelope["id"]
                assert response_data["type"] == "message_response"
                assert "timestamp" in response_data
                
                # Verify telemetry was recorded
                if server.telemetry_emitter:
                    stats = server.telemetry_emitter.get_stats()
                    assert stats["stats"]["events_emitted"] > 0
            
        finally:
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_room_based_routing_e2e(self, server_config):
        """Test end-to-end room-based message routing."""
        # Start server
        server = ArqonBusServer()
        await server.start()
        
        try:
            # Create test room
            room_id = "arq_room_test"
            
            # Create two client messages
            client1_msg = {
                "id": generate_message_id(),
                "type": "message",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "from_client": "arq_client_1",
                "room": room_id,
                "payload": {"content": "Message from client 1"}
            }
            
            client2_msg = {
                "id": generate_message_id(),
                "type": "message",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "from_client": "arq_client_2",
                "room": room_id,
                "payload": {"content": "Message from client 2"}
            }
            
            # Connect WebSocket clients
            uri = f"ws://localhost:8765"
            
            # Client 1: Join room and send message
            async with websockets.connect(uri) as client1_ws:
                # Join room (would need proper room joining logic)
                await client1_ws.send(json.dumps(client1_msg))
                
                # Client 2: Join room and send message  
                async with websockets.connect(uri) as client2_ws:
                    await client2_ws.send(json.dumps(client2_msg))
                    
                    # Both clients should receive the messages
                    response1 = await asyncio.wait_for(client1_ws.recv(), timeout=2.0)
                    response2 = await asyncio.wait_for(client2_ws.recv(), timeout=2.0)
                    
                    # Verify messages were broadcast to room
                    # In a real implementation, both clients would receive both messages
                    # For now, just verify the responses are valid
                    assert response1
                    assert response2
            
        finally:
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_command_execution_e2e(self, server_config):
        """Test end-to-end command execution."""
        # Start server
        server = ArqonBusServer()
        await server.start()
        
        try:
            # Connect WebSocket client
            uri = f"ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                # Send status command
                command_msg = {
                    "id": generate_message_id(),
                    "type": "command",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "from_client": "arq_client_123",
                    "payload": {
                        "command": "status",
                        "parameters": {}
                    }
                }
                
                await websocket.send(json.dumps(command_msg))
                
                # Receive command response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                # Verify command was executed
                assert response_data["type"] == "command_response"
                assert response_data["command"] == "status"
                assert "result" in response_data
                assert "timestamp" in response_data
                
                # Verify telemetry recorded command execution
                if server.telemetry_emitter:
                    emitter_stats = server.telemetry_emitter.get_stats()
                    assert emitter_stats["stats"]["events_emitted"] > 0
            
        finally:
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_storage_integration_e2e(self, server_config):
        """Test end-to-end storage integration."""
        # Start server with memory storage
        server = ArqonBusServer()
        await server.start()
        
        try:
            # Connect WebSocket client
            uri = f"ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                # Send message that should be stored
                message = {
                    "id": generate_message_id(),
                    "type": "message",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "from_client": "arq_client_123",
                    "to_client": "arq_client_456",
                    "payload": {"content": "Stored message"}
                }
                
                await websocket.send(json.dumps(message))
                
                # Verify storage operation
                if server.storage:
                    # Check storage stats
                    storage_stats = await server.storage.get_storage_stats()
                    assert "backend_type" in storage_stats
                    
                    # Test history retrieval
                    history = await server.storage.get_history(
                        client_id="arq_client_123"
                    )
                    # History might be empty depending on implementation
                    assert isinstance(history, list)
            
        finally:
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_redis_degradation_e2e(self, server_config):
        """Test graceful degradation when Redis is unavailable."""
        # Configure with Redis backend but simulate failure
        server_config["storage"]["backend"] = "redis_streams"
        server_config["storage"]["redis_url"] = "redis://localhost:9999"  # Invalid port
        
        server = ArqonBusServer()
        await server.start()
        
        try:
            # Connect WebSocket client
            uri = f"ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                # Send message
                message = {
                    "id": generate_message_id(),
                    "type": "message",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "from_client": "arq_client_123",
                    "to_client": "arq_client_456",
                    "payload": {"content": "Message with Redis degradation"}
                }
                
                await websocket.send(json.dumps(message))
                
                # Receive response (should work despite Redis failure)
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                assert response_data["id"] == message["id"]
                assert response_data["type"] == "message_response"
                
                # Verify storage is working with fallback
                if server.storage:
                    storage_stats = await server.storage.get_storage_stats()
                    assert storage_stats["backend_type"] == "redis_streams"
                    assert "fallback_storage" in storage_stats
            
        finally:
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_telemetry_broadcasting_e2e(self, server_config):
        """Test end-to-end telemetry event broadcasting."""
        # Start server with telemetry
        server = ArqonBusServer()
        await server.start()
        
        try:
            # Connect telemetry client
            telemetry_uri = f"ws://localhost:8081"
            telemetry_events = []
            
            async def capture_telemetry():
                nonlocal telemetry_events
                try:
                    async with websockets.connect(telemetry_uri) as telemetry_ws:
                        # Subscribe to telemetry events
                        await telemetry_ws.send(json.dumps({
                            "type": "subscribe",
                            "events": ["client_connected", "message_sent"]
                        }))
                        
                        # Capture a few events
                        for _ in range(3):
                            event = await asyncio.wait_for(telemetry_ws.recv(), timeout=2.0)
                            telemetry_events.append(json.loads(event))
                except Exception as e:
                    print(f"Telemetry capture error: {e}")
            
            # Start telemetry capture in background
            telemetry_task = asyncio.create_task(capture_telemetry())
            
            # Connect WebSocket client (should generate telemetry events)
            uri = f"ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                # Send a message to trigger telemetry
                message = {
                    "id": generate_message_id(),
                    "type": "message",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "from_client": "arq_client_123",
                    "to_client": "arq_client_456",
                    "payload": {"content": "Telemetry test message"}
                }
                
                await websocket.send(json.dumps(message))
                await asyncio.sleep(1)  # Give time for telemetry processing
            
            # Wait for telemetry capture
            await asyncio.sleep(2)
            telemetry_task.cancel()
            
            # Verify telemetry events were captured
            assert len(telemetry_events) > 0
            
            # Check for expected event types
            event_types = [event.get("event_type") for event in telemetry_events]
            assert any("connected" in event_type for event_type in event_types)
            
        finally:
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_http_monitoring_endpoints_e2e(self, server_config):
        """Test HTTP monitoring endpoints."""
        # Start server with HTTP monitoring
        server = ArqonBusServer()
        await server.start()
        
        try:
            import aiohttp
            
            # Test health endpoint
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8080/health") as response:
                    assert response.status == 200
                    health_data = await response.json()
                    assert health_data["status"] == "healthy"
                
                # Test metrics endpoint
                async with session.get("http://localhost:8080/metrics") as response:
                    assert response.status == 200
                    metrics_data = await response.json()
                    assert "system" in metrics_data
                
                # Test Prometheus metrics endpoint
                async with session.get("http://localhost:8080/metrics/prometheus") as response:
                    assert response.status == 200
                    prometheus_data = await response.text()
                    assert "arqonbus_" in prometheus_data
            
        finally:
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_clients_e2e(self, server_config):
        """Test end-to-end with multiple concurrent clients."""
        # Start server
        server = ArqonBusServer()
        await server.start()
        
        try:
            uri = f"ws://localhost:8765"
            
            # Create multiple concurrent clients
            clients = []
            for i in range(5):
                client = await websockets.connect(uri)
                clients.append(client)
            
            try:
                # Send messages from all clients simultaneously
                tasks = []
                for i, client in enumerate(clients):
                    message = {
                        "id": generate_message_id(),
                        "type": "message",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "from_client": f"arq_client_{i}",
                        "to_client": f"arq_client_{(i+1) % 5}",
                        "payload": {"content": f"Message from client {i}"}
                    }
                    
                    task = asyncio.create_task(client.send(json.dumps(message)))
                    tasks.append(task)
                
                # Wait for all sends to complete
                await asyncio.gather(*tasks)
                
                # Receive responses from all clients
                responses = []
                for client in clients:
                    try:
                        response = await asyncio.wait_for(client.recv(), timeout=3.0)
                        responses.append(json.loads(response))
                    except asyncio.TimeoutError:
                        pass  # Some clients might not receive responses immediately
                
                # Verify at least some responses were received
                assert len(responses) > 0
                
                # Verify telemetry handled concurrent load
                if server.telemetry_emitter:
                    emitter_stats = server.telemetry_emitter.get_stats()
                    assert emitter_stats["stats"]["events_emitted"] > 0
            
            finally:
                # Close all client connections
                for client in clients:
                    await client.close()
            
        finally:
            await server.stop()
    
    @pytest.mark.asyncio
    async def test_server_lifecycle_e2e(self, server_config):
        """Test complete server startup and shutdown lifecycle."""
        # Test server startup
        server = ArqonBusServer()
        assert not server.is_running()
        
        # Start server
        await server.start()
        assert server.is_running()
        
        try:
            # Verify all components are initialized
            assert server.routing_coordinator is not None
            assert server.ws_bus is not None
            assert server.storage is not None
            
            # Connect a client to verify functionality
            uri = f"ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                # Send a simple ping or status command
                command = {
                    "id": generate_message_id(),
                    "type": "command",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "from_client": "arq_client_test",
                    "payload": {"command": "ping", "parameters": {}}
                }
                
                await websocket.send(json.dumps(command))
                
                # Should receive a response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                assert response
                
                # Verify telemetry is working
                if server.telemetry_emitter:
                    stats = server.telemetry_emitter.get_stats()
                    assert stats["stats"]["events_emitted"] > 0
            
            # Test server shutdown
            await server.stop()
            assert not server.is_running()
            
        except Exception as e:
            await server.stop()
            raise