<!-- capsule-v2 -->
# Merge-optimizer greedy batching — how do you pick which segments to compact so compaction always reduces the segment count?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** Given a live set of segments and a target segment count, how are merge batches chosen so that (a) each merged output stays under the size threshold and (b) the operation provably reduces the number of segments instead of trading two for two?

## Planner with a shared remaining set; greedy ascending fill with a held first pair
**Path/Symbol:** `lib/shard/src/optimizers/merge_optimizer.rs`: doc (:16-43) + `MergeOptimizer::plan_optimizations` (:110-160). Shared machinery: `lib/shard/src/optimizers/segment_optimizer.rs`: `OptimizationPlanner` (:421-482), free `plan_optimizations` (:489-507), test wrapper `plan_optimizations_for_test` (:111-142). Candidate source: `SegmentHolder::iter_original` (`lib/shard/src/segment_holder/mod.rs` :199-204) — proxies are filtered out before planning.
**Signature:** `fn plan_optimizations(&self, planner: &mut OptimizationPlanner)`; `pub fn plan(&mut self, segments: Vec<SegmentId>)`; `pub fn expected_segments_number(&self) -> usize`.
**Data Shape:** candidates = `(SegmentId, max_available_vectors_size_in_bytes)` for every ORIGINAL segment still in `planner.remaining()`, sorted ASCENDING by size; `scheduled: Vec<(Option<Arc<Optimizer>>, Vec<SegmentId>)>` accumulates batches; `running` = count of in-flight optimizations (each assumed to produce one new segment).

### Decisive source
```rust
// merge_optimizer.rs :129-159 — the whole algorithm
let mut first_batch = None;
let mut taken_candidates = 0;
let mut last_candidate =
    (planner.expected_segments_number() + 2).saturating_sub(self.default_segments_number);
while taken_candidates < last_candidate.min(candidates.len()) {
    let batch = candidates[taken_candidates..last_candidate.min(candidates.len())]
        .iter()
        .scan(0, |size_sum, &(segment_id, size)| {
            *size_sum += size;
            (*size_sum < threshold).then_some(segment_id)   // strict < : output must stay under threshold
        })
        .collect_vec();
    if batch.len() < 2 { return; }                          // nothing worth merging
    let is_first_batch = taken_candidates == 0;
    taken_candidates += batch.len();
    last_candidate += 1;                                    // each planned batch frees one slot
    if is_first_batch && batch.len() < 3 {
        // First batch has length 2. To guarantee that the number of
        // segments will be reduced, we need another batch.
        // So, hold the first batch until we find the second one.
        first_batch = Some(batch);
        continue;
    }
    if let Some(first_batch) = first_batch.take() { planner.plan(first_batch); }
    planner.plan(batch);
}
// segment_optimizer.rs :470-472 — in-flight work counts against the target
pub fn expected_segments_number(&self) -> usize {
    self.remaining.len() + self.scheduled.len() + self.running
}
// :475-482 — claiming a batch removes it from everyone else's view
pub fn plan(&mut self, segments: Vec<SegmentId>) {
    debug_assert!(!segments.is_empty());
    for segment_id in &segments {
        let removed = self.remaining.remove(segment_id).is_some();
        debug_assert!(removed);
    }
    self.scheduled.push((self.optimizer.clone(), segments));
}
```

**Flow:** collect original-segment sizes → sort ascending → compute the candidate window `last_candidate = expected_segments_number + 2 - default_segments_number` (the +2 accounts for the new appendable segment Qdrant may create when the last appendable input is merged, per the doc diagram) → repeatedly fill a batch by running-sum scan while the sum stays strictly under `max_segment_size_kb` → a batch of <2 ends planning entirely → a first batch of exactly 2 is held until a second batch exists (2→1+∅ does not reduce the count; `[A B][C D]→∅XY` does) → each accepted batch is claimed via `planner.plan`, shrinking `remaining` so later optimizers in the ordered loop cannot double-book it, and widening the window by one.
**Invariant:** (1) every scheduled batch merges ≥2 segments AND the overall plan reduces the expected segment count — a lone 2-batch is never emitted; (2) batch membership is decided on the SHARED remaining set, so optimizer order matters and no segment is planned twice; (3) in-flight optimizations count against the target via `expected_segments_number`, so planning converges as runs finish; (4) the greedy fill uses strict `< threshold` so the merged output cannot itself exceed the size threshold.
**Probe:** `lib/collection/src/collection_manager/optimizers/merge_optimizer.rs::test_merge_optimizer_test_table` (:253-288) pins the algorithm against TEST_TABLE (:213-252): 24 hand-computed `(default_segments_number, max_segment_size_kb)` cases over 21 shuffled 10–30 KiB segments assert the exact batch strings (e.g. `(1, 54)` ⇒ `"10+11+12+13 =46 | 14+15+16 =45 | 17+18 =35 | …"`), including held-first-pair and window-shrink behavior; `test_max_merge_size` (:101-136) pins the threshold gate (100 KB ⇒ empty plan, 200 KB ⇒ exactly one 3-batch); `test_merge_optimizer` (:139-211) pins the end state (4 small merged into one 19-point segment, 3 large untouched, sources deleted only after a flush).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "MergeOptimizer plan_optimizations OptimizationPlanner expected_segments_number first_batch default_segments_number", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shared-remaining planner (claim-on-plan prevents double booking across an ordered optimizer list), the ascending greedy fill with strict threshold, the held-first-pair rule, and counting in-flight work against the target. Adapt the +2 window constant to your own appendable-segment creation policy. Omit the Rust-specific BTreeMap ordering if your host plans in a different order — but keep the claim-on-plan invariant or you will double-book segments.
