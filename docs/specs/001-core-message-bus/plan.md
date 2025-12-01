# Implementation Plan: ArqonBus v1.0 Core Message Bus

**Branch**: `001-core-message-bus` | **Date**: 2025-11-30 | **Spec**: [Link to spec.md](spec.md)
**Input**: Feature specification from `/specs/001-core-message-bus/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement ArqonBus v1.0 as a structured WebSocket message bus with rooms, channels, built-in commands, optional Redis Streams persistence, and comprehensive telemetry. The system follows a layered architecture with Transport, Routing, Command, Persistence, Telemetry, Configuration, and Logging layers. Core features include strict message envelope validation, 9 built-in administrative commands, dual persistence modes (in-memory and Redis Streams), real-time telemetry broadcasting, and HTTP endpoints for health monitoring and metrics collection.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: websockets (async WebSocket server), aiohttp or built-in http.server (HTTP endpoints), redis-py or aioredis (Redis Streams), pydantic or dataclasses (message envelope), collections (ring buffer), pytest (testing)  
**Storage**: In-memory FIFO ring buffer (default), Redis Streams (optional)  
**Testing**: pytest with unit, integration, and contract test suites  
**Target Platform**: Linux server environments with Python 3.11+ runtime  
**Project Type**: Single server application (infrastructure component)  
**Performance Goals**: Handle 5,000 concurrent WebSocket connections, p99 message routing under 50ms, 100% reliability with Redis persistence, 100ms command response time, 99.9% HTTP endpoint availability  
**Constraints**: Memory-only mode when Redis unavailable, strict message envelope validation, graceful degradation on failures, protocol backward compatibility, minimum dependencies principle  
**Scale/Scope**: 10,000+ concurrent users, hundreds of rooms/channels, enterprise deployment scenarios

## Constitution Check

**GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.**

✅ **Layered Design (Principle II)**: Architecture implements clear transport, routing, command, storage, telemetry, configuration, and logging layers as specified  
✅ **Stateless Where Possible (Principle II)**: Per-process state minimized, persistent state delegated to Redis or defined storage  
✅ **Config over Code (Principle II)**: All operational settings via environment variables, no hard-coded values in core logic  
✅ **Minimal Dependencies (Principle II)**: Uses standard library components and well-understood libraries (websockets, aiohttp, redis-py)  
✅ **Public Protocol First (Principle II)**: Strict message envelope serves as public API with versioning requirements  
✅ **TDD Approach (Principle III)**: Comprehensive testing strategy includes unit, integration, and contract tests  
✅ **Test Coverage (Principle III)**: All public behaviors, commands, routing logic, and integrations covered  
✅ **Quality Gates (Principle III)**: No features without tests, protocol changes require documentation updates  
✅ **Spec-Driven Workflow (Principle IV)**: Uses Spec Kit for requirements, planning, and task breakdown  
✅ **Incremental Changes (Principle IV)**: Implementation ordered from core infrastructure to advanced features  
✅ **Python 3.11+ Style (Principle V)**: Type hints, small focused functions, clear separation of concerns  
✅ **Error Handling (Principle V)**: Fail loudly on programmer errors, gracefully on external failures  
✅ **Structured Logging (Principle V)**: Consistent logging with context (client_id, room, channel, command)  
✅ **Backwards Compatibility (Principle V)**: Protocol versioning and additive changes for v1.0+  
✅ **Metrics and Telemetry (Principle VI)**: Core metrics tracking, structured telemetry broadcasting  
✅ **Graceful Degradation (Principle VI)**: Redis failures don't crash main bus, telemetry failures isolated  
✅ **Environment Configuration (Principle VI)**: All settings from env vars or config files  
✅ **Documentation (Principle VII)**: README, protocol specs, configuration docs, SDK examples planned  

**RESULT**: ✅ All constitution gates PASS - no violations identified

## Project Structure

### Documentation (this feature)

```text
specs/001-core-message-bus/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
arqonbus/
├── __init__.py
├── config.py
├── server.py
├── transport/
│   ├── websocket_bus.py
│   ├── telemetry_server.py
│   └── http_server.py
├── routing/
│   ├── rooms.py
│   ├── channels.py
│   └── router.py
├── commands/
│   ├── base.py
│   ├── builtin.py
│   └── executor.py
├── storage/
│   ├── interface.py
│   ├── memory.py
│   └── redis_streams.py
├── telemetry/
│   ├── emitter.py
│   └── handlers.py
├── protocol/
│   ├── envelope.py
│   ├── validator.py
│   └── ids.py
└── utils/
    ├── logging.py
    ├── timestamps.py
    └── errors.py

tests/
├── unit/
├── integration/
└── contract/

docs/
└── spec/
```

**Structure Decision**: Single project structure with clear modular organization. Transport layer handles WebSocket and HTTP connections. Routing layer manages rooms, channels, and message delivery. Command layer processes administrative functions. Storage layer provides pluggable persistence. Telemetry layer handles monitoring and activity events. Protocol layer enforces strict message envelope validation. Utility modules provide shared functionality.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations identified - all gates passed successfully.

## Implementation Order (High-Level)

1. Core config loader and environment validation
2. Message envelope + validator implementation  
3. Transport layer (WebSockets and HTTP servers)
4. Client registry and connection management
5. Rooms and channels management system
6. Message routing logic and delivery
7. Command executor and dispatch system
8. Built-in commands implementation (9 commands)
9. Storage layer (in-memory mode)
10. Storage layer (Redis Streams adapter)
11. Telemetry server and event broadcasting
12. HTTP endpoints (/health, /version, /metrics)
13. Metrics collection and Prometheus formatting
14. Structured logging and monitoring
15. Integration tests and validation
16. Documentation and SDK examples