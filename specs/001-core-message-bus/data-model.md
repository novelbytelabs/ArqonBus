# Data Model: ArqonBus v1.0 Core Message Bus

**Feature**: 001-core-message-bus  
**Created**: 2025-11-30  
**Source**: [Feature Specification](spec.md)

## Overview

The ArqonBus data model consists of five core entities that represent the structured message bus architecture. All entities are designed for high-performance, real-time operations with optional persistence through configurable storage backends.

## Core Entities

### 1. Message

**Purpose**: Structured data unit transmitted through the message bus  
**Persistence**: Optional (configurable storage backend)  
**Validation**: Required - strict envelope schema validation  

**Fields**:
- `version` (string, required): Protocol version identifier (always "1.0")
- `id` (string, required): Unique message identifier prefixed with "arq_"
- `type` (string, required): Message classification (event, system, command, private, command_response, telemetry)
- `room` (string, required): Target room namespace for routing
- `channel` (string, required): Target channel within room for precise routing
- `from` (string, required): Sender client_id for message attribution
- `timestamp` (ISO8601 string, required): Server-generated message timestamp
- `payload` (object, required): Message content data
- `metadata` (object, optional): Additional message metadata

**Validation Rules**:
- All required fields must be present and non-null
- ID must start with "arq_" prefix
- Version must be "1.0" for protocol compliance
- Timestamp must be valid ISO8601 format
- Room and channel must follow naming conventions

**State Transitions**:
- Created → Validated → Routed → Delivered/Expired
- Invalid messages rejected before routing

---

### 2. Client

**Purpose**: Connected entity participating in message bus communication  
**Persistence**: Runtime state (not persisted)  
**Lifecycle**: Created on connection, destroyed on disconnection  

**Fields**:
- `client_id` (string, required): Unique identifier for the client
- `client_type` (string, required): Classification (human, ai-agent, dashboard, service)
- `screen_name` (string, optional): Display name for human-readable identification
- `avatar` (string, optional): Avatar URL or identifier for visual representation
- `personality` (string, optional): Behavioral characteristics for AI agents
- `connected_at` (timestamp, required): Connection establishment time
- `last_activity` (timestamp, required): Most recent activity timestamp
- `subscriptions` (array, required): List of room:channel subscriptions

**Validation Rules**:
- client_id must be unique across all active connections
- client_type must be from approved classification set
- subscriptions must be valid room:channel format
- All timestamps must be valid ISO8601 format

**State Transitions**:
- Connecting → Connected → Active → Disconnected → Destroyed

---

### 3. Room

**Purpose**: Logical namespace for organizing and isolating message traffic  
**Persistence**: Runtime state with optional configuration persistence  
**Creation**: Dynamic (on-demand) or pre-configured  

**Fields**:
- `name` (string, required): Unique room identifier
- `channels` (array, required): List of active channels within room
- `created_at` (timestamp, required): Room creation timestamp
- `created_by` (string, optional): Client who created the room (if applicable)
- `type` (string, required): Room classification (system, user, dynamic)
- `config` (object, optional): Room-specific configuration settings
- `participant_count` (integer, computed): Current active participant count

**Validation Rules**:
- Room name must be unique within the system
- Room names must follow naming conventions
- System rooms cannot be deleted through normal operations
- User-created rooms subject to naming restrictions

**State Transitions**:
- Creating → Active → Paused → Deleted
- System rooms: Creating → Active (permanent)

---

### 4. Channel

**Purpose**: Sub-stream within a room for precise message routing  
**Persistence**: Runtime state with optional history persistence  
**Creation**: Dynamic (on-demand) or admin-created  

**Fields**:
- `name` (string, required): Channel identifier within room
- `room` (string, required): Parent room name
- `participants` (array, required): List of client_ids subscribed to channel
- `created_at` (timestamp, required): Channel creation timestamp
- `created_by` (string, optional): Client who created the channel
- `type` (string, required): Channel classification (general, private, system, pm)
- `metadata` (object, optional): Channel-specific metadata
- `hardcoded` (boolean, required): Whether channel is system-defined
- `auto_created` (boolean, required): Whether channel was auto-generated

**Validation Rules**:
- Channel name unique within room scope
- Cannot delete hardcoded channels
- Cannot delete channels with active participants
- PM channels have special routing rules

**State Transitions**:
- Creating → Active → Empty → Deleted
- PM channels: Creating → Active → Private

---

### 5. Command

**Purpose**: Administrative message processed by server for system operations  
**Persistence**: Runtime processing (not persisted)  
**Authorization**: Subject to permission requirements  

**Fields**:
- `name` (string, required): Command identifier (status, create_channel, delete_channel, join_channel, leave_channel, list_channels, channel_info, ping, history)
- `parameters` (object, required): Command-specific parameters
- `requester` (string, required): Client issuing the command
- `timestamp` (timestamp, required): Command execution time
- `response_format` (string, required): Expected response structure
- `requires_admin` (boolean, required): Administrative privilege requirement
- `channel_scope` (string, optional): Target channel for channel-specific commands

**Validation Rules**:
- Command name must be from supported command set
- Admin commands require appropriate authorization
- Parameters must match command specification
- Some commands have rate limiting

**State Transitions**:
- Received → Validated → Authorized → Executed → Response Sent
- Invalid commands: Received → Rejected

---

## Relationships

### Message Relationships
- **Message → Client**: Belongs to `from` client
- **Message → Room**: Routed to `room`
- **Message → Channel**: Routed to `channel`
- **Message → Command**: Command messages processed through command system

### Client Relationships  
- **Client → Room**: Subscribes to multiple rooms
- **Client → Channel**: Subscribes to multiple channels
- **Client → Message**: Sends and receives messages

### Room-Channel Relationships
- **Room → Channel**: Contains multiple channels (one-to-many)
- **Channel → Room**: Belongs to single room (many-to-one)

### Command Relationships
- **Command → Room**: Some commands operate on specific rooms
- **Command → Channel**: Channel management commands target specific channels
- **Command → Client**: Executed on behalf of requesting client

---

## Validation Rules

### Cross-Entity Constraints
1. Client subscriptions must reference existing rooms and channels
2. Message routing must validate room and channel existence
3. Channel deletion requires empty participant list
4. Command execution must validate requester permissions
5. Room deletion requires all channels to be deleted first

### Data Integrity Rules
1. All timestamps must be in valid ISO8601 format
2. Unique identifiers (client_id, room name, channel name) must be enforced
3. Foreign key relationships must be maintained
4. Hardcoded system entities cannot be modified through user operations

### Performance Considerations
1. Message lookup optimized for high-throughput routing
2. Client subscription tracking optimized for quick membership queries
3. Room/channel discovery optimized for new participant joins
4. Command execution optimized for minimal latency

---

## Storage Requirements

### In-Memory Mode (Default)
- **Message History**: FIFO ring buffer (configurable size, default 500)
- **Client State**: Active connections only
- **Room/Channel State**: Runtime state with cleanup
- **Performance**: Sub-millisecond access times

### Redis Streams Mode (Optional)
- **Message History**: Persistent streams with configurable retention
- **Client State**: Session persistence across restarts
- **Room/Channel State**: Configuration persistence
- **Performance**: Redis-optimized queries with fallback to memory mode

### Configuration-Driven
- Storage backend selection via environment variables
- Persistence settings configurable per entity type
- Graceful degradation when persistence unavailable
- Clear separation between runtime and persistent state