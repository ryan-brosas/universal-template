<!-- capsule-v2 -->
# Sequence compaction driver — how do you reclaim per-nextval version rows while keeping both storage layers consistent?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** When a hot sequence grows one row per allocation, how does checkpoint compact it to a single watermark row without blocking the executor or desyncing the MVCC store?

## SeqCompactDriver: watermark seek → scan-delete, paired across B-tree AND version chain
**Path/Symbol:** `core/mvcc/database/checkpoint_state_machine.rs:SeqCompactDriver` (:324-355), phases (:285-309), `CheckpointState::CompactSequences` doc (:80-89), direction-aware watermark note (:275-282).
**Signature:** per backing table: `SeekWatermark` (cursor.last() ascending / rewind() descending) → `ReadWatermarkRowid` → `ScanRewind` → `ScanReadRowid` → `ScanDelete` (key ≠ watermark) → `ScanNext`. Pure `IOResult` plumbing — "every cursor op yields up to the caller on page IO, so a step() call from inside the checkpoint state machine can propagate a yield upward without ever blocking the executor."
**Data Shape:** CYCLE sequences are SKIPPED ("they manage wrap correctness via inline compaction in the nextval bytecode"); non-CYCLE seqs grow monotonically because inline compaction was REMOVED from the hot path "to eliminate shared-row WW conflicts."

### Decisive source
```text
// checkpoint_state_machine.rs:311-323 — the pairing invariant:
// "the driver paired-deletes from the B-tree (via the cursor) AND from the
//  MVCC version chain (via purge_row_versions_during_checkpoint) so the two
//  layers stay consistent. Skipping the version-chain purge would leave
//  entries with btree_resident: true pointing at B-tree rows that no longer
//  exist, surviving until drop_unused_row_versions Rule 3 catches up."
// :278-281 — direction awareness:
//   "the 'current value' of a sequence is the max for ascending and the min
//    for descending — keeping the wrong end as the watermark after compaction
//    would lose the last emitted value across restart."
```

Yield-safety detail worth porting: `pending_delete_rowid` is stored on the DRIVER, not as phase payload — "so a yield mid-cursor.delete() doesn't lose the rowid across re-entry." Passive mode records deletes into `compacted` and drains them in the publish window instead of purging inline.

**Flow:** plan pending seqs → per seq: seek watermark end → capture key → scan from start deleting every row whose key ≠ watermark → paired version-chain purge → next seq.
**Invariant:** B-tree delete and version-chain purge must travel together; watermark choice is direction-dependent; never block the executor.
**Probe:** `test_sequence_watermark_tracks_nextval_allocations` (tests.rs:6186); `test_sequence_watermark_reader_never_skips_committed_rows_fuzz` (:6234); `test_sequence_watermark_tracks_lowest_active_allocation` (:6120).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "SeqCompactDriver CompactSequences sequence watermark", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-layer paired delete + resumable scan phases verbatim for any hot-counter reclamation; adapt watermark semantics to your sequence directions; omit if your counters live outside MVCC. Coverage caveat: none material — probes are direct tests.
