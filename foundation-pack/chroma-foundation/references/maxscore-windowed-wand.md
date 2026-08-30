<!-- capsule-v2 -->
# MaxScore windowed WAND — How does sparse top-k retrieval prune without materializing every posting?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** What is the exact window/threshold/essential-term choreography a porter must reproduce for MaxScore over blockfile postings?

## MaxScoreReader.query
**Path/Symbol:** `rust/index/src/sparse/maxscore.rs:MaxScoreReader::query` (:709-989); helpers `filter_competitive` family (:1004-1143), `TermState` (:992).
**Signature:** `query(&self, query_vector: impl IntoIterator<Item=(u32,f32)>, k: u32, mask: SignedRoaringBitmap) -> Result<Vec<Score>, MaxScoreError>`.
**Data Shape:** Per-dimension directories carry `max_offsets[]` + `max_weights[]` (block upper bounds); terms = query dimensions with `max_score = query_weight * dim_max_weight`; accumulators sized `WINDOW_WIDTH=4096` (bitmap of 64 words) reset per window.

### Decisive source
```rust
terms.sort_by(|a, b| a.max_score.total_cmp(&b.max_score));   // once, ascending
// ── per window ──
for t in terms.iter_mut() {
    t.window_score = t.query_weight * t.cursor.window_upper_bound(window_start, window_end);
}
terms.sort_unstable_by(|a, b| a.window_score.total_cmp(&b.window_score));
let mut essential_idx = terms.len();
let mut prefix = 0.0f32;
for (i, t) in terms.iter().enumerate() {
    prefix += t.window_score;
    if prefix >= threshold { essential_idx = i; break; }
}
...
for term in terms[essential_idx..].iter_mut() {          // HIGH-score tail drains fully
    term.cursor.drain_essential(window_start, window_end, term.query_weight, &mut accum, &mut bitmap, &mask);
}
...
let cutoff = threshold - remaining_budget;               // non-essential budget pruning
filter_competitive(&mut cand_docs, &mut cand_scores, cutoff);
```

**Flow:** three-batch IO pipeline first (directories for all dims → eager View cursors when ≤`MAX_VIEW_BLOCKS=2` blocks else Lazy cursors → post-threshold loads pruned by block upper bounds), then 4096-wide windows: re-sort by window bound, prefix-sum from the SMALLEST term to split essential (tail, accumulated unconditionally) vs non-essential (head, scored only on surviving candidates with a shrinking `remaining_budget`, iterated in REVERSE so the biggest term's filter runs first), push survivors into TopKHeap which raises the threshold mid-window. SIMD `filter_competitive` (AVX512/SSE2/NEON + scalar fallback) is pinned equal to scalar by an in-file test.
**Invariant:** Skipping is only ever justified by upper bounds that are ≥ true contributions; mask (`SignedRoaringBitmap`) filters at cursor level; empty-window windows skip Phase-2 entirely.
**Probe:** `/tmp/chroma-p1/probe_battery.py` mx.* anchors (GREEN). Direct tests: `rust/index/tests/maxscore/ms_06_correctness.rs`, `ms_09_recall.rs`, `ms_15_multi_window.rs`, `ms_19_proptest_invariants.rs` (`cargo test -p chroma-index --test maxscore` — runner available but full build not run this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "MaxScoreReader query window threshold essential drain_essential", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the windowed-WAND decomposition (it is the hybrid-search scoring primitive behind Chroma's sparse leg); adapt window width and cursor loading strategy to your storage; omit the SIMD paths until correctness parity is proven against scalar (upstream keeps a test for exactly that).
