---
description: "Task list for ArqonBus v1.0 Core Message Bus implementation"
---

# Tasks: ArqonBus v1.0 Core Message Bus

**Input**: Design documents from `/specs/001-core-message-bus/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), data-model.md, contracts/, quickstart.md  

**Tests**: TDD approach - tests included for all major functionality  
**Organization**: Tasks grouped by user story to enable independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/arqonbus/`, `tests/` at repository root
- Paths shown below follow the project structure from plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create arqonbus package structure with subdirectories: config/, protocol/, transport/, routing/, commands/, storage/, telemetry/, utils/
- [X] T002 Initialize pyproject.toml with dependencies: websockets, aiohttp, redis-py, pydantic, pytest, black, isort, mypy
- [X] T003 [P] Create all __init__.py files for proper Python package structure
- [X] T004 Set up basic test structure with unit/, integration/, contract/ directories

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Implement configuration loader in src/arqonbus/config.py with environment variable parsing and validation
- [X] T006 [P] Create Envelope dataclass in src/arqonbus/protocol/envelope.py with all required fields
- [X] T007 [P] Implement envelope validation, parsing, and JSON serialization methods
- [X] T008 [P] Create message ID generator in src/arqonbus/protocol/ids.py with arq_ prefix
- [X] T009 Implement storage interface in src/arqonbus/storage/interface.py (append, history methods)
- [X] T010 Create abstract base classes and proper interfaces for all storage backends

**Checkpoint**: Foundation ready - message envelope, configuration, and storage interfaces complete

---

## Phase 3: User Story 1 - Real-Time Message Bus Foundation (Priority: P1) 🎯 MVP

**Goal**: WebSocket server with room/channel routing and basic message delivery

**Independent Test**: Can be fully tested by starting server, connecting WebSocket clients, subscribing to rooms/channels, sending messages that are properly routed

### Tests for User Story 1 (TDD approach) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T011 [P] [US1] Test WebSocket connection lifecycle (covered by tests/integration/test_epoch1_gate.py + tests/integration/test_hello_world_sdk_e2e.py)
- [X] T012 [P] [US1] Test room and channel creation/management (covered by tests/unit/test_websocket_bus_processing.py + tests/integration/test_e2e_messaging.py)
- [X] T013 [P] [US1] Test message routing and delivery (covered by tests/integration/test_e2e_messaging.py + tests/integration/test_epoch1_gate.py)
- [X] T014 [P] [US1] Test client subscription management (covered by tests/integration/test_hello_world_sdk_e2e.py + tests/integration/test_operator_cron_e2e.py)

### Implementation for User Story 1

- [X] T015 [P] [US1] Implement WebSocket server in src/arqonbus/transport/websocket_bus.py
- [X] T016 [P] [US1] Create room manager in src/arqonbus/routing/rooms.py
- [X] T017 [P] [US1] Create channel manager in src/arqonbus/routing/channels.py  
- [X] T018 [P] [US1] Implement routing logic in src/arqonbus/routing/router.py
- [X] T019 [P] [US1] Create client registry in src/arqonbus/routing/client_registry.py
- [X] T020 [US1] Implement in-memory storage backend in src/arqonbus/storage/memory.py
- [X] T021 [US1] Create main server orchestration in src/arqonbus/server.py
- [X] T022 [US1] Add structured logging utilities in src/arqonbus/utils/logging.py

**Checkpoint**: User Story 1 complete - basic WebSocket messaging with room/channel routing works independently

---

## Phase 4: User Story 2 - Structured Protocol and Built-in Commands (Priority: P2)

**Goal**: Versioned message format validation and administrative command system

**Independent Test**: Can be fully tested by sending messages with required envelope format, issuing built-in commands, verifying responses match protocol specifications

### Tests for User Story 2 (TDD approach) ⚠️

- [X] T023 [P] [US2] Test message envelope validation (covered by tests/regression/test_envelope_timestamp_z_regression.py + tests/integration/test_e2e_messaging.py)
- [X] T024 [P] [US2] Test built-in/command flows (covered by tests/integration/test_e2e_messaging.py + tests/unit/test_standard_operator_pack.py + tests/unit/test_command_authorization.py)
- [X] T025 [P] [US2] Test command authorization and permissions (covered by tests/unit/test_command_authorization.py + tests/unit/test_http_admin_endpoints.py)
- [X] T026 [P] [US2] Test command response formatting/protocol behavior (covered by tests/integration/test_e2e_messaging.py + tests/integration/test_tier_omega_lane_e2e.py)

