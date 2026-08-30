<!-- capsule-v2 -->
# Repository observation decorator — how do you instrument every record query with analytics without touching the repository implementation?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How is a query repository wrapped so find/findStream both emit observation windows while preserving Result semantics and stream teardown?

## Marker-guarded decorator + finally-block stream accounting
**Path/Symbol:** `packages/v2/table-query-ops/src/recordQueryObservation.ts`: `ObservedTableRecordQueryRepository` (:36-152), `decorateV2TableRecordQueryRepositoryWithTableOps` (:154-171), marker symbol (:34), `buildRecordQueryShape` (:173-253), buckets (:258-270).
**Signature:** decorator resolves current repo from `v2CoreTokens.tableRecordQueryRepository`, skips when unregistered OR already marked, re-registers the WRAPPER under the same token via `registerInstance`.
**Data Shape:** windows are fixed 300s (`windowStart = floorDate(now, 300_000)`, `windowSizeSeconds: 300`) with `requestCount:1`; slow threshold hard-coded 3000ms matching the risk policy default; result buckets none/≤100/≤1000/large; search length buckets none/≤8/≤64/long.

### Decisive source
```ts
async *findStream(context, table, spec, options) {
  const startedAt = Date.now();
  const sqlDiagnostics = attachTableQuerySqlDiagnosticsCollector(context, this.sqlDiagnosticsConfig);
  let count = 0; let failed = false;
  try {
    for await (const row of this.inner.findStream(context, table, spec, options)) {
      if (row.isErr()) failed = true; else count += 1;
      yield row;                                   // consumer sees rows unchanged
    }
  } finally {                                      // records even on consumer break / early return
    try {
      await this.recordObservation(context, table, spec, options,
        { durationMs: Date.now() - startedAt, timedOut: false,
          errorKind: failed ? 'unknown' : undefined,
          resultCountBucket: bucketResultCount(count) },
        sqlDiagnostics.collector.snapshot());
    } finally { sqlDiagnostics.restore(); }
  }
}
```

**Flow:** every find → attach SQL-diagnostics collector into context (saving prior for nesting) → delegate to inner → record observation in a shape built from options (search→resolved field ids + access-path-derived mode full_text/substring/ilike, spec→coarse conditionCount:1 placeholder with EMPTY fields list, system `__row_`/`__auto_number` order columns classified as tieBreakers) → restore collector. Shape/Observation construction failures SWALLOW silently (`if (shape.isErr()) return;`) — analytics must never fail the query.
**Invariant:** The decorator never alters results or error values; double-decoration impossible via symbol marker; findOne is deliberately NOT wrapped (pass-through). Streaming observations emit exactly once per stream INCLUDING aborted consumption — the finally placement is load-bearing.
**Probe:** `recordQueryObservation.spec.ts:45` "records the resolved selected field scope and active full-text access path".
**Coverage caveat:** single-spec coverage; the spec-placeholder whereShape (count 1, empty fields) is an honest coarseness — porters should not mistake it for real filter parsing (that lives in queryConfigShape).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ObservedTableRecordQueryRepository decorateV2TableRecordQueryRepositoryWithTableOps findStream", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt marker-guarded token replacement and finally-based stream instrumentation; adapt thresholds/buckets; omit the coarse spec placeholder only if you wire real spec parsing at the same layer.
