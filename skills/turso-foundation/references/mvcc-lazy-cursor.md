<!-- capsule-v2 -->
# MVCC lazy cursor — how does a cursor merge MVCC versions with B-tree rows across async IO?

**Source:** turso (MIT) `main@def9a0601b8e` ($REFERENCE_ROOT/memory/turso); Codebase Memory project `turso`. **Question:** How are uncommitted versions, committed B-tree rows, and injected yields unified in one cursor without losing position?

## Dual-source iteration with an epoch-guarded index finger
**Path/Symbol:** `core/mvcc/cursor.rs`: `MvccLazyCursor` (:492-540), `CursorPosition` (:23-45), advance state machines (`AdvanceBtreeState`, `NextState`, `PrevState`, :60-90), `read_mvcc_current_row` (:699), seek (:1510), insert (:1749), delete (:1846); yield plumbing `core/mvcc/yield_points.rs` (`YieldPoint{ordinal, point_count}`, `YieldInjector`, `FailureInjector`) + `core/mvcc/yield_hooks.rs`.
**Signature:** `MvccLazyCursor::new(db: Arc<MvStore>, connection, tx_id, root_page_or_table_id, mv_cursor_type, btree_cursor: Box<dyn CursorTrait>)`; `fn next(&mut self) -> Result<IOResult<()>>`; `fn seek(&mut self, SeekKey<'_>, SeekOp) -> Result<IOResult<SeekResult>>`.
**Data Shape:** `CursorPosition::{BeforeFirst, Loaded { row_id, in_btree: bool, versions: Option<RowVersions> }, End}` — `versions` is captured from the range iterator on the scan path so `read_mvcc_current_row` can skip a second map lookup; btree/index/seek positions carry None and fall back to a lookup. The cursor holds BOTH a stateful MVCC table/index iterator and a boxed BTreeCursor; `index_finger_epoch` snapshots `MvStore::index_rows_epoch`.

### Decisive source
```rust
// cursor.rs:528-539 (verbatim field docs):
//   "New index keys can be created at or behind an already-positioned finger
//    while the scan's cursor is open (e.g. a DELETE on the same connection
//    inserts a tombstone key mid-scan, #7578); versions appended to *existing*
//    keys are fine (chains are read live through their Arc), but a new key
//    would be silently skipped. On an epoch mismatch the finger is reset so it
//    reseeds at the current B-tree key instead of trusting its stale position."
// new() also resolves the root page against this reader's snapshot:
//   "a PASSIVE checkpoint may have dropped (and possibly reused) the page …
//    The WAL read mark keeps the pages readable; this keeps the in-memory
//    root_page -> table_id reverse lookup snapshot-consistent. See retired_rootpages."
```

**Flow:** every public operation runs as an IO-yielding mini state machine (`return_if_io!` propagates `IOResult::IO` outward, same PC re-executes): rewind/next/prev merge two ordered sources — visible MVCC versions from the SkipList iterators and committed rows from the B-tree — by peeking both and advancing the smaller key. Injected yields (`inject_io_yield`) synthesize `IOResult::IO(explicit_yield)` at numbered safe boundaries so tests can suspend mid-advance.
**Invariant:** visibility filtering uses ONLY the owning transaction's snapshot; position survives yields because all partial progress lives in the enum state machines, never in local variables.
**Probe:** `core/mvcc/database/tests.rs:6031-6075` (`test_mvcc_cursor_next_yields_with_injected_yield`) injects a yield at `CursorYieldPoint::NextStart` via `FixedYieldInjector` and asserts the FIRST next() returns `IOResult::IO(io)` with `is_explicit_yield()`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "MvccLazyCursor CursorPosition dual_peek index_finger_epoch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-cursor merge with epoch invalidation whenever a logical view spans mutable memory structures plus a persistent tree. Adapt the merge order to your key comparator; do NOT adapt the epoch rule away — removing it silently drops concurrently created keys (#7578). Omit the reusable_immutable_record allocation optimization until profiling demands it.
