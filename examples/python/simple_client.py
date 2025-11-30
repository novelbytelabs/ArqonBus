"""
ArqonBus Python SDK - Simple Client Example

This example demonstrates how to use the ArqonBus Python SDK
to connect to an ArqonBus message bus and send/receive messages.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("websockets library not available. Install with: pip install websockets")


class ArqonBusError(Exception):
    """Base exception for ArqonBus client errors."""
    pass


class ArqonBusConnectionError(ArqonBusError):
    """Raised when connection to ArqonBus fails."""
    pass


class ArqonBusMessageError(ArqonBusError):
    """Raised when message validation or delivery fails."""
    pass


class ArqonBusClient:
    """
    ArqonBus Python Client
    
    A simple Python client for connecting to ArqonBus message bus
    and sending/receiving messages.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765, client_id: Optional[str] = None):
        """
        Initialize ArqonBus client.
        
        Args:
            host: ArqonBus server host
            port: ArqonBus server port
            client_id: Unique client identifier (auto-generated if None)
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ArqonBusError("websockets library is required. Install with: pip install websockets")
        
        self.host = host
        self.port = port
        self.client_id = client_id or self._generate_client_id()
        self.websocket = None
        self.connected = False
        self.message_handlers = []
        self.command_handlers = []
        self.error_handlers = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.url = f"ws://{host}:{port}"
    
    def _generate_client_id(self) -> str:
        """Generate a unique client ID."""
        import uuid
        return f"arq_client_{uuid.uuid4().hex[:12]}"
    
    async def connect(self) -> bool:
        """
        Connect to ArqonBus server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to ArqonBus at {self.url}")
            self.websocket = await websockets.connect(self.url)
            self.connected = True
            self.logger.info(f"Connected to ArqonBus as {self.client_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to ArqonBus: {e}")
            raise ArqonBusConnectionError(f"Connection failed: {e}")
    
    async def disconnect(self):
        """Disconnect from ArqonBus server."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            self.logger.info("Disconnected from ArqonBus")
    
    async def send_message(self, to_client: Optional[str] = None, 
                          room: Optional[str] = None, 
                          channel: Optional[str] = None,
                          content: Dict[str, Any] = None) -> str:
        """
        Send a message through ArqonBus.
        
        Args:
            to_client: Target client ID (for direct messages)
            room: Target room ID (for room messages)
            channel: Target channel ID (for channel messages)
            content: Message content dictionary
            
        Returns:
            Message ID
            
        Raises:
            ArqonBusMessageError: If message validation fails or send fails
        """
        if not self.connected:
            raise ArqonBusError("Not connected to ArqonBus")
        
        # Validate exactly one target is specified
        targets = sum([bool(to_client), bool(room), bool(channel)])
        if targets != 1:
            raise ArqonBusMessageError("Must specify exactly one target: to_client, room, or channel")
        
        # Create message
        message = {
            "id": self._generate_message_id(),
            "type": "message",
            "timestamp": datetime.utcnow().isoformat(),
            "from_client": self.client_id,
            "payload": content or {}
        }
        
        # Add target
        if to_client:
            message["to_client"] = to_client
        elif room:
            message["room"] = room
        elif channel:
            message["channel"] = channel
        
        try:
            # Send message
            await self.websocket.send(json.dumps(message))
            self.logger.info(f"Sent message {message['id']} to {to_client or room or channel}")
            return message["id"]
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise ArqonBusMessageError(f"Message send failed: {e}")
    
    async def send_command(self, command: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a command to ArqonBus.
        
        Args:
            command: Command name
            parameters: Command parameters dictionary
            
        Returns:
            Command result dictionary
            
        Raises:
            ArqonBusMessageError: If command fails
        """
        if not self.connected:
            raise ArqonBusError("Not connected to ArqonBus")
        
        command_msg = {
            "id": self._generate_message_id(),
            "type": "command",
            "timestamp": datetime.utcnow().isoformat(),
            "from_client": self.client_id,
            "payload": {
                "command": command,
                "parameters": parameters or {}
            }
        }
        
        try:
            # Send command
            await self.websocket.send(json.dumps(command_msg))
            self.logger.info(f"Sent command {command}")
            
            # Wait for response
            response = await self._wait_for_response(command_msg["id"])
            return response.get("result", {})
        except Exception as e:
            self.logger.error(f"Command {command} failed: {e}")
            raise ArqonBusMessageError(f"Command failed: {e}")
    
    async def _generate_message_id(self) -> str:
        """Generate a unique message ID."""
        import uuid
        return f"arq_msg_{uuid.uuid4().hex[:12]}"
    
    async def _wait_for_response(self, message_id: str, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Wait for response to a specific message.
        
        Args:
            message_id: ID of message to wait for response to
            timeout: Maximum time to wait for response
            
        Returns:
            Response message dictionary
        """
        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            response_data = json.loads(response)
            
            # Check if this is the response we're waiting for
            if response_data.get("id") == f"{message_id}_response":
                return response_data
            
            # If not our response, handle it as a general message
            await self._handle_message(response_data)
            
            # Try again (recursive call with remaining timeout)
            remaining_timeout = timeout - 0.1
            if remaining_timeout > 0:
                return await self._wait_for_response(message_id, remaining_timeout)
            else:
                raise ArqonBusMessageError("Timeout waiting for response")
                
        except asyncio.TimeoutError:
            raise ArqonBusMessageError(f"Timeout waiting for response to {message_id}")
    
    async def listen(self):
        """Start listening for messages from ArqonBus."""
        if not self.connected:
            raise ArqonBusError("Not connected to ArqonBus")
        
        self.logger.info("Started listening for messages")
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    self.logger.warning(f"Received invalid JSON: {message}")
                except Exception as e:
                    self.logger.error(f"Error handling message: {e}")
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("Connection closed")
            self.connected = False
        except Exception as e:
            self.logger.error(f"Error in message listener: {e}")
            raise
    
    async def _handle_message(self, message: Dict[str, Any]):
        """
        Handle incoming message.
        
        Args:
            message: Parsed message dictionary
        """
        message_type = message.get("type")
        
        if message_type == "message_response":
            await self._handle_message_response(message)
        elif message_type == "command_response":
            await self._handle_command_response(message)
        elif message_type == "error":
            await self._handle_error(message)
        elif message_type == "message":
            await self._handle_incoming_message(message)
        else:
            self.logger.warning(f"Unknown message type: {message_type}")
    
    async def _handle_message_response(self, message: Dict[str, Any]):
        """Handle message delivery response."""
        message_id = message.get("id", "")
        self.logger.info(f"Message delivery confirmed: {message_id}")
    
    async def _handle_command_response(self, message: Dict[str, Any]):
        """Handle command response."""
        command = message.get("command", "")
        result = message.get("result", {})
        self.logger.info(f"Command response: {command} -> {result}")
    
    async def _handle_error(self, message: Dict[str, Any]):
        """Handle error message."""
        error = message.get("error", {})
        error_code = error.get("code", "UNKNOWN_ERROR")
        error_message = error.get("message", "Unknown error")
        self.logger.error(f"ArqonBus error [{error_code}]: {error_message}")
    
    async def _handle_incoming_message(self, message: Dict[str, Any]):
        """Handle incoming message from another client."""
        from_client = message.get("from_client", "unknown")
        payload = message.get("payload", {})
        self.logger.info(f"Received message from {from_client}: {payload}")
    
    async def ping(self) -> bool:
        """
        Send ping command to test connectivity.
        
        Returns:
            True if ping successful
        """
        try:
            result = await self.send_command("ping")
            return result.get("pong", False)
        except Exception:
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get server status information.
        
        Returns:
            Server status dictionary
        """
        result = await self.send_command("status")
        return result
    
    async def list_channels(self) -> list:
        """
        List all available channels.
        
        Returns:
            List of channel dictionaries
        """
        result = await self.send_command("list_channels")
        return result.get("channels", [])
    
    async def create_channel(self, channel_id: str, description: str = "") -> bool:
        """
        Create a new channel.
        
        Args:
            channel_id: ID for the new channel
            description: Channel description
            
        Returns:
            True if creation successful
        """
        result = await self.send_command("create_channel", {
            "channel_id": channel_id,
            "description": description
        })
        return result.get("success", False)
    
    async def join_channel(self, channel_id: str) -> bool:
        """
        Join a channel.
        
        Args:
            channel_id: ID of channel to join
            
        Returns:
            True if join successful
        """
        result = await self.send_command("join_channel", {
            "channel_id": channel_id
        })
        return result.get("success", False)
    
    async def leave_channel(self, channel_id: str) -> bool:
        """
        Leave a channel.
        
        Args:
            channel_id: ID of channel to leave
            
        Returns:
            True if leave successful
        """
        result = await self.send_command("leave_channel", {
            "channel_id": channel_id
        })
        return result.get("success", False)


async def main():
    """Example usage of ArqonBus client."""
    
    # Create client
    client = ArqonBusClient(host="localhost", port=8765, client_id="arq_client_demo")
    
    try:
        # Connect to ArqonBus
        await client.connect()
        
        # Test connectivity
        if await client.ping():
            print("✅ Ping successful")
        else:
            print("❌ Ping failed")
            return
        
        # Get server status
        status = await client.get_status()
        print(f"✅ Server status: {status}")
        
        # Create a channel
        if await client.create_channel("arq_channel_demo", "Demo channel"):
            print("✅ Channel created")
        else:
            print("❌ Channel creation failed")
        
        # Join the channel
        if await client.join_channel("arq_channel_demo"):
            print("✅ Joined channel")
        else:
            print("❌ Failed to join channel")
        
        # Send a message to the channel
        message_id = await client.send_message(
            channel="arq_channel_demo",
            content={"message": "Hello from Python client!"}
        )
        print(f"✅ Sent message: {message_id}")
        
        # List channels
        channels = await client.list_channels()
        print(f"✅ Available channels: {channels}")
        
        # Start listening for messages (in a real app, this would run continuously)
        print("📡 Starting to listen for messages...")
        
        # Listen for a few seconds
        listen_task = asyncio.create_task(client.listen())
        await asyncio.sleep(5)
        listen_task.cancel()
        
        # Leave the channel
        await client.leave_channel("arq_channel_demo")
        print("✅ Left channel")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.disconnect()
        print("👋 Disconnected")


if __name__ == "__main__":
    # Example 1: Simple usage
    print("=== ArqonBus Python Client Example ===")
    print("Starting simple message example...")
    
    asyncio.run(main())