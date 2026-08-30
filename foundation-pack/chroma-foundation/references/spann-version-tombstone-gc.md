<!-- capsule-v2 -->
# SPANN version tombstone GC — How do deletes propagate to posting lists and when is head garbage collected?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** In the SPANN fast writer, what does version=0 mean, why does update-of-deleted error, and when does GC rebuild the head HNSW?

## FastSpannIndexWriter add/update/delete + GC
**Path/Symbol:** `rust/index/src/spann/fast_writer.rs:add` (:1590-1606), `update` (:1608-1637), `delete` (:1639-1643), `eligible_to_gc` (:1667-1683), `garbage_collect_heads` (:1685-1772), `pl_garbage_collect_random_sample` (:1774-1819).
**Signature:** `delete(&self, id: u32)` = `self.versions.insert(id, 0); self.embeddings.remove(&id);`; `update` errors with `VersionNotFound` when current version == 0.
**Data Shape:** `versions: DashMap<u32, u64>` (monotone per id; 0 reserved for deleted), `embeddings: DashMap<u32, Arc<[f32]>>`, cosine space normalizes vectors at BOTH add and update before storage.

### Decisive source
```rust
pub async fn delete(&self, id: u32) -> Result<(), SpannIndexWriterError> {
    self.versions.insert(id, 0);
    self.embeddings.remove(&id);
    Ok(())
}
// update():
if curr_version == 0 {
    tracing::error!("Trying to update a deleted point {}", id);
    return Err(SpannIndexWriterError::VersionNotFound);
}
...
pub fn eligible_to_gc(&mut self, threshold: f32) -> bool {
    let (len_with_deleted, len_without_deleted) = ...hnsw_index.(len_with_deleted(), len());
    if (len_with_deleted as f32)
        < ((1.0 + (threshold / 100.0)) * (len_without_deleted as f32)) { return false; }
    true
}
```

**Flow:** writes append to posting lists stamped with the NEW version; scrubbing later drops entries whose stored version < current (tombstones make stale postings invisible without immediate list rewrites). GC triggers only above a delete-ratio threshold; `garbage_collect_heads` builds a FRESH HNSW from non-deleted heads (doubling capacity on demand), stores it in `cleaned_up_hnsw_index`, and swaps atomically; posting-list GC samples heads randomly (`pl_garbage_collect_random_sample`) for amortized maintenance. Head deletion detection relies on hnswlib get() failure (`is_head_deleted`).
**Invariant:** Version monotonicity per id is the visibility oracle — a porter who treats delete as "remove from posting list now" loses the crash-safe deferred-scrub property; update-after-delete must be a hard error, not an implicit resurrect.
**Probe:** `/tmp/chroma-p1/probe_battery.py` sw.* anchors (tombstone insert, update-error arm, cosine normalize ×2 sites, GC formula — GREEN). Direct tests: `rust/index/tests/spann/` fast-writer suites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "FastSpannIndexWriter versions delete eligible_to_gc garbage_collect_heads scrub_posting_list", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt version-tombstone deletion + ratio-gated GC for any posting-list index; adapt thresholds (percent-based) and sampling rate; omit metric-server plumbing (`SpannMetrics`) and distributed commit coordination.
