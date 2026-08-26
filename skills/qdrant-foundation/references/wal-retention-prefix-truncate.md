<!-- capsule-v2 -->
# WAL lifecycle: retirement, retention, prefix truncate — how do segments rotate and get garbage-collected without losing contiguity?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `ext-qdrant`. **Question:** How does the Wal move entries from open→closed segments, retain history, and validate recovery when a rename wasn't durable?

## Segment rotation with recovery-time contiguity repair
**Path/Symbol:** `lib/wal/src/lib.rs`: `WalOptions` (:23-44, 32MiB default capacity, `retain_closed=1`), `Wal::with_options` recovery (:123-263), `retire_open_segment` (:265-292), `append` (:294-308), `truncate` (:351-402), `prefix_truncate` (:410-446), `open_segment_start_index` (:449-455), `find_closed_segment` (:457-467), `close_segment` rename (:535-546).
**Signature:** `pub fn append<T: Deref<Target=[u8]>>(&mut self, entry: &T) -> Result<u64>` (returns absolute index); `pub fn prefix_truncate(&mut self, until: u64) -> Result<()>`.
**Data Shape:** directory holds `open-{id}` + `closed-{start_index}` files; in-memory: one open segment, ordered closed list carrying start_index, async `SegmentCreatorV2` pre-creating empties (`segment_queue_len`).

### Decisive source
```rust
// append: retire on overflow, but an EMPTY oversized entry stays in place and grows the segment
if !self.open_segment.segment.sufficient_capacity(entry.len()) {
    if !self.open_segment.segment.is_empty() { self.retire_open_segment()?; }
    self.open_segment.segment.ensure_capacity(entry.len())?;
}
// recovery: stranded written-open segment (rename not durable) is closed at the running index
if !segment.segment.is_empty() {
    let stranded_segment = open_segment.take();
    open_segment = Some(segment);
    if let Some(segment) = stranded_segment {
        let closed_segment = close_segment(segment, next_start_index)?;
        next_start_index += closed_segment.segment.len() as u64;
        closed_segments.push(closed_segment);
    }
}
// prefix_truncate: always keep at least one closed segment; early-return below the floor
let retain_start_index = self.closed_segments.len().saturating_sub(self.retain_closed.get());
```

**Flow:** append → capacity check → retire (swap in pre-created segment, join previous flush thread, spawn `flush_async` on the retired one, rename to `closed-{start_index}` where start_index = last closed's end, pop empty closed tail if any) → return `open_start_index + local_index` → readers binary-search closed ranges then fall through to open → `prefix_truncate(until)` deletes whole closed segments strictly before `until` but keeps ≥ `retain_closed` of them → `truncate(from)` may delete whole closed segments or cut inside one (flushing after in-segment truncation) → recovery validates closed segments are non-overlapping AND contiguous (`Ordering::Less/Equal/Greater` walk), else InvalidData.
**Invariant:** (1) index space is contiguous across segments — derived solely from `closed.last().start+len`, never stored per-entry; (2) at most one written open segment may exist on disk; extra written ones become closed at recovery (durability of rename is NOT assumed); (3) empty closed segments are garbage collected at retirement; (4) prefix truncation never removes the last closed segment even when asked; (5) dir-level flock (`fs4::FileExt::try_lock`, UFCS for Android) guards single-writer.

**Probe:** `grep -c "retain_closed\|prefix_truncate" lib/wal/src/lib.rs` → prints `48`. Direct tests: parametric `check_prefix_truncate` (:948), `test_prefix_truncate_parametric` (:1105), `run_test_with_retain_closed` (:1051), reopen/recovery suite `check_reopen` (:842), exclusive-lock test (:1222).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-qdrant", query: "retire_open_segment prefix_truncate retain_closed close_segment SegmentCreatorV2", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt rotation naming, contiguity validation ladder, stranded-open repair, keep-one-closed retention. Adapt pre-creation queue depth and locking primitive per host. Omit Windows proxy-file lock workaround unless targeting Windows.
