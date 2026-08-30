<!-- capsule-v2 -->
# Named-savepoint opcode + dual-engine mirroring — how does one SAVEPOINT statement stay consistent across MVCC store, main WAL pager, temp, and attached databases?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** Where must the savepoint be recorded so ROLLBACK TO restores pages, in-memory schemas, FK counters, and every attached DB together — and what happens on partial mirror failure?

## Dispatch + connection frame ledger
**Path/Symbol:** `core/vdbe/execute.rs:op_savepoint` (:4750-4989); `mirror_named_savepoint_to_active_non_main_databases` (:3886-3955); `Connection::push/rollback/release_named_savepoint_frame` (connection.rs :4866-4879).
**Signature:** `pub fn op_savepoint(program, state, insn: &Insn /* Savepoint { op, name } */, pager) -> Result<InsnFunctionStepResult>`.
**Data Shape:** connection keeps its own `NamedSavepointFrame { name, starts_transaction, deferred_fk_violations, main_schema_snapshot, temp_schema_snapshot, staged_schema_snapshot }` stack — schema SNAPSHOTS captured at BEGIN (Arc clones), not recomputed at rollback.

### Decisive source (the BUSY gate SQLite has and why all three ops reject)
```rust
// execute.rs :4760-4776
// SQLite rejects SAVEPOINT and RELEASE with SQLITE_BUSY while write
// statements are in progress ... SQLite does allow ROLLBACK TO there
// because it trips all open cursors ... Turso has no cursor-tripping
// mechanism, and letting a suspended writer resume on top of pages
// restored by ROLLBACK TO would interleave two inconsistent page states.
if !conn.is_nested_stmt() && conn.n_active_writes.load(Ordering::SeqCst) > 0 {
    return Err(LimboError::StatementsInProgress(match *op { ... }));
}
```

**Flow (Begin):** pre-load ALL active non-main WAL headers FIRST because "Mirroring mutates several pager savepoint stacks and therefore cannot yield halfway" (:4780-4785) → under `with_savepoint_schema_snapshot` capture the three schema Arcs → route by engine: MVCC ⇒ lazily `begin_tx` if none (Read mode) then `mv_store.begin_named_savepoint(tx_id, name, starts_transaction=auto_commit, fk_count)`; WAL pager ⇒ eager `begin_read_tx`, `open_subjournal()`, `open_named_savepoint(name, db_size, ...)` (TODO comment: this pins the snapshot earlier than SQLite's write-time materialization :4809-4816) → build frame → MIRROR to attached/temp pagers; **on any mirror failure: blind idempotent Release(name) on non-main pagers, then release main's savepoint too** ("which would leak past commit / rollback" :4849-4870) → push frame to connection ledger → if `starts_transaction`, clear auto_commit.

### Decisive source (RollbackTo = pages + schemas + cookies + fk counter)
```rust
// execute.rs :4927-4983 (MVCC arm shown via mv_store/pager above)
let frame_info = conn.rollback_named_savepoint_frame(name);
mirror_...(SavepointMirror::Rollback(name))?;             // temp+attached PAGES
conn.fk_deferred_violations.store(deferred_fk_snapshot, Ordering::Release);
// Restore all in-memory schemas ... Without this restore, the in-memory
// schemas would keep DDL that the disk-level rollback just undid.
*conn.schema.write() = info.main_schema_snapshot;
... temp + staged ...
conn.bump_prepare_context_generation();
// Invalidate cached schema cookies on ALL pagers whose pages may have been rolled back.
pager.set_schema_cookie(None);  // + every attached pager (:5243-5249)  [execute.rs :5229-5249]
```
Release: engine result `NotFound` ⇒ TxError; `Commit` (root frame started the txn) ⇒ pop frame, mirror-release, then tail-call `op_auto_commit` to run the real commit ladder (execute.rs :4810; Release-arm call site :5183). Commit/Rollback clear stale mirrors explicitly — non-main pagers accumulate mirrored savepoints the main commit doesn't touch, so both are `clear_savepoints()`ed or a later same-name ROLLBACK TO "can undo unrelated pages. See fuzz regression in `named_savepoint_differential_fuzz`" (:4986-4992).

**Invariants:** (1) The pager/store owns PAGE truth; the connection frame owns SCHEMA truth — rollback needs BOTH plus cookie invalidation on every pager whose bytes changed. (2) Mirroring is best-effort atomic via compensating blind releases (idempotent on missing names). (3) No savepoint op may interleave with a suspended writer (no cursor-tripping exists). (4) Deferred-FK counter is part of the savepoint state, restored from the frame snapshot.
**Probe:** `grep -c 'SAVEPOINT' sqlite/conformance/sqlite-sqltests/savepoint.sqltest` = 41 ops incl. nested-release-outer (`RELEASE outer_sp` commits BOTH inner rows) and release-inside-begin-does-not-commit; runnable via repo sqltest runner (`@cross-check-integrity` tagged).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "op_savepoint mirror_named_savepoint rollback_to_snapshot open_subjournal", limit: 8 });
// turso.core.vdbe.execute.op_savepoint Function core/vdbe/execute.rs 4750-4989
// turso.core.storage.pager.Pager.rollback_to_snapshot Method core/storage/pager.rs 2219-2319
```

## Verdict
Adopt the three-ledger split (store/pages, connection frames w/ schema snapshots, per-pager mirrors), compensating-release mirror protocol, and post-commit/rollback mirror clearing. Adapt the busy-gate message. Omit the SQLite-materialization TODO as behavior guidance only. Coverage: cited paths `no_recorded_issue`; pager twin capsule for byte-level subjournal restore is `subjournal-single-owner-latch.md` + `rollback_to_snapshot` (aristo intent: restored pre-images and beyond-boundary discards "must happen together").
