<!-- capsule-v2 -->
# Vector-IVF threshold algebra — how does a posting scan prune rows it cannot beat, without ever missing a true neighbor?

**Source:** turso (MIT) `main@1654d1587fab` ($REFERENCE_ROOT/turso); Codebase Memory `turso`. **Question:** Given only per-component stats and each row's denormalized sum, how do you decide mid-scan that a candidate's best-case Jaccard cannot enter the top-K + delta?

## Upper-bound Jaccard from sums alone; two acceptable ranges for a row's stored sum
**Path/Symbol:** `core/index_method/toy_vector_sparse_ivf.rs`: `VectorSparseInvertedIndexSearchState` (:231-296), CollectComponentsSeek sort/take (:1094-1151), Seek-state threshold block (:1228-1310).
**Signature:** components sorted by `ScanOrder` (:298-302): `DatasetFrequencyAsc` ⇒ `sort_by_key(|(c,_)| c.cnt)` (low-cardinality first :1116-1119) or `QueryWeightDesc` (default) ⇒ `sort_by_key(|(_,w)| Reverse(FloatOrd(*w)))` (high-impact first :1120-1124); scan breadth = `ceil(len × scan_portion)` (:1126).
**Data Shape:** `Q` = query Σ values; `M` = Σ of remaining scanned components' `max` bounds, clamped to Q (`let m = c.iter().map(|c| c.max).sum::<f64>().min(*sum)` :1262); `L` = a candidate row's stored sum; `best = 1 − max_threshold_distance` = worst similarity currently in the top-K (:1270).

### Decisive source
```rust
// toy_vector_sparse_ivf.rs:1252-1261 — the derivation comment (verbatim):
// we estimate jaccard distance with the following approach:
// J = min(L, M1 + M2 + ... + Mr) / (Q + N - min(L, M1 + M2 + ... + Mr))
// so we want J > best + delta; define M1 + M2 + ... + Mr = M
// J = min(L, M) / (Q + L - min(L, M)) > best + delta
// we need to consider two cases:
// 1. L < M: J = L / (Q + L - L) > best + delta => L > (best + delta) * Q
// 2. L > M: J = M / (Q + L - M) > best + delta => L < M / (best + delta) - (Q - M)
// so we have two intervals: [(best + delta) * Q .. M] and [M .. M / (best + delta) - (Q - M)]
// to simplify code for now we will pick upper bound from second range if it is not degenerate, otherwise check first range
```

**Flow:** gate active only once `distances.len() >= limit` (:1268) — before top-K is full, everything is evaluated. Threshold selection (:1274-1283): if `m <= second_range_r` take `sum_threshold = second_range_r`; elif `first_range_l <= m` take `sum_threshold = m`; else `sum_threshold = Some(-1.0)` (**prune-all**: every real sum exceeds −1, so the Read arm bails immediately). The Read arm then stops a posting run when `row.position != component` OR `row.sum > sum_threshold` (:1369-1377); the posting seek itself is `GE { eq_only: false }` (:1318) because it starts a RANGE scan, unlike insert/delete's `eq_only:true` point lookups.
**Invariant:** the pruning predicate is one-directional by construction — a row is skipped only if its MAXIMUM possible similarity (all shared mass realized: min(L,M)) still fails `best + delta`, so recall of true neighbors is never lost; precision degrades gracefully with `delta`. This one-sidedness is exactly what the fuzz harness pins.
**Probe:** executed at HEAD: `test_vector_sparse_ivf_fuzz` (tests/integration/index_method/mod.rs:378-499) sweeps `delta ∈ {0.0,0.01,0.05,0.1,0.5}` over 200 mixed ops vs brute force; anchors verified byte-exact: threshold comment :1253-1261, `-1.0` arm :1282, `eq_only: false` :1318, `ceil` take :1126.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "ScanOrder sum_threshold CollectComponentsSeek", limit: 10 });
```
resolves `ScanOrder` :299-302, search-state enum :231-296, `query_start` :1046-1589 line-exact.

## Verdict
Adopt the sum-based upper bound as THE approximation mechanism — it needs no extra metadata beyond what insert already maintains. Adopt the exact interval choice order (non-degenerate second range preferred). Adapt `M`'s clamp and ordering heuristics to your stats quality. Omit re-deriving intervals at runtime per row — turso computes one threshold per component visit. Coverage: no_recorded_issue.
