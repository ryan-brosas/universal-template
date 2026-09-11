<!-- capsule-v2 -->
# Index-method SPI — how does an external index plug into the engine without bypassing MVCC?

**Source:** turso (MIT) `main@d9266124f` ($REFERENCE_ROOT/memory/turso); Codebase Memory `turso`. **Question:** What is the minimal contract an out-of-tree index method must implement so the engine treats it like a first-class index — and which defaults are safe only for stateless methods?

## Factory → attachment → cursor, with a declared MVCC posture
**Path/Symbol:** `core/index_method/mod.rs`: `IndexMethod::attach` (:31-37), `IndexMethodAttachment` (:53-56), `IndexMethodDefinition.mvcc_support/results_materialized/backing_btree` (:80-100), `IndexMethodMvccSupport` (:59-77), `ensure_mvcc_support` (:415-435).
**Signature:** `fn attach(&self, configuration: &IndexMethodConfiguration) -> Result<Arc<dyn IndexMethodAttachment>>`; attachment yields `definition() -> IndexMethodDefinition` + `init() -> Box<dyn IndexMethodCursor>`.
**Data Shape:** the definition declares: parsed SELECT *patterns* (with positional placeholders the planner fills from the original query), `backing_btree` (allocate a real btree root for this logical index), `results_materialized` (query_start eagerly collects rowids ⇒ DML-safe; false ⇒ emitter wraps results in a RowSet before writing), and a four-level `mvcc_support`: Unsupported / ReadOnly / TransactionalBackingStore / ExternalTransactional.

### Decisive source
```rust
// mod.rs:59-77 — the four-posture enum (doc comments verbatim):
/// The method cannot be opened while MVCC is active.
Unsupported,
/// The method may query MVCC snapshots but has no transactional write path.
ReadOnly,
/// Persistent state is stored exclusively through core-provided,
/// MVCC-aware backing storage.
///
/// Under MVCC, at most one transaction may write a given index at a time
/// (a per-index write lease, taken on the first document mutation).
/// Contention is a retryable `Busy`; a writer whose read snapshot
/// predates the index's last publication gets `WriteWriteConflict` and
/// must restart its transaction. `BEGIN CONCURRENT` therefore does not
/// parallelize writes to one index of this kind — that is the write
/// throughput ceiling per index.
TransactionalBackingStore,
```

**Flow:** CREATE INDEX ... USING <method> → factory attach() builds the attachment (schema, patterns, caches) → planner matches queries against patterns + cost estimates (`estimate_cost`) → VDBE opens cursors only through `IndexMethodContext`, which pins journal mode, transaction mode, snapshot identity, schema generation, and a hashed `runtime_id` (FNV over database incarnation ⊕ schema generation ⊕ method/table/index names, :175-191) → statement/transaction outcome flows through the hook ladder below.
**Invariant:** every access gate is DECLARED, not discovered: `ensure_mvcc_support` rejects Unsupported always and ReadOnly-on-write with ParseError (:419-434); a non-backing-btree method whose schema row carries a nonzero root page is Corrupt (:239-244). The trait's empty default outcome hooks are correct ONLY for methods keeping no transaction-private in-memory state — the doc comment states skipping `on_transaction_rolled_back` silently publishes rolled-back work and skipping `stage_statement_commit` silently loses writes (:536-541). A stateful porter MUST implement all of them.
**Probe:** `core/index_method/mod.rs:796-809` `mvcc_support_declaration_rejects_unsupported_access` asserts Unsupported→ParseError even for reads, ReadOnly read-OK/write-rejected, TransactionalBackingStore write accepted.
**Retrieve:** search_graph "IndexMethodDefinition mvcc_support ensure_mvcc_support" resolves `turso.core.index_method.mod.IndexMethodMvccSupport` core/index_method/mod.rs :59-77 line-exact.

## Statement-scoped commit ladder (the porting trap)
**Path/Symbol:** `core/index_method/mod.rs`: `IndexMethodCursor` doc contract (:518-541) + hooks `stage_statement_commit`/`abort_statement`/`on_statement_committed`/`on_transaction_committed`/`on_transaction_rolled_back`/`on_savepoint_rolled_back`/`close` (:598-623).
**Signature:** `fn stage_statement_commit(&mut self, _context: &IndexMethodContext) -> Result<IOResult<()>>` — the ONLY fallible/I-O-capable phase; all outcome hooks after it are infallible and I/O-free by contract.
**Data Shape:** ordered protocol for any cursor that wrote: 1. stage_statement_commit at statement halt → 2. on_statement_committed once the savepoint releases → 3. exactly one terminal: on_transaction_committed | on_transaction_rolled_back | replacement (a newer same-attachment cursor inherits the transaction) → 4. close. A failed statement gets abort_statement instead of steps 1–2.

### Decisive source
```rust
// mod.rs:520-532 — ordering verbatim:
/// 1. `stage_statement_commit` — stage every pending change durably (the
///    only fallible, I/O-capable phase), at the statement's halt.
/// 2. `on_statement_committed` — the statement's savepoint was released.
/// 3. Exactly one of three ends:
///    * `on_transaction_committed` — the transaction is durable;
///    * `on_transaction_rolled_back` — everything the transaction staged was
///      undone;
///    * replacement — a later statement in the same transaction opened a
///      newer cursor for the same attachment, so this one is closed without
///      either transaction outcome (the newer cursor receives it).
```

**Flow:** mirrors turso's own savepoint planes (statement-savepoint-lifecycle): per-statement staging keeps rollback cheap; publish-to-transaction happens only after the savepoint release survives; transaction end publishes or discards wholesale.
**Invariant:** fallible work cannot hide in infallible hooks — a porter who commits durable bytes inside on_statement_committed breaks the error path (no way to report failure mid-ladder); one who defers staging past statement halt breaks savepoint rollback (unstaged work can't be aborted).
**Probe:** `core/vdbe/statement_lifecycle_tests.rs` (whole file is this ladder's test plane under `#[cfg(feature = "fts")]`): `fts_writes_survive_deferred_shared_autocommit` (:1645-1686) pins that a completed writer's FTS document commits WITH its base row when a sibling statement ends the deferred shared autocommit; `interrupt_during_fail_staging_keeps_fail_outcome` (:1721+) pins INSERT OR FAIL kept rows surviving an interrupt arriving during staging.
**Retrieve:** search_graph "IndexMethodCursor stage_statement_commit on_transaction_rolled_back" resolves `turso.core.index_method.mod.IndexMethodCursor` core/index_method/mod.rs :542-647.

## Verdict
Adopt the SPI shape: factory/attachment/cursor split, declared mvcc_support posture, pattern-based planning with materialization flag, and the exact hook ladder. Adapt the runtime_id hash and context fields to your engine's identity model. Omit tantivy specifics (see fts-capsules). Coverage caveat: none — mod.rs has no_recorded_issue and its unit test executes the gate matrix.
