<!-- capsule-v2 -->
# Stale HasVector read redaction — how do queries naming a deleted/renamed vector match nothing instead of reading wrapped stale bytes?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** While a proxy holds pending vector-name deletions/re-creations, how must filters and WithVector requests be rewritten before delegating reads to the wrapped segment?

## Always-false checker swap + WithVector selector rewrite, clone only on taint
**Path/Symbol:** `lib/shard/src/proxy_segment/vector_name_changes.rs`: `AlwaysFalseChecker` (:20-35), `is_wrapped_data_stale` (:163-167), `redact_with_vector` (:192-243), `redact_filter` (:256-263) + `filter_has_stale_has_vector` (:267-307) + `redact_filter_inplace`/`redact_conditions_inplace` (:309-355).
**Signature:** `pub fn redact_filter<'a>(&self, filter: &'a Filter) -> Cow<'a, Filter>`; `pub fn redact_with_vector<'a>(&self, with_vector: &'a WithVector, wrapped_config: &SegmentConfig) -> Cow<'a, WithVector>`.
**Data Shape:** taint set derived from intents where `taints_wrapped()` (Absent or superseding Present); `Cow::Borrowed` when clean, `Cow::Owned` only after an actual rewrite.

### Decisive source
```rust
// :20-23 — the replacement condition:
// A CustomIdCheckerCondition that never matches any point. Used to replace
// HasVector conditions that reference a vector the proxy has deleted or
// superseded — the wrapped segment's storage for that vector is stale, so the
// condition must evaluate to `false` for every point.
fn check(&self, _point_id: ExtendedPointId) -> bool { false }
fn estimate_cardinality(&self, _points: usize) -> CardinalityEstimation {
    CardinalityEstimation::exact(0)
}
// :256-262 — cheap scan first, clone only on hit:
if !self.filter_has_stale_has_vector(filter) { return Cow::Borrowed(filter); }
let mut owned = filter.clone();
self.redact_filter_inplace(&mut owned);
```

**Flow:** read arrives at the proxy → `read_filtered`/search first pass the filter through `redact_filter`: a recursive scan over should/must/must_not/min_should (descending into Nested and inner Filter) looks for `HasVector` names whose wrapped data is tainted; if found, each such condition is replaced with `CustomIdChecker(AlwaysFalseChecker)` so `must: [{has_vector: "v_dropped"}]` matches zero points instead of leaking wrapped stale storage → `WithVector` requests are rewritten by `redact_with_vector`: `Bool(false)` untouched; `Bool(true)` EXPANDS against wrapped_config minus tainted names (pending brand-new creates excluded — asking wrapped for them would error); explicit `Selector` drops tainted names, skipping allocation when none requested is tainted.
**Invariant:** (1) no query may reach wrapped stale vector bytes through filter, retrieval parameter, or cardinality estimate — the always-false checker also reports exact(0) so planner math stays consistent; (2) untouched requests return Borrowed — zero-cost common path; (3) expansion of "all vectors" uses the WRAPPED config as truth for what Bool(true) means.
**Probe:** direct test `lib/shard/src/proxy_segment/tests.rs::test_read_filter` (:330-399) pins the sibling deleted-points redaction path (`must_not` id mask shrinks results exactly); the stale-HasVector swap itself has no dedicated upstream unit test — pinned by direct read of :20-355 plus the `read_filtered` call site (`segment_entry.rs` :398: `filter.map(|f| self.changed_vector_names.redact_filter(f))`). Recorded caveat in verification.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "redact filter HasVector custom id checker always false with vector tainted", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt query-redaction-before-delegation whenever reads can race schema changes: replace tainted predicates with provably-empty checkers rather than filtering results afterwards. Adapt the condition type to your filter AST. Omit qdrant's Cow borrow fast-path if your queries already clone filters per request.
