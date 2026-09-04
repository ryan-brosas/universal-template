<!-- capsule-v2 -->
# History store & drift severity — local SQLite snapshots where crawlability loss outranks score math

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you persist per-URL audit trends and classify regressions so the worst failure always wins?

## Canonicalized snapshot rows + precedence-ordered severity ladder
**Path/Symbol:** `src/geo_optimizer/core/history.py:HistoryStore` (63–275), `canonicalize_history_url` (28–36); `src/geo_optimizer/core/drift_detector.py:compute_semantic_drift` (18–57), `_classify_severity` (60–79).
**Signature:** `save_audit_result(result, retention_days=90) -> HistoryEntry`; `build_history_result(url, limit=12, retention_days=90) -> HistoryResult`; `compute_semantic_drift(entry_before, entry_after) -> SemanticDriftDelta`.
**Data Shape:** table `audit_history(canonical_url, domain, recorded_at, score, band, http_status, recommendations_count, robots_score … brand_entity_score)` with `(canonical_url, recorded_at DESC)` index; deltas computed in-memory on read.

### Decisive source
```python
def _classify_severity(delta, score_delta: int) -> str:
    if score_delta <= -_SCORE_DROP_CRITICAL:        # -15
        return "critical"
    # Crawlability loss is checked BEFORE the softer thresholds — it's the single
    # worst regression this function detects and must win even when it coincides
    # with a smaller change that would otherwise match "warning" first and mask it.
    if not delta.crawlable_after and delta.crawlable_before:
        return "critical"
    if score_delta <= -_SCORE_DROP_WARNING:         # -5
        return "warning"
    if delta.schema_types_removed:
        return "warning"
    if delta.category_deltas:
        return "info"
    if score_delta < 0:
        return "info"
    return "none"
```

**Flow:** URL canonicalization (lowercase scheme/host, strip trailing slash except root) keys every lookup → save inserts then prunes by `julianday('now') − julianday(recorded_at) > retention_days` → history read computes pairwise deltas newest→oldest (`entry.score − previous.score`), regression flag = latest < previous. Drift adds category-level delta map, a `schema_richness_degraded` hint when schema drops >3, and crawlability proxies from robots-score 1↔0 transitions.
**Invariant:** Severity is a PRECEDENCE ladder, not a score — ordering the checks differently lets a −6 warning mask total bot-blocking. The store persists only the eight SCORING categories (+totals) so schema evolution never breaks old rows; retention pruning runs on both write and read paths.
**Probe:** `tests/test_history.py::test_save_and_build_history` + `tests/test_drift_detector.py::test_crawlability_loss_is_critical` class (ladder precedence; `PYTHONPATH=src pytest tests/test_history.py tests/test_drift_detector.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "compute_semantic_drift severity", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt canonical-key snapshots + read-time deltas + precedence severity for any trend tracker; adapt thresholds; omit the SQLite specifics if you have another store but keep prune-on-write.
