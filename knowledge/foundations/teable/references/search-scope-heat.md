<!-- capsule-v2 -->
# Search scope heat policy — how do observation windows decide WHICH field-set deserves its own expression index?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Given per-query observations, how do you rank "hot" search scopes (specific field subsets) so only sustained, expensive workloads get a scoped GIN recommendation?

## SearchScopeHeatPolicy + scoped recommendation bridge
**Path/Symbol:** `packages/v2/table-query-ops/src/searchScopeHeat.ts` — `SearchScopeHeatPolicy.evaluate` (:89–202), defaults (:19–26: minRequestCount 100, minSlowCount 20, minTotalDurationMs 30_000, minEstimatedRows 10_000, maxScopes 5), heatScore formula (:163–171); consumer `PostgresTableSearchVectorAdvisor.buildScopedExpressionRecommendations` (searchVector.ts :649–716) + `evaluateScopeHeat` (:717–723).
**Signature:** `evaluate({observations: TableQueryObservationWindow[], estimatedRows}): Result<SearchScopeHeatReport, DomainError>`; entry = `{scopeKey, searchedFieldIds, searchMode, requestCount, slowCount, timeoutCount, totalDurationMs, maxDurationMs, averageDurationMs, heatScore 0-100, hot, reasonCodes, nextAction}`.
**Data Shape:** scopeKey = `stableHash({tableId, searchedFieldIds sorted-deduped, searchMode, languageConfig})` — identical field-SET with different order aggregates to one bucket.

### Decisive source
```ts
const workloadQualified =
  scope.requestCount >= this.config.minRequestCount ||
  scope.slowCount >= this.config.minSlowCount;
const costQualified = scope.totalDurationMs >= this.config.minTotalDurationMs;
const hot = input.estimatedRows >= this.config.minEstimatedRows &&
            workloadQualified && costQualified;
// heatScore: capped additive log-scales, never raw sums:
Math.min(100, Math.round(
  Math.min(25, Math.log2(scope.requestCount + 1) * 4) +          // volume ≤25
  Math.min(40, Math.log2(scope.totalDurationMs / 1000 + 1) * 8) + // duration ≤40
  Math.min(20, slowRatio * 100) +                                 // slow ratio ≤20
  (input.estimatedRows >= this.config.minEstimatedRows ? 15 : 0)  // table size ≤15
));
```

**Flow:** keep only `queryKind === 'search'` observations targeting an explicit field subset (`allFields === false`) → aggregate by stable-hash scope key → compute reason codes and the three-factor AND for `hot` → sort hot-first then heatScore then totalDuration → cap at maxScopes → advisor maps each hot scope to a scoped-expression index candidate ONLY if every searched field is individually covered by the global vector (`scopeFields.length !== scopeFieldIds.size ⇒ drop`), names it via `buildScopedExpressionIndexNames`, validates with HypoPG plan evidence (skipped with `global_search_vector_not_ready` when global inventory isn't ready), and picks the next action from that evidence.
**Invariant:** `hot` requires ALL THREE families (large table AND sustained workload AND total cost) — a single spike, however slow, must not mint an index. The score's components are individually capped so no single dimension dominates ranking. Privacy is pinned by test: reports expose neither raw search values nor metric labels.
**Probe:** `packages/v2/table-query-ops/src/searchScopeHeat.spec.ts` (:44 'aggregates selected-field scopes and ranks sustained workload ahead of isolated spikes', :105 'does not expose raw search values or metric labels in the report'); advisor path covered by searchVector integration specs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "SearchScopeHeatPolicy evaluate heatScore buildScopedExpressionRecommendations", limit: 10 });
```

## Verdict
Adopt the stable-hash scope bucketing, three-factor hot gate, capped-log heat scoring, top-N selection, and coverage-gated recommendation emission; adapt thresholds (they encode teable's SLOs) and observation-window shape to host telemetry; omit pg_bigm/trgm provider specifics if host uses another operator class.
