<!-- capsule-v2 -->
# Yield-point testing — how do you deterministically test async state machines that usually only fail under real I/O races?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What injection architecture makes "yield mid-commit" a reproducible test input instead of a flaky race?

## Enumerated yield points + keyed hooks + transition-failure injection, compiled out in prod
**Path/Symbol:** `core/mvcc/yield_points.rs` (101L: `inject_transition_yield`, `inject_transition_failure`), `core/mvcc/yield_hooks.rs` (99L: `ProvidesYieldContext`, `YieldContext`, `YieldPointMarker`), consumers `checkpoint_state_machine.rs:117-137` (`CheckpointYieldPoint` enum + `EnumCount`, selection key `0xC4EC_9011_C4EC_9011`), commit-side `CommitYieldPoint` (mod.rs:1544+), btree spill hooks (`arm_spill_yield_on_read` + `SpillYieldHook`, btree.rs:1450-1487).
**Signature:** every yield point is an ENUM VARIANT (`#[repr(u8)]` + strum `EnumCount`) — ordinal = identity; gates compile via `#[cfg(any(test, injected_yields))]` so production carries zero hook cost.
**Data Shape:** a u64 selection KEY picks which point(s) fire; hooks thread a `YieldContext` through constructors (e.g. `MvccLazyCursor` carries `connection`/`yield_instance_id` only under the same cfg).

### Decisive source
```rust
// checkpoint_state_machine.rs:118-124 — the pattern:
#[cfg(any(test, injected_yields))]
pub(crate) enum CheckpointYieldPoint {
    BeforeAcquireLock,
    AfterDurableBoundaryAdvanced,
    AfterCollectTableRows,
    BeforePagerCommit,
}
// yield_points.rs — deterministic outcomes at chosen points:
// inject_transition_yield / inject_transition_failure
```
Tests then drive the SAME state machine through resume-at-every-point matrices: `test_logical_log_streaming_recovery_forced_yields_bounded_memory`, pager's `checkpoint_db_sync_completion_still_leaves_backfill_unpublished_until_proof_install`, btree's spill-yield chain-read probe. The named-constant selection tag keeps test runs reproducible across processes.

**Flow:** test sets context {key → point set} → machine hits gated checkpoint → yields as IOResult::IO without doing IO → test resumes → asserts invariant held across that specific suspension.
**Invariant:** yield points must be ENUMERATED and versioned with the state machine — a new state with no yield point is an untested suspension; injection code must cfg-vanish from release builds.
**Probe:** the forced-yield tests listed above ARE the probes; hermitage suite composes them for isolation-under-yield.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "YieldPointMarker inject_transition_yield CheckpointYieldPoint", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt enumerated cfg-gated yield points for any resumable state machine. Adapt keying to your test harness. Omit nothing else — this is small enough to port whole.
