<!-- capsule-v2 -->
# FTS foreground merge budget — how do you run segment maintenance synchronously inside a transaction without unbounded latency?

**Source:** turso (MIT) `main@d9266124f` ($REFERENCE_ROOT/memory/turso); Codebase Memory `turso`. **Question:** Why disable tantivy's background merges, and what makes exactly-one-bounded-merge-per-commit the safe replacement?

## Third-party policy output is untrusted; smallest-first; defer beyond budget
**Path/Symbol:** `core/index_method/fts.rs`: `automatic_merge_policy` (:3104-3114), `bounded_merge_candidate` (:3116-3177), `commit_writer_with_maintenance` (:3184-3237), constants `FTS_MERGE_FACTOR=8` (:74), `FTS_DELETED_DOCS_MERGE_THRESHOLD=0.3` (:79), `FTS_MAX_SYNC_MERGE_DOCS=64_000` (:82), `FTS_MAX_SYNC_MERGE_BYTES=32MiB` (:86).
**Signature:** `fn bounded_merge_candidate(policy: &LogMergePolicy, segment_metas: &[SegmentMeta], max_source_docs: u64, max_source_bytes: u64, file_size: impl FnMut(&Path) -> Option<u64>) -> Option<Vec<SegmentId>>`.
**Data Shape:** candidates iterate the policy's levels in REVERSE (smallest eligible level first — "maintaining the smallest eligible level first prevents fresh tiny segments from piling up"); within a level sort by max_doc ascending and take FTS_MERGE_FACTOR=8 ("taking the first eight of Tantivy's largest-first list picks exactly the eight most likely to blow the foreground budget").

### Decisive source
```rust
// fts.rs:3107-3113 + 3149-3155 — policy tuning and distrust (verbatim):
policy.set_min_num_segments(FTS_MERGE_FACTOR);
// Treat one-document segments as their own level. Tantivy's default
// clips all segments below 10k docs into one level, which repeatedly
// rewrites large merged segments under small-commit workloads.
policy.set_min_layer_size(1);
...
for segment_id in &segment_ids {
    // The merge policy is third-party code; do not trust it to
    // return only segments it was given.
    let Some(segment_meta) = segment_metas.iter().find(|meta| meta.id() == *segment_id)
    else {
        tracing::error!("merge policy returned an unknown FTS segment; skipping merge");
        return None;
    };
```

**Flow:** writer.commit() (documents durable in tantivy's view) → list searchable_segment_metas → size each candidate source segment through the NEWEST byte-length source: pending_mutations first (directory writes update the catalog before they enter the resumable btree flush), then flushing_writes, then committed catalog (:3198-3216) → accept the FIRST candidate whose total docs ≤ 64k AND bytes ≤ 32MiB; otherwise defer (debug log "deferring merge beyond foreground budget") → writer.merge(...).wait() + commit again (:3229-3235). Larger compaction remains available ONLY via OPTIMIZE INDEX where the caller opts into unbounded latency (:83-85 comment).
**Invariant:** merges are driven synchronously because "Tantivy's background merge workers cannot safely drive our directory: directory mutations must be captured and persisted by the cursor's resumable BTree flush inside the current Turso transaction" (:3179-3182) — porting background merges breaks crash consistency, not just latency. min_layer_size=1 exists because tantivy's default level clipping re-rewrites large segments under small-commit workloads. The deleted-docs ratio (0.3) reclaims space without dedicated vacuum.
**Probe:** `grep -n 'FTS_MAX_SYNC_MERGE_DOCS\|FTS_MAX_SYNC_MERGE_BYTES\|set_min_layer_size' core/index_method/fts.rs` hits :82/:86/:3111; behavior pinned by fuzz/external-merge-adjacent suites and tests/integration/index_method/ segment_count stats (:474).
**Retrieve:** search_graph "bounded_merge_candidate LogMergePolicy commit_writer_with_maintenance" resolves `turso.core.index_method.fts.FtsCursor.bounded_merge_candidate` core/index_method/fts.rs :3116-3177.

## Verdict
Adopt synchronous one-bounded-merge maintenance with smallest-level-first selection, byte-exact budget accounting including PENDING writes, and explicit distrust of third-party merge-policy output. Adapt thresholds to host commit cadence. Omit tantivy LogMergePolicy internals. Coverage: no_recorded_issue on fts.rs.
