<!-- capsule-v2 -->
# Checkpoint preemption threshold — how does a multi-thousand-row checkpoint stay cooperative with the async executor?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** Where exactly may a long-running checkpoint pause, and what state must survive the pause so resumption neither skips nor duplicates work?

## COLLECT_PREEMPTION_THRESHOLD chunking + cursor-carrying resume states
**Path/Symbol:** `core/mvcc/database/checkpoint_state_machine.rs:36` (`const COLLECT_PREEMPTION_THRESHOLD: usize = 1024`), collect_table_rows (:1124-1306), collect_index_rows (:1315-1368), gc_checkpointed_table_versions (:1759-1826), GcTableRows/GcIndexStates payload `{next_index, lwm}` (:100-107), WriteRow `requires_seek` optimization (:1419-1444).
**Signature:** collection returns `Result<Option<IOCompletions>>` — `Some(Completion::new_yield())` at 1024 processed rows; GC states carry `next_index: usize` in the state variant itself.
**Data Shape:** table-collection resume = `collect_table_cursor: Option<RowID>` (last processed key → next pass scans `(Unbounded, Excluded(last))`); index-collection resume = two-level cursor `{collect_index_tableid_cursor, collect_index_key_cursor}` (outer inclusive when key cursor present, else exclusive — :1316-1323); GC resume = index into the sorted write set.

### Decisive source
```rust
// :1290-1293 — cooperative yield inside the rows() iteration:
//   processed += 1;
//   if processed >= COLLECT_PREEMPTION_THRESHOLD {
//       return Ok(Some(IOCompletions(Completion::new_yield())));
//   }
// :1295-1304 — deterministic order makes chunked resume safe:
// "Writing in ascending order of rowid gives us a better chance of using
//  balance-quick algorithm in case of an insert-heavy checkpoint."
//   write_set.sort_by_key(|v| (Reverse(table_id) /* schema first */, row_id));
// :1426-1443 — seek elision is derived from SORTED neighbors:
//   same table ∧ no special-write ∧ next_id == prev_id + 1 ⇒ requires_seek=false
```

**Flow:** every ≥1024-row phase (table collect, index collect, table GC, index GC) counts processed entries and yields an explicit completion before that count grows unbounded → on re-entry the phase restarts from its persisted cursor/index (never from zero) → after full collection the write sets are sorted (schema-first via Reverse(table_id), then rowid ascending), which both fixes crash-recovery ordering AND enables sequential-insert seek elision during WriteRow.
**Invariant:** a preempted phase MUST resume exactly once per remaining entry — cursors are updated BEFORE processing each entry and the sort is total, so yields are transparent; GC dedups consecutive same-rowid entries so chain GC runs once per row even across chunk boundaries.
**Probe:** `checkpoint_state_machine.rs::tests::collect_table_rows_preempts_on_large_scan` (:3557), `collect_index_rows_preempts_on_large_scan` (:3605), `gc_checkpointed_table_versions_preempts_on_large_scan` (:3642) — each asserts the FIRST call yields explicitly and resumed calls collect/GC every entry exactly once.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "COLLECT_PREEMPTION_THRESHOLD collect_table_rows", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt threshold-yield + key-cursor resume for any long scan embedded in a single-threaded async executor; adapt the threshold to your frame budget; omit seek elision if your writes aren't batch-sorted. Coverage caveat: none material — probes are direct tests exercising the exact yield/resume loop.