### Implementation for User Story 2

- [X] T027 [P] [US2] Implement command executor in src/arqonbus/commands/executor.py
- [X] T028 [P] [US2] Create command base classes in src/arqonbus/commands/base.py
- [X] T029 [P] [US2] Implement all built-in commands in src/arqonbus/commands/builtin.py (status, create_channel, delete_channel, join_channel, leave_channel, list_channels, channel_info, ping, history)
- [X] T030 [P] [US2] Add message validation in src/arqonbus/protocol/validator.py
- [X] T031 [US2] Implement command-specific validation and authorization logic
- [X] T032 [US2] Add metrics collection for commands in src/arqonbus/utils/metrics.py

**Checkpoint**: User Story 2 complete - protocol validation and all administrative commands work independently

---

## Phase 5: User Story 3 - Persistence and Observability (Priority: P3)

**Goal**: Optional Redis Streams persistence, telemetry system, and HTTP monitoring endpoints

**Independent Test**: Can be fully tested by configuring Redis Streams, sending messages, checking history retrieval, monitoring telemetry streams, verifying HTTP endpoints

### Tests for User Story 3 (TDD approach) ⚠️

- [X] T033 [P] [US3] Test Redis Streams integration in tests/integration/test_redis_storage.py
- [X] T034 [P] [US3] Test telemetry event broadcasting in tests/integration/test_telemetry.py
- [X] T035 [P] [US3] Test HTTP endpoints (covered by tests/unit/test_http_monitoring_endpoints.py + tests/integration/test_cli_http.py)
- [X] T036 [P] [US3] Test metrics/monitoring format and counters (covered by tests/unit/test_http_monitoring_endpoints.py + tests/integration/test_telemetry.py)

### Implementation for User Story 3

- [X] T037 [P] [US3] Implement Redis Streams storage backend in src/arqonbus/storage/redis_streams.py
- [X] T038 [P] [US3] Create telemetry WebSocket server in src/arqonbus/telemetry/server.py
- [X] T039 [P] [US3] Implement telemetry event handlers in src/arqonbus/telemetry/handlers.py
- [X] T040 [P] [US3] Create HTTP server in src/arqonbus/transport/http_server.py
- [X] T041 [P] [US3] Implement telemetry emitter in src/arqonbus/telemetry/emitter.py
- [X] T042 [P] [US3] Add Prometheus metrics exporter in src/arqonbus/utils/prometheus.py
- [X] T043 [US3] Implement agent activity event emission
- [X] T044 [US3] Add graceful degradation for Redis failures

**Checkpoint**: User Story 3 complete - persistence, telemetry, and monitoring work independently

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Integration testing, documentation, and performance optimization

- [X] T045 [P] End-to-end integration tests in tests/integration/test_e2e_messaging.py
- [X] T046 [P] Performance and load testing scenarios (tests/performance/test_load_testing.py + tests/performance/test_casil_benchmarks.py)
- [X] T047 [P] Documentation updates in docs/ and README.md
- [X] T048 [P] SDK example implementation (Python) in examples/python/hello_world_bot.py + src/arqonbus/sdk/client.py
- [X] T049 Code cleanup and refactoring across all modules (reflected by vNext stabilization phases and branch commits)
- [X] T050 Security hardening and error handling improvements (JWT edge auth, socket-gated suites, CASIL command hardening)
- [X] T051 Final validation against all success criteria from spec.md (tracked in docs/ArqonBus/vnext_status.md)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Protocol layer before transport layer
- Transport layer before routing layer  
- Routing layer before command layer
- Storage layer supports all user stories
- User story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Protocol components marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (TDD approach):
Task: "Test WebSocket connection lifecycle in tests/integration/test_connection_lifecycle.py"
Task: "Test room and channel creation/management in tests/unit/test_routing.py"
Task: "Test message routing and delivery in tests/integration/test_message_routing.py"

# Launch all protocol components for User Story 1 together:
Task: "Create Envelope dataclass in src/arqonbus/protocol/envelope.py"
Task: "Implement message ID generator in src/arqonbus/protocol/ids.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (P1)
   - Developer B: User Story 2 (P2)  
   - Developer C: User Story 3 (P3)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD approach)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Total tasks: 51 (11 Setup/Foundational, 20 User Story 1, 12 User Story 2, 12 User Story 3, 6 Polish)