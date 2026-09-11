<!-- capsule-v2 -->
# op_transaction five-state begin ladder — why does schema validation happen at three different points, and what survives each IO yield?

**Source:** turso MIT `main@1654d1587` (re-pinned pass 15); Codebase Memory `turso`. **Question:** Opening a transaction spans writer-mutex checks, MVCC/WAL begins, named-savepoint replay, and two schema-cookie comparisons — what order is mandatory and why?

## Start → AttachedBeginWriteTx → BeginNamedSavepoints → CheckSchemaCookie → BeginStatement
**Path/Symbol:** `core/vdbe/execute.rs`: `enum OpTransactionState` (:3993-4000), error wrapper `op_transaction` (:4018, clears the op slot on ANY Err), `op_transaction_inner` machine (:4214-end); helpers `begin_mvcc_tx` (:4041), `pager_db_size_for_named_savepoint` (:4062), `open_named_savepoint_frames_on_wal_pager` (:4070).
**Signature:** states via `*state.active_op_state.transaction()`; entry guard `let statement_writes_db = program.write_databases.get(*db)` (:4249).
**Data Shape:** connection-level `TransactionState::{None, Read, Write{schema_did_change}, PendingUpgrade}` transition table evaluated in Start; attached DBs skip phase 1 entirely (their pager locks are independent, :4054-4058).

### Decisive source
```rust
// execute.rs:4263-4271 — the async-IO-motivated mutex:
//   // One connection may have many active readers, but only one
//   // top-level writer. A second writer on the same connection is
//   // rejected before it opens transaction or savepoint state.
//   // This is stricter than SQLite … Turso can suspend there for async I/O,
//   // so a second writer would make reset/drop cleanup hard to get right.
// :4282-4287 — pre-tx reprepare gate (cookie alone can miss shared-schema swaps):
//   // Fast path: if checkpoint root publication already replaced the
//   // shared schema, force reprepare before opening any transaction state.
//   if is_main_db && mv_store.is_some()
//      && conn.mvcc_schema_requires_reprepare_before_tx() { return Err(SchemaUpdated) }
```
The ladder's three validation points: (1) BEFORE any tx opens — the fast reprepare gate above (shared-schema swap without a cookie bump); (2) AFTER read-tx/write-tx/savepoint opens — `CheckSchemaCookie` (:4695) compares header vs compiled cookie ⇒ `LimboError::SchemaUpdated`, tolerating `Page1NotAlloc` as "no page 1 yet" (:4710); (3) AT COMMIT — `last_committed_schema_change_ts > tx.begin_ts` check (pinned by test_insert_in_middle_commit_of_create_index_returns_err). `BeginStatement` then layers statement journals per DB role: main ⇒ full `begin_statement` (core/vdbe/mod.rs :1305); attached WAL ⇒ pager subjournal + savepoint + tracked pager; attached MVCC ⇒ MvStore savepoint; and enforces single-writer bookkeeping (`n_active_writes.fetch_add` with `previous == 0` assert :4776) plus sibling-aware auto-commit cleanup marking.

**Flow:** every arm persists progress in the slot before yielding IO; AttachedBeginWriteTx exists because attached write-txs open only after their read snapshot exists; BeginNamedSavepoints replays connection savepoint frames into the pager/subjournal and routes back to AttachedBeginWriteTx when an attached writer still needs its lock.

**Invariant:** ordering is fixed — no transaction state may open before the writer-exclusivity check; no statement journal before the schema cookie validates; errors always clear the active-op slot (op_transaction wrapper).

**Probe:** `test_insert_in_middle_commit_of_create_index_returns_err` (`core/mvcc/database/tests.rs:8227`, yield injected at `CommitYieldPoint::LogRecordPrepared` :8247 with assertion message at :8263) pins the commit-time gate end-to-end. Coverage caveat: mvcc tests not executed this pass (pass-14 window recorded 383 passed / 2 env-quota failures); ranges verified by direct source read at `1654d1587`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "OpTransactionState op_transaction_inner mvcc_schema_requires_reprepare_before_tx get_schema_cookie", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the validate-at-three-points ladder and slot-persisted resume for any executor that can suspend mid-BEGIN. Adapt the attached-DB split to your attach model. Omit named-savepoint frame replay if you lack SAVEPOINT. Coverage caveat recorded above.
