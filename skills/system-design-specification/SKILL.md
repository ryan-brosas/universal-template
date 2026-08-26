---
name: system-design-specification
description: "Use when authoring formal, crash-proof system design documents and architectural specifications: scope fences and non-goals, 4-part state ontologies, mathematical invariants, provisioned ID pre-allocation, ASCII trace calculus (E/R/L/G/H/X), exhaustive crash matrices, and deterministic boundary testing."
disable-model-invocation: true
---

# System Design Specification: Formal Architecture & Design Doc Authoring

## Use this for
Author comprehensive, ambiguity-free architectural design documents for complex distributed, concurrent, or asynchronous software systems (modeled on the formal specification calculus of Pi's `harness-v2.md`).

A great design doc is not persuasive prose; it is a **constructive proof** that the system is correct, crash-proof, and deterministically testable before writing production code.

## The 8-Phase Design Specification Calculus

### Phase 1: Explicit Compatibility & Non-Goals
Define the scope fence before describing features:
- **Migration & backward compatibility**: Exactly which formats/APIs stay intact and how migrations execute.
- **Explicit Non-Goals**: Enumerate capabilities the design deliberately refuses to solve to keep boundaries crisp.

### Phase 2: 4-Part State Ontology
Strictly partition domain state into:
1. **Passive Shared Data (Tree/DAG)**: Immutable conversation/event history linked by parent pointers.
2. **Active Execution Lines (Lanes/Threads)**: Pointers to leaf nodes owning serialization and queues.
3. **Write-Ahead Operation Logs (WAL)**: Flat execution records (intent, attempts, cost) used purely for recovery.
4. **Global Facts**: Key-value settings with latest-write-wins semantics.

### Phase 3: Mathematical Invariants
Declare 5–10 unbreakable mathematical laws governing state transitions (e.g. "Tree nodes are immutable", "At most one open operation per lane", "WAL deletion preserves full conversation validity").

### Phase 4: Intent-First Provisioned IDs
For all external or asynchronous side effects, pre-allocate the target entry UUID and persist an intent record to storage *before* initiating the effect.

### Phase 5: ASCII Trace Calculus
Specify all async interleaving and execution flows using the 6-letter trace grammar:
- `E`: Entry append to shared DAG
- `R`: Record append to local WAL log
- `L`: Pointer / lane navigation
- `G`: Global fact write
- `H`: Hook / interceptor awaited
- `X`: Crash site / fault injection point

### Phase 6: Exhaustive Crash-Site Proof Matrix
Identify every fault site $X_1 \dots X_n$ across effects, and map each to the exact durable state on disk and the deterministic recovery algorithm.

### Phase 7: Algebraic Type-Level Contracts
Provide zero-dependency, lightweight type definitions (`Result<T, E>`, `TaggedError`, discriminating unions) that eliminate thrown runtime exceptions across architectural boundaries.

### Phase 8: Deterministic Boundary Testing Engine
Specify how long-running loops park at effect boundaries in test mode (`drive: "manual"`, `peekAction()`, `executeAction()`) for 100% deterministic test execution.

## Load the matching reference
- `references/trace-calculus-grammar.md` — 6-letter trace grammar ($E, R, L, G, H, X$) for unambiguous async sequence notation.
- `references/crash-site-matrices.md` — how to construct exhaustive crash $\to$ durable state $\to$ recovery action proof tables.
- `references/state-ontology-and-invariants.md` — separating passive data DAGs from active execution lines and formulating hard invariants.
- `references/provisioned-id-protocols.md` — intent pre-allocation protocols for crash-proof side effects without 2PC.
