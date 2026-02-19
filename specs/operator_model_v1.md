# ArqonBus Operator Model v1 Specification

## 1. Core Concepts: Recursive Self-Improvement (RSI)

We are building a **System Synthesis** engine. The Operator is not just a fixed model improving its outputs (Software 2.0); it is an agent capable of modifying its own source code, tools, and architecture.

### 1.1 The RSI-SAM Loop
- **State ($S_t$)**: The current System Snapshot (Source Code, Runtime Memory, Global Truth).
- **Model ($M_t$)**: The Operator's current logic (defined by $S_t$).
- **Action ($A_t$)**: The **Improvement Operator**. A specific, mathematically defined operation on the Source Code or System State (e.g., `Patch(File)`, `AddConstraint(Test)`, `Tune(Param)`).
- **Witness ($W_t$)**: Cryptographic proof of the transition effectiveness (audit trail).
- **Update ($U$)**: The application of $A_t$ to $S_t$.

$$ A_t = M_t(S_t) $$
$$ S_{t+1} = \text{IntegriGuard}(S_t, A_t) $$

> **Note**: IntegriGuard acts as the "Selection Function" in this evolutionary loop, rejecting $S_{t+1}$ if it violates constitutional invariants, preventing "capabilities overhang" or regression.

### 1.2 Defense Against Entropy (The Arqon Answer)
We address the "Entropy Wall" (model collapse from closed-loop self-reflection) through **Grounded Multi-Agent Loops**.

1.  **External Grounding (Real World Priors)**:
    - Operators do not hallucinate improvement; they must **prove** it.
    - **Lattice Lane 1**: Hash-Forward Witnessing binds outputs to immutable input configurations.
    - **Lane 3**: Input Binding ensures every mutation is causally linked to a specific external Trigger.

2.  **Multi-Agent Orchestration**:
    - ArqonBus is the "Nervous System" connecting specialized agents (Coder, Critic, Auditor).
    - **Adversarial Review**: The "Critic" agent (IntegriGuard) is distinct from the "Actor" (Coder).
    - **Regression Shield**: No mutation is committed without passing the `tripwire` suite, ensuring $S_{t+1}$ is strictly better (or at least no worse) than $S_t$.

3.  **Algorithmic Mutation with Guardrails**:
    - The Operator uses tools (compilers, linters, tests) to "ground" its hallucinations in executable reality.
    - If code doesn't compile or tests fail, the "Entropy Guard" (IntegriGuard) rejects the Action.

### 1.3 Governance Alignment (The SI $\to$ RSI Bridge)
The critique is correct: Arqon v1 is SI (Autopoietic). Arqon vNext is RSI, enabled by mapping the SAM loop to the **Superpower Stack**:

1.  **Tier $\Omega$ (Discovery)**: The **Operator ($M_t$)**. It explores the search space and generates candidate Improvement Operators ($A_t$).
2.  **Tier 2 (Adaptive Engine)**: **IntegriGuard**. It validates $A_t$ against the Constitution and Regression Shield. It cannot mutate state, only approve/reject.
3.  **Tier 1 (Safe Executor)**: The **Bus/System**. It serves as the sole writer, applying the validated $A_t$ to produce $S_{t+1}$.

> **Resolution**: We do not choose between SI and RSI. We implement **Governed RSI**—using the SI architecture to safely contain the RSI loop.

## 2. Operator Lifecycle

Operators must register with the **Operator Registry** to receive tasks.

### 2.1 Registration (`operator.join`)
- **Handshake**: WebSocket connection with `client_type="operator"`.
- **Capabilities**: Operator declares supported `capabilities` (e.g., `["truth.verify", "code.generation"]`).
- **Group**: Operator joins a Load Balancing Group (e.g., `truth_workers`).

### 2.2 Heartbeat & Liveness
- **Ping/Pong**: Standard WebSocket heartbeats.
- **Lease**: Operators hold a lease on their tasks; failure to heartbeat releases tasks to other group members.

## 3. Task Dispatch Subsystem

Tasks are routed to operators based on **Capabilities** and **Availability**.

### 3.1 Dispatch Logic
1.  **Direct**: `send_to(client_id)` (Targeted).
2.  **Broadcast**: `publish(room)` (Pub/Sub).
3.  **Balanced**: `enqueue(group, task)` (Queue-based).
    - Uses Redis Streams Consumer Groups (`XADD`, `XREADGROUP`).
    - Guarantees **At-Least-Once** delivery.

### 3.2 Task Protocol
- **Submit**: Client sends `command` message.
- **Route**: Bus determines target Group based on Command Type.
- **Push**: Bus pushes task to Operator via WebSocket.
- **Ack**: Operator sends `ack` after processing.
- **Result**: Operator sends `result` message back to Bus (which routes to original Client).

### 3.3 Parallel Speculation (Evolutionary RSI)
To prevent "local optima" and "model collapse," we support **Population-Based Evolution**:

-   **Dispatch Strategy**: `dispatch_strategy="competing"`
-   **Mechanism**:
    1.  Bus broadcasts the same Improvement Task to $N$ Operators in a Group.
    2.  Operators generate divergent candidates ($A_{t,1}, A_{t,2}, \dots, A_{t,N}$) via high temperature or diverse prompts.
    3.  **Tier 2 Filter**: IntegriGuard provides the **Selection Function**. It validates all candidates.
    4.  **Winner Takes All**: The System applies the *best* valid candidate (e.g., passed tests + lowest latency).

> **Result**: Entropy drives exploration (Generation), but the Bus enforces order (Selection).

## 4. SAM Interface Definition

```python
class Operator(ABC):
    @abstractmethod
    async def process(self, state: State) -> Action:
        """Core SAM loop."""
        pass

    async def on_task(self, task: Envelope):
        """Adapter from Bus Task to SAM State."""
        state = self.hydrate_state(task)
        action = await self.process(state)
        await self.emit_action(action)
```

## 5. Migration Strategy

- **Legacy**: `LegacyRedisAdapter` (current IntegriGuard workers).
- **Bridge**: `ArqonBusQueueAdapter` (Phase 2 output).
- **Native**: `NativeOperator` (Phase 40 target).

We will verify `NativeOperator` compliance using the `ArqonBus` test suite.
