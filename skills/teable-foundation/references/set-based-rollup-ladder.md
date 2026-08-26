<!-- capsule-v2 -->
# Set-based rollup join-mode ladder — when a grouped host aggregate replaces a correlated LATERAL, and how hosts-without-links keep COUNT/SUM semantics

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does teable decide between correlated LATERAL, uncorrelated INNER, host-driven LEFT JOIN (`hostLeft`), and scalar-host-key LEFT JOIN (`hostKey`) for rollup/conditional-rollup computation — and why must zero-match hosts still emit a row?

## Four join modes chosen per lateral group
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/computed/ComputedTableRecordQueryBuilder.ts` — gate `isSetBasedLinkRollupGroup` (:1311–1358: requires dirty filter or `allowFullTableSetBasedRollups`, non-self table, every column an order-insensitive rollup with no condition/sort/limit; junction shapes OK, oneMany needs non-`__id` foreign host key); aggregate `buildSetBasedLinkRollupAggregate` (:1364–1435) with host-source doc :1360–1363 and empty-row comment "Drive the aggregate from the relevant host set so hosts without links still produce a grouped row and retain the existing COUNT/SUM/null empty semantics"; conditional ladder in `buildConditionalJoins` (:1485–1715): shared field-ref groups → `buildConditionalRollupFieldReferenceAggregate` (:1879–1986, ranking only when `!group.orderInsensitive || group.limit !== undefined`, default limit = `CONDITIONAL_QUERY_DEFAULT_LIMIT` from env-capped `CONDITIONAL_QUERY_MAX_LIMIT=5000` :76–77); source-only fast path `shouldUseConditionalRollupFastPath` (:1717–1738, `SIMPLE_CONDITIONAL_ROLLUP_OPERATORS = {'is','isAnyOf'}` :81).
**Signature:** join modes emitted per subquery: `'lateral' | 'inner' | 'hostLeft' | 'hostKey'`; `hostKey` additionally carries `hostKeyColumn` resolved by `resolveScalarConditionalHostKeyColumn` (:1450–1479, ONLY singleLineText↔singleLineText pairs).
**Data Shape:** `hostLeft`/`hostKey` subqueries expose `__host_id` / `__host_key` for the outer LEFT JOIN onto `t.__id` / `t.{column}`; `nullSafeTextKeyEquality` (:1481–1483) `(l IS NULL) = (r IS NULL) AND coalesce(l,'') = coalesce(r,'')`.

### Decisive source
```ts
if (this.isSetBasedLinkRollupGroup(table, foreignTable, linkField, lateral.columns)) {
  subqueries.push({ query: yield* this.buildSetBasedLinkRollupAggregate(...), joinMode: 'hostLeft' });
  continue;
}
// ... conditional path:
subqueries.push({ query, joinMode: useUncorrelatedRollupFastPath ? 'inner'
                 : /* else */ 'lateral', ... });
// hostKey when BOTH sides are singleLineText (stable under DISTINCT/GROUP BY):
joinMode: hostKeyColumn ? 'hostKey' : 'hostLeft',
```
```sql
-- hostLeft shape (set-based link rollup), grouped so empty hosts survive:
select h.__id as __host_id, <rollup aggregates>
from <dirty-gated host source> h
left join junction j on j.<selfKey> = h.__id
left join foreign f on f.__id = j.<foreignKey>
group by h.__id
```
**Flow:** ordinary reads keep per-host indexed laterals (their outer limit/order isn't visible to the builder) → bulk recompute/backfill switches eligible groups to one grouped scan: plain order-insensitive rollups → `hostLeft`; conditional rollups with a single field-reference equality (+ residual constants, optional limit/sort) → ranked or unranked host aggregate, joined by `__host_key` when both fields are text else `__host_id`; trivial source-only filters (`is`/`isAnyOf`, no sort/limit, all referenced fields on the foreign table) → uncorrelated `inner` fast path computed once instead of per row.
**Invariant:** the host drives FROM and aggregation is grouped BY the host identity so a host whose links all vanished still yields one row (COUNT→0, SUM→0, arrays→empty) — switching to inner-join semantics silently drops rows from recompute and leaves stale values; text-key joins must be NULL-safe-equal or NULL-keyed hosts cross-match. The dirty gate rides inside every host source (see capsule `dirty-set-join-placement`).
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/computed/ComputedTableRecordQueryBuilder.spec.ts` — `"keeps empty-host sum semantics in the set-based oneMany aggregate"` (:2008), `"keeps ordinary paginated rollup reads correlated"` (:2033), `"conditional rollups with residual field-ref filters use set-based host joins"` (:2680), `"conditional rollup uses window ranking for field-reference filter with limit"` (:2891), `"executes scalar field-reference rollup once per dirty host key"` (:3029).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "isSetBasedLinkRollupGroup buildSetBasedLinkRollupAggregate", limit: 5 });
// → both methods …/query-builder/computed/ComputedTableRecordQueryBuilder.ts 1311-1358 / 1364-1435
```

## Verdict
Adopt the four-way decision ladder keyed on (relationship shape, expression order-sensitivity, condition complexity, host/foreign field types) — it is the performance/correctness contract for scaling per-row aggregates to bulk recompute; adopt host-driven grouping + NULL-safe key equality verbatim. Adapt the eligibility gate to your own "am I inside a bounded recompute?" signal. Omit teable's snapshot-test harness specifics. Coverage caveat: none material — each mode has direct spec tests at this pin.
