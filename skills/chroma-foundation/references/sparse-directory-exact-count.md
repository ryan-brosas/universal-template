<!-- capsule-v2 -->
# Sparse directory exact count — Why must an overflowing document frequency be left UNCOUNTED instead of saturated?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** The v1 directory format stores posting counts as u32 — what should a writer do when the true count exceeds u32::MAX?

## with_exact_count
**Path/Symbol:** `rust/index/src/sparse/maxscore.rs:with_exact_count` (:73-86); consumed by `MaxScoreWriter::commit` pass 2; reader side `count_postings` (:622+) falls back to estimation when count is missing.
**Signature:** `fn with_exact_count(encoded_dim: &str, directory: Directory, count: u64) -> Directory`.
**Data Shape:** Version-1 directories carry an exact posting count; version-0 (legacy) carry none and readers estimate from block structure.

### Decisive source
```rust
/// A dimension holds at most one posting per u32 offset, so the count
/// can only exceed `u32::MAX` in the degenerate case where all 2^32
/// offsets carry the dimension (or if an already-corrupt stored count
/// was carried forward). Rather than fabricate a saturated count —
/// which [`MaxScoreReader::count_postings`] would report as a real
/// document frequency, collapsing the term's IDF to ~0 and silently
/// dropping it from scoring — leave the directory uncounted (legacy
/// version-0 semantics) so readers fall back to the estimate path.
fn with_exact_count(encoded_dim: &str, directory: Directory, count: u64) -> Directory {
    match u32::try_from(count) {
        Ok(count) => directory.with_posting_count(count),
        Err(_) => { tracing::warn!(...); directory }
    }
}
```

**Flow:** on commit each dimension's exact entry count is attached when representable; overflow ⇒ log + attach nothing. Readers treat `MissingPostingCount` as "estimate" — never as zero.
**Invariant:** A stored statistic must never be a fabricated plausible value; degrade to the weaker-but-honest representation instead. Corrupt counts are not laundered: suffix-rewrite underflow triggers a header recount and self-heals on write (:268-296).
**Probe:** in-file tests `with_exact_count_stores_fitting_count` / `with_exact_count_overflow_leaves_uncounted` (`rust/index/src/sparse/maxscore.rs` tests module, asserts `MissingPostingCount` variant); battery anchor mx.exact_count GREEN.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "with_exact_count with_posting_count MissingPostingCount count_postings", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the refuse-to-saturate rule for any bounded statistics field (df, cardinalities, sizes); adapt the fallback path your readers take; omit Spanner-specific directory storage details.
