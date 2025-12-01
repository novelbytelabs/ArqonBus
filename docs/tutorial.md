# ArqonBus Tutorial: Building Real-Time Applications

This hands-on tutorial teaches you how to build real-world applications using ArqonBus. We'll create three complete examples: a chat application, a collaborative document editor, and an IoT monitoring dashboard.

## Tutorial Overview

### What You'll Build

1. **Real-time Chat Application** - Multi-user chat with channels and user presence
2. **Collaborative Document Editor** - Real-time collaborative editing with cursor tracking
3. **IoT Monitoring Dashboard** - Real-time sensor data visualization and alerts

### Prerequisites

- Python 3.10+ installed
- ArqonBus installed and running
- Basic knowledge of Python and async/await
- Redis (optional, for persistence)

### Learning Goals

- Understanding ArqonBus message patterns
- Building robust client applications
- Implementing real-time features
- Handling authentication and security
- Scaling and monitoring applications

## Project Setup

### Step 1: Environment Setup

```bash
# Create project directory
mkdir arqonbus-tutorial
cd arqonbus-tutorial

# Set up virtual environment
python -m venv tutorial-env
source tutorial-env/bin/activate  # On Windows: tutorial-env\Scripts\activate

# Install dependencies
pip install websockets aiohttp asyncio
pip install redis  # Optional, for persistence

# Start ArqonBus server
# (Run in separate terminal)
python -m arqonbus.main
```

### Step 2: Verify Setup

Create a quick test file to verify everything works:

```python
# test_setup.py
import asyncio
import websockets
import json

async def test_connection():
    try:
        uri = "ws://localhost:8765"
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to ArqonBus successfully!")
            
            # Send a test message
            test_message = {
                "type": "message",
                "channel": "test",
                "content": "Hello ArqonBus!",
                "sender": "test-client"
            }
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✅ Received response: {data['content']}")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
```

Run the test:
```bash
python test_setup.py
```

## Project 1: Real-Time Chat Application

### Overview

We'll build a multi-user chat application with:
- Multiple channels
- User presence (online/offline status)
- Message history
- User authentication
- File sharing (bonus feature)

### Architecture

```
┌─────────────────────┐
│   Chat Client       │
│  (Web Interface)    │
└─────────┬───────────┘
          │ WebSocket
          ▼
┌─────────────────────┐
│    ArqonBus         │
│   Message Bus       │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   User Database     │
│   (Optional)        │
└─────────────────────┘
```

### Step 1: Create Chat Client Library

```python
# chat_client.py
import asyncio
import websockets
import json
from datetime import datetime
from typing import Dict, List, Callable, Optional

class ChatClient:
    """Advanced chat client with full feature set."""
    
    def __init__(self, uri: str, username: str, password: str = None):
        self.uri = uri
        self.username = username
        self.password = password
        self.websocket = None
        self.channels = set()
        self.users = {}  # username -> status
        self.message_handlers = []
        self.presence_handlers = []
        self.system_handlers = []
        
    async def connect(self):
        """Connect to ArqonBus server."""
        try:
            self.websocket = await websockets.connect(self.uri)
            print(f"✅ Connected to {self.uri}")
            
            # Send authentication if password provided
            if self.password:
                await self.send_command("authenticate", {
                    "username": self.username,
                    "password": self.password
                })
            
            # Start message listener
            asyncio.create_task(self._message_listener())
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from server."""
        if self.websocket:
            await self.websocket.close()
            print("🔌 Disconnected from server")
    
    async def join_channel(self, channel: str):
        """Join a chat channel."""
        await self.send_command("join_channel", {"channel": channel})
        self.channels.add(channel)
        print(f"📥 Joined channel: {channel}")
    
    async def leave_channel(self, channel: str):
        """Leave a chat channel."""
        await self.send_command("leave_channel", {"channel": channel})
        self.channels.discard(channel)
        print(f"📤 Left channel: {channel}")
    
    async def create_channel(self, channel: str, description: str = ""):
        """Create a new channel."""
        await self.send_command("create_channel", {
            "channel": channel,
            "description": description
        })
        print(f"✨ Created channel: {channel}")
    
    async def list_channels(self) -> List[Dict]:
        """Get list of available channels."""
        response = await self.send_command("list_channels")
        return response.get("data", {}).get("channels", [])
    
    async def send_message(self, channel: str, content: str, message_type: str = "text"):
        """Send a message to a channel."""
        message = {
            "type": "message",
            "channel": channel,
            "content": {
                "text": content,
                "type": message_type,
                "timestamp": datetime.now().isoformat()
            },
            "sender": self.username
        }
        await self.websocket.send(json.dumps(message))
    
    async def send_private_message(self, recipient: str, content: str):
        """Send a private message to another user."""
        message = {
            "type": "message",
            "channel": f"private_{recipient}",
            "content": {
                "text": content,
                "type": "private",
                "timestamp": datetime.now().isoformat()
            },
            "sender": self.username,
            "metadata": {
                "recipient": recipient,
                "private": True
            }
        }
        await self.websocket.send(json.dumps(message))
    
    async def get_message_history(self, channel: str, limit: int = 50):
        """Get message history for a channel."""
        await self.send_command("history", {"channel": channel, "limit": limit})
    
    async def update_status(self, status: str):
        """Update user presence status."""
        await self.send_command("set_status", {
            "username": self.username,
            "status": status
        })
    
    async def send_command(self, command: str, data: Dict = None):
        """Send a command to the server."""
        command_msg = {
            "type": "command",
            "command": command,
            "data": data or {}
        }
        await self.websocket.send(json.dumps(command_msg))
        
        # Wait for command response
        response = await self.websocket.recv()
        return json.loads(response)
    
    async def _message_listener(self):
        """Listen for incoming messages."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Connection closed")
        except Exception as e:
            print(f"❌ Message listener error: {e}")
    
    async def _handle_message(self, message: Dict):
        """Handle incoming messages based on type."""
        msg_type = message.get("type")
        
        if msg_type == "message":
            await self._handle_chat_message(message)
        elif msg_type == "event":
            await self._handle_system_event(message)
        elif msg_type == "command_response":
            await self._handle_command_response(message)
    
    async def _handle_chat_message(self, message: Dict):
        """Handle chat messages."""
        content = message.get("content", {})
        channel = message.get("channel", "unknown")
        sender = message.get("sender", "unknown")
        msg_type = content.get("type", "text")
        
        if msg_type == "private":
            print(f"🔒 [PRIVATE] {sender}: {content.get('text')}")
        else:
            timestamp = content.get("timestamp", "")
            formatted_time = timestamp.split("T")[1].split(".")[0] if "T" in timestamp else ""
            print(f"[{formatted_time}] #{channel} {sender}: {content.get('text')}")
        
        # Call registered handlers
        for handler in self.message_handlers:
            try:
                await handler(message)
            except Exception as e:
                print(f"Message handler error: {e}")
    
    async def _handle_system_event(self, message: Dict):
        """Handle system events like user presence."""
        event_type = message.get("content", {}).get("type")
        
        if event_type == "user_joined":
            user = message.get("content", {}).get("user")
            channel = message.get("content", {}).get("channel")
            print(f"👤 {user} joined #{channel}")
            
        elif event_type == "user_left":
            user = message.get("content", {}).get("user")
            channel = message.get("content", {}).get("channel")
            print(f"👋 {user} left #{channel}")
            
        elif event_type == "user_status":
            user = message.get("content", {}).get("user")
            status = message.get("content", {}).get("status")
            self.users[user] = status
            print(f"💬 {user} is now {status}")
        
        # Call registered handlers
        for handler in self.presence_handlers:
            try:
                await handler(message)
            except Exception as e:
                print(f"Presence handler error: {e}")
    
    async def _handle_command_response(self, message: Dict):
        """Handle command responses."""
        command = message.get("command")
        success = message.get("success", False)
        
        if success:
            print(f"✅ Command '{command}' executed successfully")
        else:
            error = message.get("error", "Unknown error")
            print(f"❌ Command '{command}' failed: {error}")
    
    # Event handlers registration
    def on_message(self, handler: Callable):
        """Register a message handler."""
        self.message_handlers.append(handler)
    
    def on_presence(self, handler: Callable):
        """Register a presence handler."""
        self.presence_handlers.append(handler)
    
    def on_system(self, handler: Callable):
        """Register a system event handler."""
        self.system_handlers.append(handler)
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
```

