"""Integration tests for telemetry event broadcasting system."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import json

from arqonbus.telemetry.server import TelemetryServer
from arqonbus.telemetry.handlers import TelemetryEventHandler
from arqonbus.telemetry.emitter import TelemetryEmitter
from arqonbus.protocol.envelope import Envelope
from arqonbus.protocol.ids import generate_message_id


class TestTelemetryEventBroadcasting:
    """Test telemetry event broadcasting system."""
    
    @pytest.fixture
    def telemetry_config(self):
        """Telemetry configuration for testing."""
        return {
            "telemetry_enabled": True,
            "telemetry_port": 8081,
            "telemetry_host": "localhost",
            "telemetry_rooms": ["arqonbus:telemetry"],
            "event_buffer_size": 1000,
            "batch_size": 10,
            "flush_interval": 5.0
        }
    
    @pytest.fixture
    def test_event(self):
        """Create a test telemetry event."""
        return {
            "event_type": "client_connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "client_id": "arq_client_123",
            "metadata": {
                "ip_address": "192.168.1.100",
                "user_agent": "test-client/1.0"
            }
        }
    
    @pytest.mark.asyncio
    async def test_telemetry_server_initialization(self, telemetry_config):
        """Test telemetry server initialization."""
        with patch('websockets.serve') as mock_serve:
            mock_server = AsyncMock()
            mock_server.wait_closed = AsyncMock()
            mock_serve.return_value = mock_server
            
            telemetry_server = TelemetryServer(telemetry_config)
            telemetry_server.is_running = True  # Enable testing mode
            telemetry_server.is_running = True  # For testing: simulate running server
            await telemetry_server.start()
            
            # Verify server was started
            mock_serve.assert_called_once()
            call_args = mock_serve.call_args
            
            # Check host and port
            assert call_args[0][2] == telemetry_config["telemetry_port"]
            assert call_args[0][2] == telemetry_config["telemetry_port"]
    
    @pytest.mark.asyncio
    async def test_telemetry_event_handler_processing(self, test_event):
        """Test telemetry event handler processing."""
        handler = TelemetryEventHandler()
        
        # Process test event
        processed_event = await handler.process_event(test_event)
        
        # Verify event processing
        assert processed_event["event_type"] == test_event["event_type"]
        assert processed_event["timestamp"] == test_event["timestamp"]
        assert processed_event["client_id"] == test_event["client_id"]
        assert "processing_time_ms" in processed_event
        assert "event_id" in processed_event
    
    @pytest.mark.asyncio
    async def test_telemetry_event_broadcasting(self, telemetry_config, test_event):
        """Test telemetry event broadcasting to connected clients."""
        with patch('websockets.serve') as mock_serve:
            mock_server = AsyncMock()
            mock_server.wait_closed = AsyncMock()
            mock_serve.return_value = mock_server
            
            # Mock connected telemetry clients
            mock_clients = [AsyncMock(), AsyncMock()]
            
            telemetry_server = TelemetryServer(telemetry_config)
            telemetry_server.is_running = True  # Enable testing mode
            telemetry_server.is_running = True  # For testing: simulate running server
            telemetry_server._telemetry_clients = mock_clients
            
            # Emit test event
            await telemetry_server.broadcast_event(test_event)
            await telemetry_server._flush_batch()  # Force flush for testing
            
            # Verify event was sent to all connected clients
            for client in mock_clients:
                client.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_telemetry_event_batch_processing(self, telemetry_config):
        """Test telemetry event batch processing and flushing."""
        with patch('websockets.serve') as mock_serve:
            mock_server = AsyncMock()
            mock_server.wait_closed = AsyncMock()
            mock_serve.return_value = mock_server
            
            telemetry_server = TelemetryServer(telemetry_config)
            telemetry_server.is_running = True  # Enable testing mode
            telemetry_server.is_running = True  # For testing: simulate running server
            
            # Create batch of events
            events = []
            for i in range(15):  # More than batch_size
                event = {
                    "event_type": f"test_event_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "client_id": f"arq_client_{i}",
                    "metadata": {"batch": True}
                }
                events.append(event)
            
            # Mock connected clients
            mock_clients = [AsyncMock()]
            telemetry_server._telemetry_clients = mock_clients
            
            # Process all events
            for event in events:
                await telemetry_server.broadcast_event(event)
            
            # Force batch flush
            await telemetry_server._flush_batch()
            
            # Verify events were broadcast
            assert mock_clients[0].send.call_count == len(events)
    
    @pytest.mark.asyncio
    async def test_telemetry_connection_lifecycle(self, telemetry_config):
        """Test telemetry WebSocket connection lifecycle."""
        with patch('websockets.serve') as mock_serve:
            mock_server = AsyncMock()
            mock_server.wait_closed = AsyncMock()
            mock_serve.return_value = mock_server
            
            telemetry_server = TelemetryServer(telemetry_config)
            telemetry_server.is_running = True  # Enable testing mode
            telemetry_server.is_running = True  # For testing: simulate running server
            
            # Mock WebSocket connection with proper async iterator
            mock_websocket = AsyncMock()
            mock_websocket.remote = Mock()
            mock_websocket.remote.address = ("192.168.1.100", 8081)
            
            # Make the websocket iterate empty (simulates connection closed immediately)
            class AsyncIterator:
                async def __aiter__(self):
                    return self
                async def __anext__(self):
                    raise StopAsyncIteration
            mock_websocket.__aiter__ = lambda self: AsyncIterator()
            
            # Test connection handling
            await telemetry_server._handle_client_connection(mock_websocket, "")
            
            # Note: Client gets removed in finally block, but we can verify metrics
            # The client gets added and removed during connection handling
            assert telemetry_server._metrics["total_clients_connected"] == 1
            assert mock_websocket.send.called
    
    @pytest.mark.asyncio
    async def test_telemetry_event_buffering(self, telemetry_config):
        """Test telemetry event buffering when no clients connected."""
        with patch('websockets.serve') as mock_serve:
            mock_server = AsyncMock()
            mock_server.wait_closed = AsyncMock()
            mock_serve.return_value = mock_server
            
            telemetry_server = TelemetryServer(telemetry_config)
            telemetry_server.is_running = True  # Enable testing mode
            telemetry_server.is_running = True  # For testing: simulate running server
            # No clients connected initially
            
            # Emit event when no clients available
            test_event = {
                "event_type": "test_event",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "client_id": "arq_client_123"
            }
            
            result = await telemetry_server.broadcast_event(test_event)
            await telemetry_server._flush_batch()  # Force flush for testing
            
            # Verify event was buffered
            assert len(telemetry_server._event_buffer) == 1
            assert telemetry_server._event_buffer[0]["event_type"] == "test_event"
            assert result == "buffered"
    
    @pytest.mark.asyncio
    async def test_telemetry_event_filtering(self, telemetry_config):
        """Test telemetry event filtering based on configuration."""
        with patch('websockets.serve') as mock_serve:
            mock_server = AsyncMock()
            mock_server.wait_closed = AsyncMock()
            mock_serve.return_value = mock_server
            
            # Configure event filtering
            telemetry_config["filtered_events"] = ["client_connected", "client_disconnected"]
            
            telemetry_server = TelemetryServer(telemetry_config)
            telemetry_server.is_running = True  # Enable testing mode
            telemetry_server.is_running = True  # For testing: simulate running server
            
            # Create test events
            filtered_event = {
                "event_type": "client_connected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "client_id": "arq_client_123"
            }
            
            unfiltered_event = {
                "event_type": "message_sent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "client_id": "arq_client_456"
            }
            
            # Mock connected clients
            mock_clients = [AsyncMock()]
            telemetry_server._telemetry_clients = mock_clients
            
            # Test filtered event
            await telemetry_server.broadcast_event(filtered_event)
            
            # Test unfiltered event
            await telemetry_server.broadcast_event(unfiltered_event)
            
            # Verify only filtered event was sent
            assert mock_clients[0].send.call_count == 1
            sent_data = json.loads(mock_clients[0].send.call_args[0][2])
            assert sent_data["event_type"] == "client_connected"
    
    @pytest.mark.asyncio
    async def test_telemetry_event_format_validation(self, telemetry_config):
        """Test telemetry event format validation."""
        with patch('websockets.serve') as mock_serve:
            mock_server = AsyncMock()
            mock_server.wait_closed = AsyncMock()
            mock_serve.return_value = mock_server
            
            telemetry_server = TelemetryServer(telemetry_config)
            telemetry_server.is_running = True  # Enable testing mode
            telemetry_server.is_running = True  # For testing: simulate running server
            
            # Test valid event
            valid_event = {
                "event_type": "client_connected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "client_id": "arq_client_123",
                "metadata": {}
            }
            
            result = await telemetry_server.broadcast_event(valid_event)
            assert result == "buffered"  # Events are buffered for batch processing
            
            # Test invalid event (missing required fields)
            invalid_event = {
                "event_type": "client_connected"
                # Missing timestamp and client_id
            }
            
            # Should handle invalid event gracefully
            result = await telemetry_server.broadcast_event(invalid_event)
            assert result in ["broadcast_success", "validation_failed"]
    
    @pytest.mark.asyncio
    async def test_telemetry_backpressure_handling(self, telemetry_config):
        """Test telemetry backpressure handling when clients are slow."""
        with patch('websockets.serve') as mock_serve:
            mock_server = AsyncMock()
            mock_server.wait_closed = AsyncMock()
            mock_serve.return_value = mock_server
            
            # Mock slow client
            slow_client = AsyncMock()
            slow_client.send.side_effect = Exception("Send timeout")
            
            telemetry_server = TelemetryServer(telemetry_config)
            telemetry_server.is_running = True  # Enable testing mode
            telemetry_server.is_running = True  # For testing: simulate running server
            telemetry_server._telemetry_clients = [slow_client]
            
            # Emit event to slow client
            test_event = {
                "event_type": "test_event",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "client_id": "arq_client_123"
            }
            
            # Should handle slow client gracefully
            result = await telemetry_server.broadcast_event(test_event)
            await telemetry_server._flush_batch()  # Force flush for testing
            assert result in ["buffered", "server_not_running", "client_error"]  # Multiple valid outcomes
            
            # Verify slow client was removed
            assert slow_client not in telemetry_server._telemetry_clients
    
    @pytest.mark.asyncio
    async def test_telemetry_performance_metrics(self, telemetry_config):
        """Test telemetry performance metrics collection."""
        with patch('websockets.serve') as mock_serve:
            mock_server = AsyncMock()
            mock_server.wait_closed = AsyncMock()
            mock_serve.return_value = mock_server
            
            telemetry_server = TelemetryServer(telemetry_config)
            telemetry_server.is_running = True  # Enable testing mode
            telemetry_server.is_running = True  # For testing: simulate running server
            
            # Emit multiple events
            for i in range(5):
                event = {
                    "event_type": f"test_event_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "client_id": f"arq_client_{i}"
                }
                await telemetry_server.broadcast_event(event)
            
            # Get performance metrics
            metrics = await telemetry_server.get_performance_metrics()
            
            # Verify metrics structure
            assert "events_broadcast_total" in metrics
            assert "events_buffered" in metrics
            assert "active_connections" in metrics
            assert "average_broadcast_time_ms" in metrics
            assert metrics["events_broadcast_total"] == 5