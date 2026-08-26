<!-- capsule-v2 -->
# Progressive group-point fan-out — N-level groups via prefix-slice re-aggregation

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How are multi-level (group-by A, then B) statistics assembled without one mega GROUP BY CUBE?

## Prefix-sliced handleAggregation loop + hashed composite ids
**Path/Symbol:** `apps/nestjs-backend/src/features/aggregation/aggregation.service.ts:performGroupedAggregation` (:354–440) — the loop at :391–403, id hashing :408–416, per-func group fill :418–435; hash helper `utils.string2Hash`; sibling row-emitter `record.service.ts:groupDbCollection2GroupPoints` (:2699–2779).
**Signature:** `performGroupedAggregation({aggregations, statisticFields, groupBy, ...}) → IRawAggregations`.
**Data Shape:** group value key = `${fieldId}_${convertValueToStringify(v1)}_${...}` hashed to numeric string; result `aggregations[].group = { [groupId]: {value, aggFunc} }`.

### Decisive source
```ts
for (let i = 0; i < groupBy.length; i++) {
  const rawGroupedAggregationData = await this.handleAggregation({
    ..., groupBy: groupBy.slice(0, i + 1), statisticFields, ...
  })!;
  ...
  const flagString = `${currentGroupFieldId}_${groupByValueString}`;
  const groupId = String(string2Hash(flagString));
```

**Flow:** Level i re-runs the FULL aggregation query grouped by the first i+1 fields → each row's group path is stringified (`convertValueToStringify`) and `_`-joined → hashed with fieldId prefix into a stable groupId → every statistic field's value lands in `group[groupId]`. The sibling grid path (`groupDbCollection2GroupPoints`) walks the SAME ordered rows once, tracking a `fieldValues` sentinel array (Symbol() = "no value yet at this depth") to emit Header points on depth changes, `break`-ing below a collapsed depth, and appending an `'unknown'` header + remainder row when `curRowCount < rowCount` (the maxGroupPoints LIMIT truncated tail rows).
**Invariant:** The groupId must be computed from the PREFIX PATH (all levels so far), not just the leaf value — two subtrees can share a leaf label ("Done" under Project A and B); hashing only the leaf collides their buckets. The unknown-tail synthesis is the honest-degradation contract for the maxGroupPoints cap (default 5,000, threshold.config.ts:14): counts stay exact, identity is what's lost. Sentinels must be Symbol() not undefined — a legit group value can BE undefined/null.
**Probe:** `grep -cF 'groupBy.slice(0, i + 1)' apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` → 1; `grep -cF 'MAX_SAFE_INTEGER' apps/nestjs-backend/src/features/record/record.service.ts` → 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "performGroupedAggregation groupDbCollection2GroupPoints string2Hash", limit: 10 });
```

## Verdict
Adopt prefix-slice aggregation for hierarchical grouping when your engine lacks multi-dimensional rollup; adapt hashing to your id scheme; keep the unknown-tail honesty marker.
