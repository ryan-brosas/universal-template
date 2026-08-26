<!-- capsule-v2 -->
# maxGroupPoints cap — LIMIT-on-grouped-aggregate as honest truncation

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What happens to grouped statistics when a view has more distinct groups than one page can hold?

## Env-tunable cap applied ONLY when groupBy present
**Path/Symbol:** `apps/nestjs-backend/src/features/aggregation/aggregation.service.ts:handleAggregation` (:339–341); threshold `configs/threshold.config.ts:maxGroupPoints` (:14, `MAX_GROUP_POINTS ?? 5_000`); grid twin cap `record.service.ts:3006`; tail synthesis `groupDbCollection2GroupPoints` :2762–2773.
**Signature:** `if (groupBy?.length) qb.limit(this.thresholdConfig.maxGroupPoints);`
**Data Shape:** LIMIT on the grouped SELECT = first N groups in choice/sort order; remainder collapses into an `'unknown'` bucket.

### Decisive source
```ts
if (groupBy?.length) {
  qb.limit(this.thresholdConfig.maxGroupPoints);
}
```
```ts
// record.service.ts — the consumer-side honesty marker
if (curRowCount < rowCount) {
  groupPoints.push(
    { id: 'unknown', type: GroupPointType.Header, depth: 0, value: 'Unknown', isCollapsed: false },
    { type: GroupPointType.Row, count: rowCount - curRowCount },
  );
}
```

**Flow:** The limit is applied AFTER grouping/ordering so the surviving groups are the FIRST N in declared order (choice-position or value sort), never arbitrary. The row-count side separately computes the TRUE filtered count (`getRowCountByFilter`) and compares against the sum of emitted group rows; any deficit becomes a synthetic Unknown header + remainder row.
**Invariant:** Counts stay EXACT while identity degrades — porters who instead raise the limit "until it fits" turn a bounded endpoint into an unbounded memory/latency surface (a link field with 500k distinct values). The unknown-bucket contract requires the separate total count; computing it from the same limited query would always show no deficit. The cap applies ONLY under groupBy (:339) because a footer aggregation's single-row result needs no LIMIT and adding one would be dead weight but also change nothing semantically — keeping it conditional documents intent.
**Probe:** `grep -cF 'maxGroupPoints' apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` → 1; `grep -cF "'unknown'" apps/nestjs-backend/src/features/record/record.service.ts` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "groupDbCollection2GroupPoints maxGroupPoints unknown", limit: 10 });
```

## Verdict
Adopt capped grouped aggregates with explicit remainder buckets; adapt cap size and ordering guarantees; never let the cap silently drop counts without a marker.
