<!-- capsule-v2 -->
# MVCC rowid allocation — how do BEGIN/END markers keep concurrent allocators from colliding or leaking ids across restart?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What protocol lets each transaction allocate rowids optimistically while guaranteeing committed rows never collide — even after recovery?

## start/end watermark bracketing with per-tx local counters
**Path/Symbol:** `core/mvcc/cursor.rs:725-766` (`MvccLazyCursor::{start_new_rowid, initialize_max_rowid, allocate_next_rowid, end_new_rowid}`), allocator store side `mod.rs` (`get_rowid_allocator`, `insert_row_id_maybe_update` at :5033 region).
**Signature:** `pub fn allocate_next_rowid(&self) -> Option<(i64, Option<i64>)>`; `initialize_max_rowid(&mut self, max_rowid: Option<i64>)`.
**Data Shape:** `NextRowidResult` seeds the cursor's local window from the table's durable max; the tuple return carries the allocated id plus an optional hint of the next free id; per-table allocators are separate (table_id-keyed), and MVCC table ids canonicalize to NEGATIVE root-page numbers so schema tables bootstrap cleanly.

### Decisive source
```rust
// mod.rs:5031-5034 — allocation is recorded into BOTH version and allocator:
let row_versions = self.insert_version(id.clone(), row_version)?;
let allocator = self.get_rowid_allocator(&id.table_id);
allocator.insert_row_id_maybe_update(id.row_id.to_int_or_panic());
// cursor.rs:201-205 context: the same dual-source discipline governs reads;
// writes must keep allocator watermarks ahead of every visible row.
```
`insert_row_id_maybe_update`'s name carries the rule: update only when advancing the max (monotonic, fetch-max semantics in spirit) — a rolled-back transaction's speculative allocations must not LOWER the watermark, and a checkpoint must persist it so post-restart allocations continue above every materialized row. The end_new_rowid / begin bracket on the cursor side scopes a single statement's reservation window.

**Flow:** init from durable max → allocate locally within tx → insert versions + maybe_update allocator → commit ⇒ watermark stands | abort ⇒ versions become invisible garbage; watermark never retreats.
**Invariant:** monotonic-only updates; per-table isolation; recovery must reseed from persisted allocator state, not from scanning rows (a deleted max row would otherwise regress).
**Probe:** round-trips via `test_logical_log_roundtrip_random_table_ops`; rowid edge coverage `test_logical_log_read_i32_min_table_id` + `test_logical_log_rowid_negative_varint_roundtrip` pin the negative-id (schema-table) encoding that allocator persistence relies on.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "allocate_next_rowid rowid_allocator insert_row_id_maybe_update", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt monotonic-maybe-update allocators for optimistic id assignment. Adapt persistence point to your checkpoint machinery. Omit negative-canonicalization unless you share SQLite's schema-table conventions.