### Step 2: Create Chat Interface

```python
# chat_interface.py
import asyncio
from chat_client import ChatClient

class ChatInterface:
    """Interactive chat interface."""
    
    def __init__(self, client: ChatClient):
        self.client = client
        self.running = False
    
    async def start(self):
        """Start the interactive chat interface."""
        self.running = True
        
        # Register handlers
        self.client.on_message(self._message_handler)
        self.client.on_presence(self._presence_handler)
        
        print("🎮 Chat Interface Started")
        print("Commands:")
        print("  /join <channel> - Join a channel")
        print("  /leave <channel> - Leave a channel") 
        print("  /channels - List channels")
        print("  /create <channel> - Create new channel")
        print("  /status <status> - Set your status")
        print("  /help - Show this help")
        print("  /quit - Exit chat")
        print()
        
        # Join default channels
        await self.client.join_channel("general")
        await self.client.join_channel("random")
        
        # Start input loop
        await self._input_loop()
    
    async def _input_loop(self):
        """Main input processing loop."""
        while self.running:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, f"{self.client.username}> "
                )
                
                if user_input.strip():
                    await self._process_input(user_input)
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Input error: {e}")
        
        self.running = False
        await self.client.disconnect()
    
    async def _process_input(self, user_input: str):
        """Process user input."""
        user_input = user_input.strip()
        
        # Handle commands
        if user_input.startswith('/'):
            await self._process_command(user_input)
        else:
            # Send as message to general channel
            await self.client.send_message("general", user_input)
    
    async def _process_command(self, user_input: str):
        """Process slash commands."""
        parts = user_input.split(' ', 2)
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if command == "/join" and args:
            await self.client.join_channel(args[0])
            
        elif command == "/leave" and args:
            await self.client.leave_channel(args[0])
            
        elif command == "/channels":
            channels = await self.client.list_channels()
            print("📋 Available channels:")
            for channel in channels:
                print(f"  #{channel}")
                
        elif command == "/create" and args:
            channel_name = args[0]
            description = args[1] if len(args) > 1 else ""
            await self.client.create_channel(channel_name, description)
            
        elif command == "/status" and args:
            await self.client.update_status(args[0])
            
        elif command == "/help":
            self._show_help()
            
        elif command == "/quit":
            self.running = False
            
        else:
            print(f"❌ Unknown command: {command}")
    
    def _show_help(self):
        """Show help information."""
        print("📚 Available commands:")
        print("  /join <channel> - Join a channel")
        print("  /leave <channel> - Leave a channel")
        print("  /channels - List channels")
        print("  /create <channel> [description] - Create new channel")
        print("  /status <status> - Set your status (online, away, busy)")
        print("  /help - Show this help")
        print("  /quit - Exit chat")
    
    async def _message_handler(self, message: Dict):
        """Handle incoming messages with rich formatting."""
        content = message.get("content", {})
        sender = message.get("sender")
        channel = message.get("channel")
        msg_type = content.get("type")
        
        # Skip our own messages in the display
        if sender == self.client.username:
            return
        
        # Format based on message type
        if msg_type == "system":
            print(f"🔧 [SYSTEM] {content.get('text')}")
        elif msg_type == "file":
            print(f"📎 [FILE] {sender}: {content.get('filename')} ({content.get('size')} bytes)")
        elif msg_type == "image":
            print(f"🖼️ [IMAGE] {sender}: {content.get('filename')}")
        else:
            text = content.get("text", "")
            print(f"💬 {sender} in #{channel}: {text}")
    
    async def _presence_handler(self, message: Dict):
        """Handle presence events."""
        content = message.get("content", {})
        event_type = content.get("type")
        
        if event_type == "user_online":
            user = content.get("user")
            print(f"🟢 {user} came online")
            
        elif event_type == "user_offline":
            user = content.get("user")
            print(f"🔴 {user} went offline")

# Main execution
async def main():
    print("🎯 ArqonBus Chat Application")
    print("=" * 40)
    
    username = input("Enter your username: ")
    password = input("Enter password (optional): ") or None
    server_url = "ws://localhost:8765"
    
    # Create and connect client
    client = ChatClient(server_url, username, password)
    
    try:
        await client.connect()
        
        # Start chat interface
        interface = ChatInterface(client)
        await interface.start()
        
    except Exception as e:
        print(f"❌ Failed to start chat: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 3: Run the Chat Application

```bash
# Terminal 1: Start ArqonBus server
python -m arqonbus.main

# Terminal 2: Run chat application
python chat_interface.py
```

Test with multiple users in separate terminals to see real-time communication in action!

### Step 4: Add File Sharing Feature

```python
# file_sharing.py
import asyncio
import base64
import json
import os
from pathlib import Path

