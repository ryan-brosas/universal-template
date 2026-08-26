<!-- capsule-v2 -->
# MVCC commit coordinator — how do the MVCC log and the pager WAL stay from interleaving their commits?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** With two durability pipelines (logical log for MVCC, pager WAL for B-tree), what serializes their critical sections?

## One shared TursoRwLock handed to every commit state machine
**Path/Symbol:** `core/mvcc/database/mod.rs:1528-1539` (`struct CommitCoordinator { pager_commit_lock: Arc<TursoRwLock> }`), consumed by checkpoint machine (`checkpoint_state_machine.rs:19` imports `TursoRwLock`; BeginPagerTxn state acquires).
**Signature:** `CommitCoordinator::new()` mints ONE lock per database; every `CommitStateMachine`/`CheckpointStateMachine` receives clones — writer exclusivity across both planes derives from holding it.
**Data Shape:** `Arc<TursoRwLock>` (turso's own rwlock, not std) so IO-yielding waits integrate with the completion model; no lock ordering hazards because there is exactly ONE cross-plane edge.

### Decisive source
```rust
// mod.rs:1529-1531 — the entire coordination surface:
struct CommitCoordinator {
    pager_commit_lock: Arc<TursoRwLock>,
}
// mod.rs:1464-1466 — its planned obsolescence, honestly noted:
// TODO: if and when we transform this code to async we won't be needing this
// explicit state machine nor the mutex
```
Why a dedicated coordinator rather than ad-hoc locking: the logical-log append (MVCC commit record) and the pager's own commit (WriteRow/BeginPagerTxn states) must never interleave, or recovery could pair an MVCC replay with a half-applied B-tree state. One RwLock makes that interleaving unrepresentable. The TODO comment doubles as design documentation: in a fully async runtime the yield-based machines would replace explicit mutual exclusion.

**Flow:** MVCC commit reaches log-append → holds coordinator write side → pager txn (checkpoint path) takes same lock → serialized → released.
**Invariant:** exactly one coordinator per database; acquire order fixed (MVCC plane before pager plane); nothing else may serialize these planes.
**Probe:** forced-yield checkpoints around BeforePagerCommit exercise the handoff; restart tests assert log/WAL agreement.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "CommitCoordinator pager_commit_lock TursoRwLock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt a single named coordinator object when two persistence layers must serialize; resist adding a second. Omit if your engine has one durability pipeline.
