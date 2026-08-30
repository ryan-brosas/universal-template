<!-- capsule-v2 -->
# Permission-aware projection funnel — how denied fields resolve to NULL instead of leaking

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How do aggregation queries include only permitted fields while filters on hidden fields keep working?

## resolveAggregationProjection ∩ enabledFieldIds
**Path/Symbol:** `apps/nestjs-backend/src/features/aggregation/aggregation.service.ts:resolveAggregationProjection` (:445–494) + probe :289–294; row-count twin search-projection :610–616; builder consumption `record-query-builder.service.ts` (projection → `getOrderedFieldsByProjection`, buildAggregateSelect :683–714; augmented filter map :716–751).
**Signature:** `resolveAggregationProjection({statisticFields, groupBy, filter, searchFields, allowedFieldIds}) → string[] | undefined`.
**Data Shape:** projection = field-id list limiting CTE/link joins; undefined = no restriction.

### Decisive source
```ts
const filtered = projectionArray.filter((fieldId) => allowedSet.has(fieldId));
return filtered.length > 0 ? filtered : Array.from(allowedSet);
```
```ts
// Limit link/lookup CTEs to enabled fields so denied fields resolve to NULL
projection,
```

**Flow:** Collect every field the request touches (statistic targets, groupBy, FILTER operands via extractFieldIdsFromFilter, search fields), intersect with permissionProbe.enabledFieldIds, and hand the result as the builder's projection so ONLY those fields' CTEs/joins get built — a denied field never enters SQL, so its aggregate reads NULL rather than erroring or leaking. The final line is the subtle one: if the intersection is EMPTY, fall back to ALL allowed ids rather than an empty projection.
**Invariant:** Two asymmetries porters invert: (1) FILTERS are not projected away — `buildFilter` augments the selectionMap with qualified refs for EVERY table field precisely "so that permission-hidden fields can still participate in WHERE clauses" (:724–725); hiding a field hides its VALUES, not its filtering power. (2) Empty-intersection ⇒ allowedSet fallback keeps the query ANSWERABLE (all-NULL aggregates) instead of throwing — degrade, don't fail. The '*' fieldId in statisticFields must be skipped when collecting (:457) since it's a wildcard, not a column.
**Probe:** `grep -cF 'extractFieldIdsFromFilter' apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` → 1; `grep -cF 'permission-hidden fields' apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "resolveAggregationProjection enabledFieldIds wrapView", limit: 10 });
```

## Verdict
Adopt collect→intersect→project funnels for any aggregate over permission-scoped columns; adapt the empty-set fallback to your product's fail-vs-degrade posture.
