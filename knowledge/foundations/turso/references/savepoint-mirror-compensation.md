<!-- capsule-v2 -->
# Savepoint mirror pre-load + compensating release — how do temp/attached databases join a savepoint when mirroring cannot yield mid-flight?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** Why are all non-main WAL headers loaded BEFORE the first savepoint opens, and what exactly happens when the mirror to attached pagers fails halfway?

## Header pre-load (restartability of the Begin path)
**Path/Symbol:** `core/vdbe/execute.rs:load_active_non_main_wal_headers_for_named_savepoint` (:3865-3878) called at op_savepoint Begin :4783-4785; per-pager body `pager_db_size_for_named_savepoint`; the no-yield rationale comment :4780-4782.
**Signature:** `fn load_active_non_main_wal_headers_for_named_savepoint(conn: &Connection) -> Result<IOResult<()>>` — returns `IOResult::IO(io)` so op_savepoint can yield BEFORE mutating any state.
**Data Shape:** iterates `with_all_attached_pagers_with_index`, skipping MVCC-backed dbs (`mv_store_for_db().is_some()`) and pagers without a read lock.

### Decisive source
```rust
// execute.rs :4780-4785
// Mirroring mutates several pager savepoint stacks and therefore
// cannot yield halfway through. Load every active WAL header
// before opening the first savepoint so an I/O yield is restartable.
if let IOResult::IO(io) = load_active_non_main_wal_headers_for_named_savepoint(&conn)? {
    return Ok(InsnFunctionStepResult::IO(io));
}
```

**Flow:** SAVEPOINT Begin is a two-phase opcode: phase 1 performs ALL potentially-yielding header reads up-front and yields if needed (restart from the same PC is safe because NOTHING has mutated yet) → phase 2 runs snapshot-capture, engine begin, mirror, frame push with NO I/O points. This is the vdbe async-contract pattern applied to multi-object mutation: partition the opcode into "yielding reads first, atomic mutations second".
**Invariant:** Once Begin starts opening savepoints across engines/pagers it MUST complete without yielding — an I/O yield between mirror steps would leave partial stacks that a resumed program cannot distinguish from success. The MVCC skip matters: MVCC dbs record named savepoints in the store's transaction state, not pager stacks, and have no WAL headers to load.
**Probe:** `sed -n '4750,4989p' core/vdbe/execute.rs | grep -c 'load_active_non_main_wal_headers_for_named_savepoint(&conn)'` = 1 (single call site, before any mutation).

## Mirror dispatch + compensating-release on partial failure
**Path/Symbol:** `core/vdbe/execute.rs:SavepointMirror` enum (:3880-3884); `mirror_named_savepoint_to_active_non_main_databases` (:3886-3955); failure handler in op_savepoint Begin (:4849-4870); IO-fallback error arm (:3930-3943).
**Signature:** `enum SavepointMirror<'a> { Begin(&'a NamedSavepointFrame), Release(&'a str), Rollback(&'a str) }`.
**Data Shape:** per attached db: MVCC store path (`begin/release/rollback_to_named_savepoint` on tx_id) vs WAL-pager path (`holds_read_lock()` gate). Release/Rollback results are discarded with `let _ =` — best-effort by design.

### Decisive source (the compensation ladder)
```rust
// execute.rs :4849-4869
if let Err(mirror_err) = mirror_named_savepoint_to_active_non_main_databases(
    &conn,
    SavepointMirror::Begin(&frame),
) {
    // Release the partially-opened mirror savepoints.
    let _ = mirror_named_savepoint_to_active_non_main_databases(
        &conn,
        SavepointMirror::Release(name),
    );
    // Release the main savepoint we just opened so it
    // does not linger without a connection-level frame
    // recording it (which would leak past commit / rollback).
    if let Some(mv_store) = mv_store.as_ref() {
        if let Some(tx_id) = conn.get_mv_tx_id() {
            let _ = mv_store.release_named_savepoint(tx_id, name);
        }
    } else {
        let _ = pager.release_named_savepoint(name);
    }
    return Err(mirror_err);
}
conn.push_named_savepoint(frame);
```

**Flow:** main-engine savepoint opens FIRST → mirror fans out to every attached/temp db → ANY mirror error triggers: blind idempotent `Release(name)` across non-main pagers (safe on names never opened: release-of-missing = NotFound no-op), then release of MAIN's savepoint (MVCC or WAL arm), then propagate the original error. Only after full mirror success is the connection-level frame pushed (:4871) — keeping the three ledgers (store/pages, connection frames, mirrors) consistent or fully rolled back.
**Flow (RollbackTo ordering):** engine rollback returns the deferred-FK counter snapshot → `rollback_named_savepoint_frame` pulls schema restore info → MIRROR runs Rollback on attached pages → THEN fk counter stored (:4943-4944) and schemas restored — page rollback precedes in-memory restore so a failed mirror never leaves memory ahead of disk.
**Invariant:** The connection frame is pushed ONLY after every ledger agrees; conversely Release/Rollback clear frames even when mirror calls fail silently (`let _`). The IO-fallback arm documents the one unrecoverable shape — mirror Begin on a non-main pager whose page 1 was evicted would need I/O mid-mutation, so it surfaces as a loud InternalError ("not yet IO-reentrant", :3936-3941) instead of panicking.
**Probe:** `sed -n '4849,4870p' core/vdbe/execute.rs | grep -c 'SavepointMirror::Release(name)'` = 1 (compensating blind release present) and `grep -cF '(page 1 not cached)' core/vdbe/execute.rs` = 1; direct test: tests/fuzz/savepoint.rs `named_savepoint_differential_fuzz` seeds TEMP DDL + FK workloads whose verify queries include `temp.sqlite_schema`, exercising the mirror+restore pair against rusqlite for 2000 steps.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "op_savepoint mirror_named_savepoint rollback_to_snapshot open_subjournal", limit: 8 });
// turso.core.vdbe.execute.op_savepoint Function core/vdbe/execute.rs 4750-4989
```
Sibling capsule `savepoint-opcode-mirroring.md` owns the BUSY gate excerpt + three-ledger split overview; this capsule owns the PRE-LOAD phase and the compensation ladder mechanics.

## Verdict
Adopt the two-phase Begin (all yielding I/O up-front, then atomic multi-ledger mutation with compensating releases on failure) for any fan-out savepoint/join protocol; adopt best-effort mirror semantics with loud-error fallback for genuinely un-restartable shapes. Adapt the header-preload mechanism to the host's equivalent of "reads that may evict/yield". Omit Turso's eager read-tx on the main pager (TODO :4809-4816 — SQLite materializes at write upgrade; guidance only). Direct tests: savepoint.sqltest attach-plane cases via @cross-check-integrity; fuzz harness outcome-parity incl. temp_schema verification.
