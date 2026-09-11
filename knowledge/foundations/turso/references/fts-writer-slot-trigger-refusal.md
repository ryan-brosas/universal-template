<!-- capsule-v2 -->
# FTS per-index writer slot — why can't one statement open two flushing cursors, and what error must the second get?

**Source:** turso (MIT) `main@d9266124f` ($REFERENCE_ROOT/memory/turso); Codebase Memory `turso`. **Question:** How do you stop a trigger writing the FTS-indexed table it fires on from storing the union of two divergent Tantivy file sets under one manifest — without blocking legitimate sequential statements?

## One slot per connection, claimed on first mutation, refused with Raise(Abort)
**Path/Symbol:** `core/index_method/fts.rs`: `FtsWriterSlot` (:1377-1380), `claim_writer_slot` (:2015-2061), `release_writer_slot` (:2185-2194), `acquire_mvcc_write_lease` (:2065-2110), lazy `ensure_writer` (:2154-2181).
**Signature:** `fn claim_writer_slot(&mut self) -> Result<()>`; slot state is `Arc<Mutex<Option<FtsWriterSlot>>>` shared between attachment and every cursor; `FtsWriterSlot { connection: Weak<Connection>, cursor_instance: u64 }`.
**Data Shape:** claim identity = (live connection ptr, cursor instance id). The slot is claimed on the cursor's FIRST document mutation (a plan may open several write-mode cursors; usually only one ever mutates), and released at stage_statement_commit / abort / close — after which that cursor never flushes again, so a later statement's cursor may write.

### Decisive source
```rust
// fts.rs:2033-2044 — the refusal arm (verbatim):
if same_live_connection && claim.cursor_instance != self.cursor_instance_id {
    // Raise(Abort) so the whole statement rolls back: the
    // refused write may sit mid-statement (a trigger body),
    // and its base rows must not commit without their index
    // entries.
    return Err(LimboError::Raise(
        turso_parser::ast::ResolveType::Abort,
        "statement already has an open writer on this FTS index; \
         a trigger cannot write the FTS-indexed table its firing \
         statement is writing".to_string(),
    ));
}
// A claim from another (or dead) connection: cross-connection
// writers are serialized by the pager write lock or the MVCC
// write lease, so this claim is stale. Replace it.
```

**Flow:** claim → if same live connection holds it with a DIFFERENT cursor instance → Raise(Abort) (statement-level rollback keeps base rows consistent with their absent index entries); a claim from another or DEAD connection (Weak upgrade fails) is stale and silently replaced → then acquire_mvcc_write_lease runs (no-op in WAL mode) and on lease error releases the slot before propagating (:2055-2058) → ensure_writer builds the Tantivy IndexWriter ONLY after slot+lease are held (:2144-2148 comment: "a refused writer never pays for Tantivy writer construction").
**Invariant:** the Raise(Abort) choice is semantic, not cosmetic — aborting only the offending statement (not the transaction) matches SQLite RAISE(ABORT) semantics where prior changes of THAT statement roll back but keep the transaction. The stale-claim replacement rule is sound ONLY because cross-connection writers are already serialized by pager write lock (WAL) or the MVCC write lease; port both halves together. Writer construction is 1 worker + 1 merge thread with NoMergePolicy (:2160-2178) because merges are driven synchronously by commit-time maintenance — background workers would sit idle forever.
**Probe:** grep anchors byte-exact at HEAD: `grep -c 'Raise(' core/index_method/fts.rs` ≥ 1 hitting :2038; `grep -n 'fn claim_writer_slot' core/index_method/fts.rs` = :2015; direct behavior pinned by integration suite tests/integration/index_method/ (trigger double-writer case exercised via sqllogic fts scripts under testing/).
**Retrieve:** search_graph "FtsWriterSlot claim_writer_slot acquire_mvcc_write_lease" resolves all three symbols line-exact (:2015-2061/:2065-2110/:1377-1380).

## Verdict
Adopt the single-flusher-per-statement discipline with statement-scope Abort refusal and stale-claim replacement; adapt the slot key to your engine's cursor identity. Omit tantivy's writer threading model unless porting the FTS method itself. Coverage: no_recorded_issue on fts.rs.
