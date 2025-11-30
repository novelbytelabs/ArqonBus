# ArqonBus

ArqonBus is a lightweight, structured WebSocket message bus with rooms, channels, and a simple JSON protocol. It gives your apps, services, and agents a clean way to talk to each other in real time, with optional Redis Streams durability.

Think: **organized real-time messaging** instead of raw ad-hoc WebSockets.

---

## Features

- 🧩 **Rooms & Channels**
  - `room:channel` addressing (e.g. `science:explore`)
  - Multiple channels per room, multiple rooms per client

- 📡 **Structured Messaging**
  - JSON messages with `type`, `room`, `channel`, `from`, `payload`, etc.
  - Supports normal events, system messages, commands, private messages

- 🧭 **Built-in Commands**
  - `status`, `join_channel`, `leave_channel`
  - `list_channels`, `channel_info`, `history`, `ping`
  - `create_channel` / `delete_channel` (admin-only)

- 🧠 **Client Awareness**
  - Tracks client id, type, joined channels, screen name, avatar
  - Join/leave notifications as system events

- 📊 **Telemetry & Activity Stream**
  - Separate telemetry WebSocket endpoint
  - Agent activity events for dashboards and monitoring

- 🗂️ **Message History**
  - In-memory history out of the box
  - Designed for optional Redis Streams backing (Upstash-friendly)

---

## Quick Start

```bash
python websocket_bus.py --host 0.0.0.0 --port 8765 --telemetry-port 8766
```

Then connect a client (example in JavaScript):

```js
const ws = new WebSocket("ws://localhost:8765");

// 1) Initial auth / registration
ws.onopen = () => {
  ws.send(JSON.stringify({
    client_id: "my-client-1",
    client_type: "app",
    room: "science:explore",
    screen_name: "MyApp",
    avatar: null,
    personality: {}
  }));
};

// 2) Send a message into a room/channel
function sendMessage(text) {
  ws.send(JSON.stringify({
    type: "event",
    room: "science",
    channel: "explore",
    message: text
  }));
}

// 3) Listen for messages
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log("ArqonBus message:", msg);
};
```

---

## Message Shape (v0)

Typical message fields:

```json
{
  "type": "event | system | command | private | telemetry",
  "room": "science",
  "channel": "explore",
  "from": "client-id",
  "to": ["optional-target-client-ids"],
  "command": "status",
  "message": "optional free text",
  "payload": {},
  "timestamp": "2025-01-01T00:00:00Z"
}
```

(A more formal protocol spec will follow in v1.)

---

## Roadmap (High-Level)

* Optional **Redis Streams** for durable history and worker consumers
* **Auth & roles** for channel/command permissions
* Official **SDKs** (TypeScript, Python, etc.)
* Exportable **metrics & telemetry** (Prometheus/OpenTelemetry)
* Clustering & **multi-node ArqonBus** support

---

## Status

ArqonBus is currently **experimental / early stage** but already powers:

* Multi-room, multi-channel WebSocket communication
* Real-time agent / dashboard messaging
* Telemetry streams and activity indicators

Use it if you want a structured alternative to raw WebSockets, and you’re comfortable evolving with the project.

---