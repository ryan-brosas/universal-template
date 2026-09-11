<!-- capsule-v2 -->
# IndexMethodContext identity — what coordinates make a parked external-index cursor safe across detach, drop, and schema churn?

**Source:** turso (MIT) `main@d9266124f` ($REFERENCE_ROOT/memory/turso); Codebase Memory `turso`. **Question:** Which fields must an index-method operation capture at open time so reuse decisions never guess — and why is the connection edge Weak?

## FNV identity + dual snapshot shape + Weak self-edge
**Path/Symbol:** `core/index_method/mod.rs`: `IndexMethodContext` (:198-211), `new()` (:228-314), `IndexMethodDatabaseIdentity{id,name,incarnation}` (:148-155), `IndexMethodIdentity{...,runtime_id,schema_root}` (:158-173), `index_method_runtime_id` (:175-191), `IndexMethodSnapshotIdentity::{Wal,Mvcc}` (:112-124), `connection()` upgrade-or-error (:331-335).
**Signature:** `fn new(connection: &Arc<Connection>, database_id: usize, definition: &IndexMethodDefinition<'_>) -> Result<Self>`; production callers receive contexts ONLY from the VDBE (`for_test` is feature-gated :318-326).
**Data Shape:** database identity = (connection-local slot id, name, `incarnation` — runtime identity distinguishing detach/reattach and close/reopen lifetimes); index identity adds `runtime_id` = FNV-1a over incarnation ⊕ schema_generation ⊕ method/table/index name bytes (init 0xcbf29ce484222325 ⊕ incarnation; prime 0x100000001b3) and `schema_root` (MUST stay 0 for non-backing methods). Snapshot = Wal{checkpoint_sequence,max_frame} or Mvcc{transaction_id,begin_timestamp}.

### Decisive source
```rust
// mod.rs:199-202 + 331-334 — the cycle-breaker (verbatim):
/// Weak so a cursor parked on its connection (with its context) does not
/// make the connection reference itself — a strong edge here kept leaked
/// connections alive forever, holding their WAL locks.
...
self.connection.upgrade().ok_or_else(|| {
    LimboError::InternalError("index method context outlived its connection".to_string())
})
```

**Flow:** VDBE opens cursor → Context::new resolves journal mode + transaction mode + snapshot from EITHER mv_store (Mvcc: read_snapshot_ts(tx), schema_generation()) OR pager (Wal: wal_pos() → (checkpoint_sequence,max_frame), schema cookie as generation) → runtime_id hashed for same_attachment comparisons → cursor parks with its context → any later use upgrades the Weak; teardown-in-progress ⇒ InternalError "context outlived its connection", which outcome hooks treat as nothing-left-to-clean (:330 comment).
**Invariant:** the collision tolerance is DOCUMENTED, not accidental (:162-168): Drop/recreate of the index inside ONE MVCC transaction can produce equal runtime_ids because MVCC DDL does not advance the schema generation — consumers tolerate this because "a colliding cursor is merely replaced-and-closed and index content is validated separately by the persisted (incarnation, generation) pair". Porters who add DDL-driven generation bumps under MVCC change that contract. The Weak edge is load-bearing for crash recovery: Connection::drop rolls the tx back and releases locks/leases — a strong cycle would leak connections holding WAL locks (see mvcc-index-method-write-lease probe).
**Probe:** `core/vdbe/statement_lifecycle_tests.rs:1693-1719` asserts `weak.upgrade().is_none()` after dropping the writing connection mid-tx (cycle-free proof); `grep -n 'fn index_method_runtime_id' core/index_method/mod.rs` hits :175.
**Retrieve:** search_graph "IndexMethodContext IndexMethodDatabaseIdentity runtime_id" resolves `turso.core.index_method.mod.IndexMethodContext` core/index_method/mod.rs :198+ line-exact.

## Verdict
Adopt captured-at-open immutable identity + dual-mode snapshot stamping + Weak back-edge to the owner. Adapt the hash inputs to your object lifecycles but keep incarnation semantics (detach/reopen ≠ same database). Omit yield-context test plumbing unless porting the deterministic simulator. Coverage: no_recorded_issue on mod.rs.