class FileSharer:
    """File sharing functionality for chat."""
    
    def __init__(self, client: ChatClient):
        self.client = client
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)
    
    async def share_file(self, channel: str, file_path: str, file_type: str = "auto"):
        """Share a file in a channel."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                return
            
            # Determine file type
            if file_type == "auto":
                file_type = self._detect_file_type(file_path)
            
            # Read and encode file
            with open(file_path, 'rb') as f:
                file_data = f.read()
                encoded_data = base64.b64encode(file_data).decode('utf-8')
            
            # Send file message
            file_message = {
                "type": "message",
                "channel": channel,
                "content": {
                    "type": "file",
                    "filename": file_path.name,
                    "size": len(file_data),
                    "file_type": file_type,
                    "data": encoded_data,
                    "upload_time": asyncio.get_event_loop().time()
                },
                "sender": self.client.username
            }
            
            await self.client.websocket.send(json.dumps(file_message))
            print(f"📎 Shared file: {file_path.name} ({len(file_data)} bytes)")
            
        except Exception as e:
            print(f"❌ File sharing failed: {e}")
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type based on extension."""
        extension = file_path.suffix.lower()
        
        image_types = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'}
        document_types = {'.pdf', '.doc', '.docx', '.txt', '.md'}
        code_types = {'.py', '.js', '.html', '.css', '.java', '.cpp', '.c'}
        
        if extension in image_types:
            return "image"
        elif extension in document_types:
            return "document"
        elif extension in code_types:
            return "code"
        else:
            return "binary"
    
    async def download_file(self, message: Dict, save_path: str = None):
        """Download a file from a message."""
        try:
            content = message.get("content", {})
            if content.get("type") != "file":
                print("❌ Not a file message")
                return
            
            filename = content.get("filename")
            file_data = content.get("data")
            
            if not save_path:
                save_path = self.upload_dir / filename
            else:
                save_path = Path(save_path)
            
            # Decode and save file
            decoded_data = base64.b64decode(file_data)
            with open(save_path, 'wb') as f:
                f.write(decoded_data)
            
            print(f"📥 Downloaded: {filename} -> {save_path}")
            
        except Exception as e:
            print(f"❌ File download failed: {e}")

# Usage in chat client
async def enhanced_chat_main():
    username = input("Username: ")
    client = ChatClient("ws://localhost:8765", username)
    
    await client.connect()
    
    # Add file sharing
    file_sharer = FileSharer(client)
    
    # Enhanced message handler
    async def enhanced_message_handler(message):
        content = message.get("content", {})
        msg_type = content.get("type")
        
        if msg_type == "file":
            print(f"📎 File received: {content.get('filename')}")
            print("Type 'y' to download: ", end="")
            
            # Simple download prompt (in real app, use proper UI)
            user_choice = input().strip().lower()
            if user_choice == 'y':
                await file_sharer.download_file(message)
        
        # Process other message types...
    
    client.on_message(enhanced_message_handler)
    
    # File sharing commands
    while True:
        command = input("Command (/share <filename> or /quit): ").strip()
        
        if command.startswith("/share"):
            parts = command.split(" ", 1)
            if len(parts) > 1:
                filename = parts[1]
                await file_sharer.share_file("general", filename)
            else:
                print("Usage: /share <filename>")
        elif command == "/quit":
            break
        else:
            await client.send_message("general", command)
    
    await client.disconnect()
```

## Project 2: Collaborative Document Editor

### Overview

Build a real-time collaborative editor with:
- Live cursor tracking
- Conflict resolution
- Undo/redo functionality
- User presence indicators
- Document versioning

### Step 1: Create Collaborative Editor

```python
# collaborative_editor.py
import asyncio
import json
import difflib
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict

@dataclass
class CursorPosition:
    """Represents a user's cursor position."""
    user_id: str
    line: int
    column: int
    timestamp: float

@dataclass
class DocumentChange:
    """Represents a document change operation."""
    operation: str  # 'insert', 'delete', 'replace'
    position: int
    content: str
    user_id: str
    timestamp: float
    version: int

@dataclass
class DocumentVersion:
    """Represents a document snapshot."""
    content: str
    version: int
    timestamp: float
    user_id: str

class CollaborativeDocument:
    """Manages a collaborative document with real-time editing."""
    
    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self.content = ""
        self.version = 0
        self.changes: List[DocumentChange] = []
        self.cursors: Dict[str, CursorPosition] = {}
        self.user_versions: Dict[str, DocumentVersion] = {}
        self.undo_stacks: Dict[str, List[DocumentChange]] = {}
        self.max_undo_steps = 50
        
    def add_change(self, change: DocumentChange):
        """Add a document change."""
        self.changes.append(change)
        self.version += 1
        
        # Add to user's undo stack
        if change.user_id not in self.undo_stacks:
            self.undo_stacks[change.user_id] = []
        
        self.undo_stacks[change.user_id].append(change)
        
        # Limit undo stack size
        if len(self.undo_stacks[change.user_id]) > self.max_undo_steps:
            self.undo_stacks[change.user_id].pop(0)
        
        # Update content
        self._apply_change(change)
        
        # Create version snapshot
        self.user_versions[change.user_id] = DocumentVersion(
            content=self.content,
            version=self.version,
            timestamp=change.timestamp,
            user_id=change.user_id
        )
    
    def _apply_change(self, change: DocumentChange):
        """Apply a change to the document content."""
        if change.operation == 'insert':
            self.content = (self.content[:change.position] + 
                          change.content + 
                          self.content[change.position:])
        
        elif change.operation == 'delete':
            self.content = (self.content[:change.position] + 
                          self.content[change.position + len(change.content):])
        
        elif change.operation == 'replace':
            self.content = (self.content[:change.position] + 
                          change.content + 
                          self.content[change.position + len(change.content):])
    
    def undo(self, user_id: str) -> Optional[DocumentChange]:
        """Undo the last change for a user."""
        if user_id not in self.undo_stacks or not self.undo_stacks[user_id]:
            return None
        
        change = self.undo_stacks[user_id].pop()
        
        # Create inverse operation
        inverse_change = self._create_inverse_change(change)
        
        if inverse_change:
            self._apply_change(inverse_change)
            self.changes.append(inverse_change)
            self.version += 1
        
        return inverse_change
    
    def _create_inverse_change(self, change: DocumentChange) -> Optional[DocumentChange]:
        """Create the inverse of a change for undo."""
        if change.operation == 'insert':
            # Inverse of insert is delete
            return DocumentChange(
                operation='delete',
                position=change.position,
                content=change.content,
                user_id=change.user_id,
                timestamp=datetime.now().timestamp(),
                version=self.version + 1
            )
        elif change.operation == 'delete':
            # Inverse of delete is insert
            return DocumentChange(
                operation='insert',
                position=change.position,
                content=change.content,
                user_id=change.user_id,
                timestamp=datetime.now().timestamp(),
                version=self.version + 1
            )
        return None
    
    def update_cursor(self, user_id: str, line: int, column: int):
        """Update a user's cursor position."""
        self.cursors[user_id] = CursorPosition(
            user_id=user_id,
            line=line,
            column=column,
            timestamp=datetime.now().timestamp()
        )
    
    def get_conflicts(self, change: DocumentChange) -> List[DocumentChange]:
        """Check for conflicts with recent changes."""
        conflicts = []
        recent_changes = [c for c in self.changes[-10:] if c.user_id != change.user_id]
        
        for recent_change in recent_changes:
            if self._changes_conflict(change, recent_change):
                conflicts.append(recent_change)
        
        return conflicts
    
    def _changes_conflict(self, change1: DocumentChange, change2: DocumentChange) -> bool:
        """Check if two changes conflict."""
        # Simplified conflict detection
        if change1.operation == 'insert' and change2.operation == 'insert':
            # Concurrent insertions at the same position
            return abs(change1.position - change2.position) < len(change1.content)
        
        elif change1.operation == 'delete' and change2.operation == 'delete':
            # Concurrent deletions overlapping
            pos1_start, pos1_end = change1.position, change1.position + len(change1.content)
            pos2_start, pos2_end = change2.position, change2.position + len(change2.content)
            
            return not (pos1_end <= pos2_start or pos2_end <= pos1_start)
        
        return False

