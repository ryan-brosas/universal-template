<!-- capsule-v2 -->
# Yield-based async IO — how does a single-threaded engine issue disk IO without blocking its executor?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** What is the completion/yield contract that lets every layer (btree, pager, WAL, MVCC) stay resumable?

## IOResult::IO + Completion + io_yield_one!
**Path/Symbol:** `core/types.rs:IOResult` / `IOCompletions`, `core/io/mod.rs:Completion` (backend-agnostic), `core/io/completions.rs` (:1-1318), macro `io_yield_one!` (imported at logical_log.rs:241), `core/io/memory_yield.rs` (649L deterministic yield injection).
**Signature:** fallible ops return `Result<IOResult<T>>`; `IOResult::IO(IOCompletions)` carries completions to the driver, which resumes the state machine on completion; `io.block(|| …)` is the sanctioned blocking island for genuinely synchronous segments.
**Data Shape:** Completion wraps one backend op (pwrite/pread/sync) with a callback; groups (`CompletionGroup`) fan-in multiple ops.

### Decisive source
```text
// checkpoint_state_machine.rs:311-315 — the contract restated at the top user:
// "Pure IOResult plumbing — every cursor op yields up to the caller on page
//  IO, so a step() call from inside the checkpoint state machine can propagate
//  a yield upward without ever blocking the executor."
// logical_log.rs spill-path doc (wal.rs legacy): "Must NOT block for
//  durability here… A synchronous drain would deadlock a caller that drives
//  I/O from a single-threaded event loop."
```

The pattern's price and payoff are visible in the parsers: every re-entrant machine (BuildSharedWal chunk loop, StreamingLogicalLogReader phases, CheckpointStateMachine states, SeqCompactDriver phases) carries explicit progress state so a yield can land between ANY two steps. Deterministic testing comes from yield injectors (`arm_spill_yield_on_read`, `inject_transition_yield!` with named yield points like `CheckpointYieldPoint::BeforePagerCommit`) plus failure injectors — reproducible crash/timing matrices without real IO races.

**Flow:** op needs a page → issue pread Completion → return IO up the stack → executor drains → callback resumes exactly where progress was checkpointed.
**Invariant:** no durability-blocking call inside async paths; every cross-yield structure must own its resume state explicitly.
**Probe:** `process_overflow_read_survives_spill_yield_from_next_chain_read` (~11950); `test_integrity_check_after_checkpoint_io_yield_then_post_durable_failure_uses_user_apis` (tests.rs:3690); yield-point enums in checkpoint_state_machine.rs:111-134.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "IOResult Completion io_yield memory_yield", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt IOResult-style yields + named yield points for any single-threaded async engine; adapt to your executor (tokio/epoll); omit Windows IOCP variants unless porting cross-platform. Coverage caveat: capsule documents the pattern via its consumers; io/mod.rs backend internals (io_uring specifics) remain omit-with-reason for this pass.
