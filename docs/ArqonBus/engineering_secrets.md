# Engineering Secrets: Performance Sharp Edges

> **Critical Performance Insights** — The 100µs Budget Killers

---

A few sharp edges to watch (these are the usual places systems like this silently lose their microsecond budget):

### 1) NATS latency is real, but tails are the enemy
“~80µs RTT on localhost” is plausible with Core NATS and a clean setup — but the question is always: **p50 vs p95 vs p99 vs p99.9**, and what happens under contention (other subjects, bursts, fanout).

If you want the claim to be bulletproof, treat “NATS RTT” as a distribution, not a number, and lock down:
*   **CPU pinning** for NATS + Shield + op_reflex (and avoid cross-NUMA chatter on dual Xeon)
*   **fixed message sizes** (protobuf frames stay small and predictable)
*   **no accidental synchronous request/reply** patterns where async pub/sub would do

### 2) Protobuf is fast, but “nanosecond-scale” only holds in a narrow sense
Protobuf can be extremely fast, but the wall-clock cost comes from:
*   memory movement (copying bytes)
*   cache misses
*   allocator usage if you’re not careful with arenas / reuse

The win is: protobuf keeps you in “tight, predictable binary” territory. Just make sure you’re actually doing:
*   **preallocated buffers / reuse**
*   no “build new Vec every message”
*   avoid string allocations in the hot path (IDs as integers or interned)

### 3) “Zero allocation hot path” is mostly an allocator + ownership discipline problem
You already know this, but it’s worth stating bluntly: most “we lost 3ms” incidents come from one of:
*   a hidden allocation in a logging path
*   an accidental clone/copy of payload buffers
*   an error path that allocates (and gets hit more than you expect)

**Best practice**: keep a hard rule that any hot-path function must be provably allocation-free (and tested).

### 4) Tier 0 WASM is excellent — but measure the runtime overhead
WASM can be “almost a function call,” but only if:
*   you’re using a lightweight runtime
*   you’re not doing host<->guest boundary crossings per tiny predicate
*   you avoid dynamic memory inside WASM for common checks

If CASIL is a set of small, composable predicates, you want: **one call into WASM per sentence/event**, not 20 calls per sentence/event.

### 5) Your numbers add up — now prove them end-to-end
The breakdown (NATS ~80µs + lookup ~50µs → ~130–150µs) is internally consistent. To make it defensible, benchmark in three layers:
1.  **Microbench**: Reflex lookup alone (graph/bloom/logic)
2.  **Bus bench**: NATS request/reply latency (same box, pinned cores)
3.  **End-to-end bench**: Shield → (Tier0 optional) → NATS → op_reflex → decision → Shield emit

And report: **p50, p95, p99, p99.9** under burst (e.g., 10k msg/s) and mixed traffic.

### 6) The “speed moat” story is strongest if you formalize the contract lanes
What you’ve described is effectively:
*   **Tier 0**: must-run invariants (in-process)
*   **Tier 1**: microsecond audit (binary spine + RAM lookup)
*   **Tier 2**: millisecond novelty (embedder / deeper retrieval)

That’s a clean narrative and it prevents “someone later routes everything through the slow lane.”
