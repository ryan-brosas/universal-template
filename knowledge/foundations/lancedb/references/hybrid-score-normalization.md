<!-- capsule-v2 -->
# Hybrid score normalization — how do rank() and normalize_scores() behave at empty, constant, and near-equal edges?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** What do the pre-fusion transforms do when scores are missing, degenerate, or differ by less than float noise?

## Edge-condition semantics
**Path/Symbol:** `rust/lancedb/src/query/hybrid.rs:rank` (19–58) and `rust/lancedb/src/query/hybrid.rs:normalize_scores` (123–174).
**Signature:** `pub fn rank(results: RecordBatch, column: &str, ascending: Option<bool>) -> Result<RecordBatch>`; `pub fn normalize_scores(results: RecordBatch, column: &str, invert: Option<bool>) -> Result<RecordBatch>`.
**Data Shape:** Operate in-place on the named Float32 score column (`_distance` for vector, `_score` for FTS); missing column → InvalidInput error embedding the list of found columns; empty batch → returned untouched.

### Decisive source
```rust
let max = max(&scores).unwrap_or(0.0);
let min = min(&scores).unwrap_or(0.0);
// this is equivalent to np.isclose which is used in python
let rng = if max - min < 10e-5 { max } else { max - min };
// if rng is 0, then min and max are both 0 so we just leave the scores as is
if rng != 0.0 {
    let tmp = div(&sub(&scores, &Float32Array::new_scalar(min))?, &Float32Array::new_scalar(rng))?;
    scores = downcast_array(&tmp);
}
if invert.unwrap_or(false) {
    let tmp = sub(&Float32Array::new_scalar(1.0), &scores)?;
    scores = downcast_array(&tmp);
}
```

**Flow:** `rank()` swaps the score column for arrow competition ranks (default ASCENDING; `ascending=Some(false)`/descending for distances); `normalize_scores()` computes range, picks the divisor by the `< 10e-5` closeness rule, divides `(s-min)/rng` when `rng != 0.0`, optionally inverts with `1-s`.
**Invariant:** The closeness rule only changes the DIVISOR (falls back to `max`), it does not skip normalization: all-equal scores like 2.1 still become 0.0 via `(max-min)/max`, while all-zero scores stay 0.0 only because `rng == 0.0` exactly. Near-equal values (1.0 vs 0.9999999) KEEP their tiny rounding difference — upstream test asserts `1.0 - 0.9999999` survives. A porter who "cleans up" the branch to `if max==min {skip}` flips the all-constant case from 0.0 to unchanged.
**Probe:** `cargo test -p lancedb --lib query::hybrid::test::test_normalize_scores` (pins constant→zeros, rounding-preservation, invert, empty, and the missing-column error message).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "normalize_scores rank query_schemas hybrid", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier divisor rule and the empty-batch short-circuit verbatim (they pin Python-parity behavior — comments say "equivalent to np.isclose … used in python"); adapt arrow kernels (min/max/div/sub/rank) to host equivalents; omit `with_field_name_replaced`/`query_schemas` schema-synthesis only if the porter has no empty-arm concept — otherwise adopt it too (it is what lets fusion proceed when one arm returns nothing). Direct-test coverage present (test_rank + test_normalize_scores).