class CollaborativeEditor:
    """Real-time collaborative document editor."""
    
    def __init__(self, doc_id: str, server_url: str):
        self.doc_id = doc_id
        self.server_url = server_url
        self.websocket = None
        self.document = CollaborativeDocument(doc_id)
        self.client_id = f"editor_{doc_id}"
        self.is_running = False
        
    async def connect(self):
        """Connect to ArqonBus server."""
        self.websocket = await websockets.connect(self.server_url)
        
        # Join document channel
        join_message = {
            "type": "command",
            "command": "join_channel",
            "channel": f"doc_{self.doc_id}"
        }
        await self.websocket.send(json.dumps(join_message))
        
        # Start message listener
        asyncio.create_task(self._message_listener())
        self.is_running = True
        
        print(f"📝 Connected to document: {self.doc_id}")
    
    async def disconnect(self):
        """Disconnect from server."""
        if self.websocket:
            await self.websocket.close()
        self.is_running = False
    
    async def edit_text(self, operation: str, position: int, content: str):
        """Submit a text edit operation."""
        change = DocumentChange(
            operation=operation,
            position=position,
            content=content,
            user_id=self.client_id,
            timestamp=datetime.now().timestamp(),
            version=self.document.version + 1
        )
        
        # Check for conflicts
        conflicts = self.document.get_conflicts(change)
        
        if conflicts:
            print(f"⚠️  Conflicts detected with {len(conflicts)} recent changes")
            # In a real system, you'd show conflict resolution UI
        
        # Apply local change
        self.document.add_change(change)
        
        # Broadcast to server
        edit_message = {
            "type": "message",
            "channel": f"doc_{self.doc_id}",
            "content": {
                "type": "edit",
                "operation": operation,
                "position": position,
                "content": content,
                "version": change.version
            },
            "sender": self.client_id
        }
        
        await self.websocket.send(json.dumps(edit_message))
    
    async def update_cursor(self, line: int, column: int):
        """Update cursor position."""
        self.document.update_cursor(self.client_id, line, column)
        
        cursor_message = {
            "type": "message",
            "channel": f"doc_{self.doc_id}",
            "content": {
                "type": "cursor",
                "line": line,
                "column": column
            },
            "sender": self.client_id
        }
        
        await self.websocket.send(json.dumps(cursor_message))
    
    async def undo(self):
        """Undo the last edit."""
        inverse_change = self.document.undo(self.client_id)
        
        if inverse_change:
            undo_message = {
                "type": "message",
                "channel": f"doc_{self.doc_id}",
                "content": {
                    "type": "undo",
                    "inverse_change": asdict(inverse_change)
                },
                "sender": self.client_id
            }
            
            await self.websocket.send(json.dumps(undo_message))
            print("↩️  Undo executed")
        else:
            print("❌ Nothing to undo")
    
    async def _message_listener(self):
        """Listen for document synchronization messages."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Document connection closed")
    
    async def _handle_message(self, message: Dict):
        """Handle incoming document messages."""
        content = message.get("content", {})
        sender = message.get("sender")
        msg_type = content.get("type")
        
        if sender == self.client_id:
            return  # Skip our own messages
        
        if msg_type == "edit":
            # Apply remote edit
            change = DocumentChange(
                operation=content["operation"],
                position=content["position"],
                content=content["content"],
                user_id=sender,
                timestamp=datetime.now().timestamp(),
                version=content["version"]
            )
            
            self.document.add_change(change)
            print(f"📝 Applied remote edit by {sender}")
            
        elif msg_type == "cursor":
            # Update remote cursor
            self.document.update_cursor(
                sender,
                content["line"],
                content["column"]
            )
            
        elif msg_type == "undo":
            # Apply remote undo
            inverse_data = content["inverse_change"]
            inverse_change = DocumentChange(**inverse_data)
            
            self.document.add_change(inverse_change)
            print(f"↩️  Applied remote undo by {sender}")

# Interactive editor interface
async def interactive_editor():
    """Interactive collaborative editor."""
    doc_id = input("Document ID (or press Enter for 'demo'): ").strip() or "demo"
    server_url = "ws://localhost:8765"
    
    editor = CollaborativeEditor(doc_id, server_url)
    
    try:
        await editor.connect()
        
        print("🎯 Collaborative Editor")
        print("Commands:")
        print("  i <position> <text> - Insert text at position")
        print("  d <position> <length> - Delete text at position")
        print("  r <position> <length> <text> - Replace text at position")
        print("  u - Undo last change")
        print("  c <line> <column> - Update cursor position")
        print("  s - Show document content")
        print("  p - Show document statistics")
        print("  q - Quit")
        print()
        
        print("📝 Document content:")
        print(editor.document.content)
        print()
        
        while editor.is_running:
            try:
                command = input("Editor> ").strip()
                
                if not command:
                    continue
                
                if command == 'q':
                    break
                elif command == 's':
                    print("📝 Current content:")
                    print(editor.document.content)
                elif command == 'p':
                    print(f"📊 Document statistics:")
                    print(f"  Version: {editor.document.version}")
                    print(f"  Characters: {len(editor.document.content)}")
                    print(f"  Lines: {editor.document.content.count(chr(10)) + 1}")
                    print(f"  Active users: {len(editor.document.cursors)}")
                elif command == 'u':
                    await editor.undo()
                elif command.startswith('i '):
                    parts = command.split(' ', 2)
                    if len(parts) >= 3:
                        position = int(parts[1])
                        text = parts[2]
                        await editor.edit_text('insert', position, text)
                elif command.startswith('d '):
                    parts = command.split(' ', 2)
                    if len(parts) >= 3:
                        position = int(parts[1])
                        length = int(parts[2])
                        # Get text to delete
                        text_to_delete = editor.document.content[position:position + length]
                        await editor.edit_text('delete', position, text_to_delete)
                elif command.startswith('r '):
                    parts = command.split(' ', 3)
                    if len(parts) >= 4:
                        position = int(parts[1])
                        length = int(parts[2])
                        text = parts[3]
                        # Get text to replace
                        text_to_replace = editor.document.content[position:position + length]
                        await editor.edit_text('replace', position, text)
                elif command.startswith('c '):
                    parts = command.split(' ')
                    if len(parts) >= 3:
                        line = int(parts[1])
                        column = int(parts[2])
                        await editor.update_cursor(line, column)
                else:
                    print("❌ Unknown command")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Command error: {e}")
        
        await editor.disconnect()
        
    except Exception as e:
        print(f"❌ Editor error: {e}")

if __name__ == "__main__":
    asyncio.run(interactive_editor())
```

## Project 3: IoT Monitoring Dashboard

### Overview

Build an IoT monitoring dashboard with:
- Real-time sensor data visualization
- Alert system with thresholds
- Historical data storage
- Device management
- Multi-tenant support

### Step 1: Create IoT Device Simulator

```python
# iot_simulator.py
import asyncio
import json
import random
import time
from datetime import datetime
from typing import Dict, List, Optional

class IoTDevice:
    """Simulated IoT device."""
    
    def __init__(self, device_id: str, device_type: str, location: str):
        self.device_id = device_id
        self.device_type = device_type
        self.location = location
        self.is_online = True
        self.last_heartbeat = time.time()
        self.data_points = []
        self.alert_thresholds = {}
        
        # Device-specific configurations
        self.config = self._get_device_config(device_type)
    
    def _get_device_config(self, device_type: str) -> Dict:
        """Get configuration for device type."""
        configs = {
            "temperature_sensor": {
                "min_value": 15.0,
                "max_value": 35.0,
                "unit": "°C",
                "precision": 1,
                "update_interval": 5  # seconds
            },
            "humidity_sensor": {
                "min_value": 30.0,
                "max_value": 80.0,
                "unit": "%",
                "precision": 1,
                "update_interval": 10
            },
            "pressure_sensor": {
                "min_value": 900.0,
                "max_value": 1100.0,
                "unit": "hPa",
                "precision": 1,
                "update_interval": 15
            },
            "motion_detector": {
                "values": ["motion", "no_motion"],
                "unit": "boolean",
                "update_interval": 2
            },
            "light_sensor": {
                "min_value": 0.0,
                "max_value": 1000.0,
                "unit": "lux",
                "precision": 0,
                "update_interval": 8
            }
        }
        return configs.get(device_type, {})
    
    def generate_sensor_data(self) -> Dict:
        """Generate sensor reading."""
        timestamp = datetime.now()
        
        if self.device_type == "motion_detector":
            # Motion detector - random boolean
            value = random.choice(self.config["values"])
        else:
            # Numeric sensors with some random variation
            base_value = random.uniform(self.config["min_value"], self.config["max_value"])
            value = round(base_value, self.config["precision"])
        
        # Add some drift and noise for realism
        if isinstance(value, (int, float)) and self.data_points:
            last_value = self.data_points[-1]["value"]
            drift = random.uniform(-2, 2)
            value = max(self.config.get("min_value", value), 
                       min(self.config.get("max_value", value), 
                           last_value + drift))
            value = round(value, self.config["precision"])
        
        data_point = {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "location": self.location,
            "timestamp": timestamp.isoformat(),
            "value": value,
            "unit": self.config.get("unit", ""),
            "quality": random.choice(["good", "fair", "poor"]),  # Data quality
            "battery_level": random.randint(10, 100) if random.random() < 0.1 else 95
        }
        
        self.data_points.append(data_point)
        
        # Keep only last 1000 data points to prevent memory issues
        if len(self.data_points) > 1000:
            self.data_points = self.data_points[-1000:]
        
        # Check for alerts
        alerts = self._check_alerts(data_point)
        if alerts:
            data_point["alerts"] = alerts
        
        return data_point
    
    def _check_alerts(self, data_point: Dict) -> List[Dict]:
        """Check if data point triggers any alerts."""
        alerts = []
        value = data_point["value"]
        
        # Temperature alerts
        if self.device_type == "temperature_sensor":
            if value > 30.0:
                alerts.append({
                    "type": "high_temperature",
                    "message": f"Temperature too high: {value}°C",
                    "severity": "warning" if value < 35 else "critical"
                })
            elif value < 18.0:
                alerts.append({
                    "type": "low_temperature", 
                    "message": f"Temperature too low: {value}°C",
                    "severity": "warning"
                })
        
        # Humidity alerts
        elif self.device_type == "humidity_sensor":
            if value > 70.0:
                alerts.append({
                    "type": "high_humidity",
                    "message": f"Humidity too high: {value}%",
                    "severity": "warning"
                })
            elif value < 40.0:
                alerts.append({
                    "type": "low_humidity",
                    "message": f"Humidity too low: {value}%",
                    "severity": "warning"
                })
        
        # Motion alerts
        elif self.device_type == "motion_detector":
            if value == "motion":
                alerts.append({
                    "type": "motion_detected",
                    "message": "Motion detected in area",
                    "severity": "info"
                })
        
        # Battery alerts
        battery_level = data_point.get("battery_level", 100)
        if battery_level < 20:
            alerts.append({
                "type": "low_battery",
                "message": f"Battery level low: {battery_level}%",
                "severity": "warning"
            })
        
        return alerts
    
    def simulate_offline(self):
        """Simulate device going offline."""
        self.is_online = False
        print(f"📴 Device {self.device_id} went offline")
    
    def simulate_online(self):
        """Simulate device coming back online."""
        self.is_online = True
        self.last_heartbeat = time.time()
        print(f"📶 Device {self.device_id} came online")

class IoTDeviceManager:
    """Manages multiple IoT devices."""
    
    def __init__(self):
        self.devices: Dict[str, IoTDevice] = {}
        self.running = False
        
    def add_device(self, device: IoTDevice):
        """Add a device to the manager."""
        self.devices[device.device_id] = device
        print(f"➕ Added device: {device.device_id} ({device.device_type})")
    
    def remove_device(self, device_id: str):
        """Remove a device from the manager."""
        if device_id in self.devices:
            del self.devices[device_id]
            print(f"➖ Removed device: {device_id}")
    
    async def start_simulation(self):
        """Start the device simulation."""
        self.running = True
        print("🚀 Starting IoT device simulation...")
        
        while self.running:
            for device in self.devices.values():
                if device.is_online:
                    data_point = device.generate_sensor_data()
                    yield data_point
                    
                    # Simulate occasional offline periods
                    if random.random() < 0.01:  # 1% chance per cycle
                        device.simulate_offline()
                        
                        # Come back online after 30-60 seconds
                        await asyncio.sleep(random.uniform(30, 60))
                        device.simulate_online()
            
            # Wait for next update cycle
            await asyncio.sleep(2)
    
    def stop_simulation(self):
        """Stop the device simulation."""
        self.running = False
        print("⏹️  Stopped IoT device simulation")

class IoTDataPublisher:
    """Publishes IoT data to ArqonBus."""
    
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.websocket = None
        self.device_manager = IoTDeviceManager()
        
    async def connect(self):
        """Connect to ArqonBus server."""
        self.websocket = await websockets.connect(self.server_url)
        print(f"📡 Connected to ArqonBus at {self.server_url}")
    
    async def disconnect(self):
        """Disconnect from server."""
        if self.websocket:
            await self.websocket.close()
    
    async def publish_data(self, data_point: Dict):
        """Publish a data point to ArqonBus."""
        if not self.websocket:
            return
        
        message = {
            "type": "message",
            "channel": f"sensors/{data_point['device_type']}",
            "content": {
                "type": "sensor_data",
                "data": data_point
            },
            "sender": "iot_simulator",
            "metadata": {
                "device_id": data_point["device_id"],
                "location": data_point["location"],
                "timestamp": data_point["timestamp"]
            }
        }
        
        await self.websocket.send(json.dumps(message))
    
    async def publish_alert(self, alert: Dict, device_id: str, device_type: str):
        """Publish an alert to ArqonBus."""
        if not self.websocket:
            return
        
        alert_message = {
            "type": "message",
            "channel": "alerts",
            "content": {
                "type": "alert",
                "alert": alert,
                "device_id": device_id,
                "device_type": device_type,
                "timestamp": datetime.now().isoformat()
            },
            "sender": "iot_simulator"
        }
        
        await self.websocket.send(json.dumps(alert_message))
    
    def setup_demo_devices(self):
        """Set up demonstration devices."""
        # Temperature sensors
        self.device_manager.add_device(IoTDevice(
            "temp_001", "temperature_sensor", "office_floor_1"
        ))
        self.device_manager.add_device(IoTDevice(
            "temp_002", "temperature_sensor", "server_room"
        ))
        
        # Humidity sensors
        self.device_manager.add_device(IoTDevice(
            "humid_001", "humidity_sensor", "warehouse"
        ))
        
        # Motion detectors
        self.device_manager.add_device(IoTDevice(
            "motion_001", "motion_detector", "entrance_hall"
        ))
        self.device_manager.add_device(IoTDevice(
            "motion_002", "motion_detector", "parking_garage"
        ))
        
        # Light sensors
        self.device_manager.add_device(IoTDevice(
            "light_001", "light_sensor", "office_floor_1"
        ))
    
    async def run_simulation(self):
        """Run the complete IoT simulation."""
        await self.connect()
        self.setup_demo_devices()
        
        print("🏭 IoT Device Simulation Started")
        print("Devices:")
        for device in self.device_manager.devices.values():
            print(f"  - {device.device_id}: {device.device_type} ({device.location})")
        print()
        
        try:
            async for data_point in self.device_manager.start_simulation():
                # Publish data
                await self.publish_data(data_point)
                
                # Publish alerts if any
                alerts = data_point.get("alerts", [])
                for alert in alerts:
                    await self.publish_alert(
                        alert, 
                        data_point["device_id"], 
                        data_point["device_type"]
                    )
                
                # Print data point
                print(f"📊 {data_point['device_id']}: {data_point['value']}{data_point['unit']} "
                      f"({data_point['location']})")
                
        except KeyboardInterrupt:
            print("\n⏹️  Simulation interrupted")
        finally:
            self.device_manager.stop_simulation()
            await self.disconnect()

# Run the IoT simulator
async def main():
    publisher = IoTDataPublisher("ws://localhost:8765")
    await publisher.run_simulation()

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 2: Create IoT Dashboard

```python
# iot_dashboard.py
import asyncio
import json
import websockets
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, deque

class IoTDashboard:
    """Real-time IoT monitoring dashboard."""
    
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.websocket = None
        self.devices: Dict[str, Dict] = {}
        self.sensor_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.alerts: List[Dict] = []
        self.subscribed_channels = set()
        
    async def connect(self):
        """Connect to ArqonBus server."""
        self.websocket = await websockets.connect(self.server_url)
        print(f"📡 Connected to ArqonBus dashboard")
        
        # Subscribe to sensor channels
        sensor_channels = [
            "sensors/temperature_sensor",
            "sensors/humidity_sensor", 
            "sensors/motion_detector",
            "sensors/light_sensor",
            "sensors/pressure_sensor",
            "alerts"
        ]
        
        for channel in sensor_channels:
            await self.subscribe_channel(channel)
        
        # Start message listener
        asyncio.create_task(self._message_listener())
        
    async def disconnect(self):
        """Disconnect from server."""
        if self.websocket:
            await self.websocket.close()
    
    async def subscribe_channel(self, channel: str):
        """Subscribe to a sensor channel."""
        subscribe_message = {
            "type": "command",
            "command": "join_channel",
            "channel": channel
        }
        await self.websocket.send(json.dumps(subscribe_message))
        self.subscribed_channels.add(channel)
        print(f"📥 Subscribed to channel: {channel}")
    
    async def _message_listener(self):
        """Listen for sensor data and alerts."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Dashboard connection closed")
    
    async def _handle_message(self, message: Dict):
        """Handle incoming messages."""
        content = message.get("content", {})
        msg_type = content.get("type")
        
        if msg_type == "sensor_data":
            await self._handle_sensor_data(content["data"])
        elif msg_type == "alert":
            await self._handle_alert(content["alert"], content)
    
    async def _handle_sensor_data(self, data_point: Dict):
        """Handle incoming sensor data."""
        device_id = data_point["device_id"]
        
        # Update device info
        if device_id not in self.devices:
            self.devices[device_id] = {
                "device_id": device_id,
                "device_type": data_point["device_type"],
                "location": data_point["location"],
                "last_seen": None,
                "status": "online",
                "battery_level": data_point.get("battery_level", 100),
                "current_value": data_point["value"],
                "unit": data_point["unit"]
            }
        
        device = self.devices[device_id]
        device["last_seen"] = data_point["timestamp"]
        device["current_value"] = data_point["value"]
        device["battery_level"] = data_point.get("battery_level", 100)
        device["quality"] = data_point.get("quality", "good")
        
        # Store historical data
        channel = f"{data_point['device_type']}_{data_point['location']}"
        self.sensor_data[channel].append(data_point)
        
        # Print data point
        timestamp = datetime.fromisoformat(data_point["timestamp"].replace("Z", "+00:00"))
        print(f"📊 [{timestamp.strftime('%H:%M:%S')}] {device_id}: "
              f"{data_point['value']}{data_point['unit']} "
              f"({data_point['location']})")
    
    async def _handle_alert(self, alert: Dict, message_data: Dict):
        """Handle incoming alerts."""
        device_id = message_data["device_id"]
        alert["device_id"] = device_id
        alert["timestamp"] = message_data["timestamp"]
        
        self.alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        # Print alert with severity coloring
        severity_icons = {
            "info": "ℹ️",
            "warning": "⚠️", 
            "critical": "🚨"
        }
        
        icon = severity_icons.get(alert["severity"], "📢")
        print(f"{icon} ALERT [{alert['severity'].upper()}] {alert['message']} "
              f"(Device: {device_id})")
    
    def get_dashboard_summary(self) -> Dict:
        """Get dashboard summary data."""
        now = datetime.now()
        
        # Count devices by type and status
        devices_by_type = defaultdict(int)
        devices_online = 0
        total_devices = len(self.devices)
        
        for device in self.devices.values():
            device_type = device["device_type"]
            devices_by_type[device_type] += 1
            
            # Check if device is online (seen within last 5 minutes)
            if device["last_seen"]:
                last_seen = datetime.fromisoformat(device["last_seen"].replace("Z", "+00:00"))
                if (now - last_seen).total_seconds() < 300:  # 5 minutes
                    devices_online += 1
        
        # Recent alerts (last hour)
        recent_alerts = [
            alert for alert in self.alerts
            if (now - datetime.fromisoformat(alert["timestamp"].replace("Z", "+00:00"))).total_seconds() < 3600
        ]
        
        # Critical alerts count
        critical_alerts = [a for a in recent_alerts if a["severity"] == "critical"]
        warning_alerts = [a for a in recent_alerts if a["severity"] == "warning"]
        
        return {
            "summary": {
                "total_devices": total_devices,
                "devices_online": devices_online,
                "devices_offline": total_devices - devices_online,
                "recent_alerts": len(recent_alerts),
                "critical_alerts": len(critical_alerts),
                "warning_alerts": len(warning_alerts)
            },
            "devices_by_type": dict(devices_by_type),
            "last_update": now.isoformat()
        }
    
    def get_device_details(self, device_id: str) -> Optional[Dict]:
        """Get detailed information about a device."""
        return self.devices.get(device_id)
    
    def get_sensor_history(self, channel: str, hours: int = 1) -> List[Dict]:
        """Get sensor data history for a channel."""
        if channel not in self.sensor_data:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        history = []
        
        for data_point in self.sensor_data[channel]:
            data_time = datetime.fromisoformat(data_point["timestamp"].replace("Z", "+00:00"))
            if data_time >= cutoff_time:
                history.append(data_point)
        
        return history
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts."""
        return self.alerts[-limit:]
    
    def display_dashboard(self):
        """Display dashboard in terminal."""
        summary = self.get_dashboard_summary()
        
        print("\n" + "="*60)
        print("🏭 IoT DASHBOARD - REAL-TIME MONITORING")
        print("="*60)
        
        # Summary section
        print(f"📊 SUMMARY")
        print(f"  Total Devices: {summary['summary']['total_devices']}")
        print(f"  Online: {summary['summary']['devices_online']} | "
              f"Offline: {summary['summary']['devices_offline']}")
        print(f"  Recent Alerts: {summary['summary']['recent_alerts']} "
              f"(⚠️ {summary['summary']['warning_alerts']} | 🚨 {summary['summary']['critical_alerts']})")
        
        # Device types
        print(f"\n🔧 DEVICE TYPES")
        for device_type, count in summary['devices_by_type'].items():
            print(f"  {device_type}: {count} devices")
        
        # Recent alerts
        recent_alerts = self.get_recent_alerts(5)
        if recent_alerts:
            print(f"\n🚨 RECENT ALERTS")
            for alert in reversed(recent_alerts[-5:]):
                timestamp = datetime.fromisoformat(alert["timestamp"].replace("Z", "+00:00"))
                severity_icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(alert["severity"], "📢")
                print(f"  {severity_icon} {timestamp.strftime('%H:%M:%S')} - {alert['message']} ({alert['device_id']})")
        
        print(f"\n📡 Channels: {', '.join(self.subscribed_channels)}")
        print("="*60)

# Interactive dashboard
async def interactive_dashboard():
    """Interactive IoT dashboard."""
    dashboard = IoTDashboard("ws://localhost:8765")
    
    try:
        await dashboard.connect()
        
        print("🎯 IoT Monitoring Dashboard")
        print("Commands:")
        print("  s - Show dashboard summary")
        print("  d <device_id> - Show device details")
        print("  h <channel> [hours] - Show sensor history")
        print("  a [limit] - Show recent alerts")
        print("  l - List all devices")
        print("  q - Quit")
        print()
        
        # Start periodic dashboard updates
        async def periodic_updates():
            while True:
                await asyncio.sleep(10)  # Update every 10 seconds
                dashboard.display_dashboard()
        
        update_task = asyncio.create_task(periodic_updates())
        
        # Command loop
        while True:
            try:
                command = input("Dashboard> ").strip()
                
                if command == 'q':
                    break
                elif command == 's':
                    dashboard.display_dashboard()
                elif command == 'l':
                    print("\n📋 ALL DEVICES")
                    for device_id, device in dashboard.devices.items():
                        status = "🟢" if (datetime.now() - 
                                       datetime.fromisoformat(device["last_seen"].replace("Z", "+00:00"))).total_seconds() < 300 else "🔴"
                        print(f"  {status} {device_id}: {device['device_type']} ({device['location']})")
                elif command.startswith('d '):
                    device_id = command.split(' ', 1)[1].strip()
                    device = dashboard.get_device_details(device_id)
                    if device:
                        print(f"\n📱 DEVICE DETAILS: {device_id}")
                        print(f"  Type: {device['device_type']}")
                        print(f"  Location: {device['location']}")
                        print(f"  Status: {'🟢 Online' if device.get('last_seen') and (datetime.now() - datetime.fromisoformat(device['last_seen'].replace('Z', '+00:00'))).total_seconds() < 300 else '🔴 Offline'}")
                        print(f"  Current Value: {device['current_value']}{device['unit']}")
                        print(f"  Battery: {device['battery_level']}%")
                        print(f"  Last Seen: {device.get('last_seen', 'Never')}")
                    else:
                        print(f"❌ Device {device_id} not found")
                elif command.startswith('h '):
                    parts = command.split(' ', 2)
                    if len(parts) >= 2:
                        channel = parts[1]
                        hours = int(parts[2]) if len(parts) > 2 else 1
                        history = dashboard.get_sensor_history(channel, hours)
                        print(f"\n📈 SENSOR HISTORY: {channel} (last {hours}h)")
                        for data_point in history[-10:]:  # Show last 10 points
                            timestamp = datetime.fromisoformat(data_point["timestamp"].replace("Z", "+00:00"))
                            print(f"  {timestamp.strftime('%H:%M:%S')}: {data_point['value']}{data_point['unit']}")
                    else:
                        print("Usage: h <channel> [hours]")
                elif command.startswith('a '):
                    try:
                        limit = int(command.split(' ', 1)[1])
                    except:
                        limit = 10
                    
                    alerts = dashboard.get_recent_alerts(limit)
                    print(f"\n🚨 RECENT ALERTS (last {limit})")
                    for alert in reversed(alerts):
                        timestamp = datetime.fromisoformat(alert["timestamp"].replace("Z", "+00:00"))
                        severity_icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(alert["severity"], "📢")
                        print(f"  {severity_icon} {timestamp.strftime('%H:%M:%S')} - {alert['message']} ({alert['device_id']})")
                else:
                    print("❌ Unknown command")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Command error: {e}")
        
        update_task.cancel()
        await dashboard.disconnect()
        
    except Exception as e:
        print(f"❌ Dashboard error: {e}")

if __name__ == "__main__":
    asyncio.run(interactive_dashboard())
```

## Running the Complete Tutorial

### Step 1: Start All Components

```bash
# Terminal 1: Start ArqonBus server
python -m arqonbus.main

# Terminal 2: Start IoT simulator (in background)
python iot_simulator.py &

# Terminal 3: Start IoT dashboard
python iot_dashboard.py

# Terminal 4: Start chat application (separate terminal)
python chat_interface.py
```

### Step 2: Test All Features

1. **Chat Application**: 
   - Join channels
   - Send messages
   - Test file sharing
   - Monitor real-time updates

2. **Collaborative Editor**:
   - Open document editing sessions
   - Test concurrent editing
   - Verify conflict resolution
   - Test undo/redo functionality

3. **IoT Dashboard**:
   - Monitor sensor data
   - Watch for alerts
   - Track device status
   - View historical data

## Advanced Tutorial Extensions

### Security Features
Add authentication and authorization to all applications:

```python
# Add to any client
config = {
    "security": {
        "enable_authentication": True,
        "auth_token": "your-jwt-token",
        "rate_limit_per_minute": 60
    }
}

# Implement secure connections
async def secure_connect(client):
    await client.connect()
    await client.authenticate("jwt-token-here")
```

### Scaling Features
Implement horizontal scaling with Redis clustering:

```python
# Redis cluster configuration
config = {
    "redis": {
        "cluster_nodes": [
            "redis1.example.com:6379",
            "redis2.example.com:6379",
            "redis3.example.com:6379"
        ],
        "connection_pool_size": 20
    }
}
```

### Monitoring Features
Add comprehensive monitoring:

```python
# Add monitoring hooks
async def add_monitoring(client):
    client.on_message(log_message_metrics)
    client.on_presence(log_presence_metrics)
    
def log_message_metrics(message):
    # Send to monitoring system
    metrics.increment("messages_processed")
    metrics.histogram("message_size", len(json.dumps(message)))
```

## Conclusion

Congratulations! You've completed a comprehensive tutorial on building real-time applications with ArqonBus. You've learned to:

✅ **Build robust real-time chat applications** with channels, file sharing, and presence  
✅ **Create collaborative editing systems** with conflict resolution and versioning  
✅ **Develop IoT monitoring dashboards** with real-time data visualization and alerts  
✅ **Implement security features** with authentication and authorization  
✅ **Scale applications** with Redis persistence and clustering  
✅ **Add monitoring and analytics** for production deployment  

### Next Steps

1. **Production Deployment**: Use the operations runbook to deploy in production
2. **Custom Extensions**: Build your own commands, storage backends, and features
3. **Performance Optimization**: Apply the performance tuning techniques from the developer guide
4. **Integration**: Connect with your existing systems and databases

### Resources

- 📖 [API Documentation](api.md) - Complete API reference
- 🏗️ [Architecture Guide](architecture.md) - System architecture details  
- 👨‍💻 [Developer Guide](developers_guide.md) - Comprehensive developer documentation
- 🔧 [Operations Runbook](runbook.md) - Production deployment and operations
- ⚡ [Quick Start](quickstart.md) - Fast setup guide

### Support

- **Issues**: Report bugs and feature requests on GitHub
- **Community**: Join our Discord/Slack for help and discussions
- **Documentation**: All documentation is available in the `/docs` directory
- **Examples**: Check the `/examples` directory for more code samples

**🎉 Happy building with ArqonBus!**