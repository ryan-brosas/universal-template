<!-- capsule-v2 -->
# LogicalClock — how does a timestamp source make "allocate ts" and "publish ts" atomic?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What interface must a logical clock expose so the commit protocol can close the TOCTOU window between choosing an end_ts and advertising it?

## Lock held across a callback, not returned-then-stored
**Path/Symbol:** `core/mvcc/clock.rs:9-24` (`trait LogicalClock`, doc contract), :26-60 (`MvccClock` + speculative-read rationale incl. turso#5198), `no_op` helper :3-7.
**Signature:** `fn get_timestamp<F: FnOnce(u64)>(&self, f: F) -> u64` — implementations hold their internal lock ACROSS `f`, so the timestamp is published (e.g. stored as `Preparing(ts)`) before any other caller can observe a timestamp. `fn reset(&self, ts: u64)` reseeds after recovery (monotonic from the log).
**Data Shape:** callback receives the freshly minted u64; `no_op` marks call sites (begin timestamps) that need no atomic side effect.

### Decisive source
```rust
// clock.rs:9-16 — the contract:
// Implementations that guard concurrent commit protocols (e.g.
// [`MvccClock`]) hold their internal lock across the `f` call, so
// that the timestamp is published (e.g. stored as `Preparing(ts)`)
// before any other caller can observe a timestamp.
// :52-58 — why speculation exists at all:
// > We need speculative reads, otherwise it's difficult to make
// > the MVCC model work without blocking. I made an attempt in
// > turso#5198 but this introduced a subtle bug which violated snapshot isolation.
```
Without atomicity, tx A could mint end_ts=10 and stall before storing Preparing(10); tx B mints 11 and validates against a world where A doesn't exist yet — breaking end_ts-ordering assumptions the dependency graph relies on ("edges go from higher end_ts to lower"). The begin path uses `get_timestamp(no_op)` because snapshot publication has its own critical section (see begin/rollback capsule); only commit needs the fused publish.

**Flow:** Commit state → `clock.get_timestamp(|ts| tx.store_state(Preparing(ts)))` → lock released → next committer's validation sees either Preparing(ts) or nothing-before-it, never a gap.
**Invariant:** any timestamp whose value another transaction can observe in ordering decisions MUST be published under the same critical section that mints it; read-only allocations are exempt.
**Probe:** tests.rs restart probe asserts clock reseeds monotonically from the log (`reset(max(persistent_tx_ts_max, max_replayed_commit_ts) + 1)` per logical_log.rs recovery docs); hermitage suite pins observable isolation that depends on the ordering.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "LogicalClock get_timestamp MvccClock no_op", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt callback-fused timestamp publication for any optimistic concurrency scheme with observable timestamps; adapt to async by passing a closure that stages the write. Omit `reset` only if your clock is wall-derived and monotonic by construction.
