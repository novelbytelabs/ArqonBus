# ArqonBus

**ArqonBus** is a lightweight, structured WebSocket message bus with rooms, channels, and a simple command protocol. It’s designed to be the real-time backbone for applications, services, and agents that need organized, multi-channel communication.

> Status: **experimental / WIP**

---

## Key Features (Current)

### 🔌 WebSocket Server
- Persistent, bi-directional connections over WebSockets
- Configurable `--host`, `--port`, `--telemetry-port`

### 🧑‍💻 Client Model
- Tracks connected clients with:
  - `id`, `type` (human, dashboard, ai-agent, etc.)
  - room → channel memberships
  - optional `personality`, `screen_name`, `avatar`
  - `connected_at`, `last_activity`
- Server stats:
  - total / active connections
  - active rooms & channels
  - total messages

### 🏠 Rooms & Channels
- Hierarchical routing:
  - `room`
  - `room:channel` (e.g. `science:explore`)
- Each room has multiple channels; each channel has multiple clients.
- Clients can join/leave channels dynamically.

### 📡 Message Routing
- Automatic room/channel resolution:
  - explicit `room` / `channel`
  - `room:channel` format
  - fallback to client’s initial room/channel
- Message types:
  - **system** – internal/system broadcasts
  - **private** – direct to target client IDs
  - **command** – processed by the command handler
  - default **event** messages for normal traffic
- “pm” channel support for private-channel style messaging.

### 📢 Broadcast Helpers
- `broadcast_to_channel(room, channel, ...)`
- `broadcast_to_room(room, ...)`
- Avoids duplicate delivery to the same client.
- Cleans up broken connections automatically.

### 🧾 Message History
- In-memory rolling history (`deque`, max ~500 messages).
- `history` command:
  - filter by room
  - optional channel
  - returns recent messages (last 50).

### 🧩 Command System
Built-in commands (via `type: "command"`):

- `status` – server stats, channels, clients
- `create_channel` – admin-only, create `room:channel`
- `delete_channel` – admin-only, delete **empty** channels
- `join_channel` – join an existing (or auto-created) channel
- `leave_channel` – leave a channel
- `list_channels` – list channels in a room with participant counts
- `channel_info` – participants + metadata for a specific channel
- `ping` – returns `pong`
- `history` – recent message history

### 📊 Telemetry & Activity
- Separate telemetry WebSocket server (`--telemetry-port`).
- Validated telemetry events (`eventType` + `payload`).
- Telemetry broadcast to:
  - room: `integriguard`
  - channel: `telemetry-stream`
- Lightweight `agent_activity` events emitted for non-system agents to:
  - room: `integriguard`
  - channel: `dashboard-events`

### 🧪 Hardcoded Infrastructure
- Bootstrapped `science` room with workflow channels:
  - `general, explore, hypothesize, design, execute, interpret, share`
- Channel metadata with `created_at`, `created_by`, `type`, `hardcoded`.

### 📈 Monitoring & Logging
- Periodic stats logging (clients, rooms, total messages).
- Detailed routing, command, and error logs.

---

## Getting Started (Very Rough)

```bash
python websocket_bus.py --host localhost --port 8765 --telemetry-port 8766
