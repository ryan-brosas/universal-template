<!-- capsule-v2 -->
# Sub-group counts — where can COUNT(DISTINCT ...) legally live, and why does the inner SQL need re-sanitizing after composition?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How is "how many child groups per parent group" computed without tripping ORA-00937, missing-column references, or knex binding-count errors?

## Three placements for the distinct-count aggregate
**Path/Symbol:** `packages/nocodb/src/db/BaseModelSqlv2/group-by.ts:list` :397-448 (inner projection), outer aggregate at :542-547.
**Signature:** `subGroupColumnName?` arg → either an extra projected column `__nc_sub_group_col__` or an inline `__sub_group_count__` aggregate.
**Data Shape:** leaf-level sanitized SQL STRING (`processColumn(...).toQuery()` → `sanitizeQuery`) re-embedded into raw expressions.

### Decisive source
```ts
// :400-402 — sanitize AT THE LEAF first: formula string literals contain
// literal '?' characters that would corrupt the outer .toSQL() chain:
const subGroupQuery = baseModel.sanitizeQuery(await processColumn(subGroupColumnName, true));

// mssql (:403-412): project the expression as a REAL NVARCHAR(MAX) column on
// the inner derived table; the OUTER aggregation computes COUNT(DISTINCT...):
qb.select(raw(`CAST(?? AS NVARCHAR(MAX)) as ??`, [raw(subGroupQuery), '__nc_sub_group_col__']));

// oracle (:413-427): ALSO column-projection, NOT pg-style inline aggregate —
// Oracle can't aggregate on this ungrouped inner query (ORA-00937), and the
// earlier bug took the pg branch → outer referenced a __nc_sub_group_col__
// that was never projected → sub-group count came back missing/NaN, so
// nested group expansion couldn't grow the canvas virtual height:
qb.select(raw(`TO_CHAR(??) as ??`, [raw(subGroupQuery), '__nc_sub_group_col__']));

// everyone else (:428-447): inline COUNT(DISTINCT COALESCE(blank→NULL(key),'__null__'))
const innerExpr = baseModel.sanitizeQuery(
  `COUNT(DISTINCT COALESCE(${sqlNullIfBlank({
    columnName: raw(baseModel.isPg ? '(??)::text' : '??', [raw(subGroupQuery)]),
    baseModel, isStringType: true}), '__null__'))`);
// :429-433 WHY re-sanitize: composing via template literal toString()s the Raw
// → toQuery(), whose formatQuery UNESCAPES '\?' back to bare '?'; feeding that
// straight into outer raw(...) counts those as placeholders → Knex throws
// "Expected 1 bindings, saw N".
```
Outer side (mssql/oracle): `, COUNT(DISTINCT COALESCE(__nc_sub_group_col__, '__null__')) as __sub_group_count__` appended inside the single outer `raw` select (:551-556).

**Flow:** leaf sanitize → dialect picks projection vs inline aggregate → composed string RE-sanitized → bound as raw select → outer derived-table path appends its own DISTINCT count over the projected column.
**Invariant:** (1) Any aggregate over the sub-group expression may only live where the dialect allows aggregates (outer for mssql/oracle). (2) Every string-composition hop through `.toQuery()` re-introduces unescaped `?`; sanitize again at each hop. (3) COALESCE sentinel `'__null__'` keeps NULL children counted as ONE distinct group rather than vanishing from COUNT(DISTINCT).
**Probe:** No unit tests upstream. Deterministic probe: pg SQL with subGroupColumnName contains BOTH `__nc_sub_group_col__`-free inline `COUNT(DISTINCT COALESCE(` AND `as "__sub_group_count__"`; oracle SQL contains `TO_CHAR(` projection instead.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "sub_group_count", limit: 5 });
// nocodb.packages.nocodb.src.db.BaseModelSqlv2.group-by.list Function group-by.ts 109-724 (:397-448)
```

## Verdict
Adopt the three-placement rule and the re-sanitize-at-every-composition-hop invariant. Adapt sanitizer to your escaping scheme. Caveat: no direct tests at pin; graph ranges verified live.
