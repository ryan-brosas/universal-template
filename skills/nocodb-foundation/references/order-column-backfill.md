<!-- capsule-v2 -->
# Order column backfill — how do you seed a fresh ordering column with dense values across three SQL dialects?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What is the per-dialect recipe for populating a new order/position column, and when can you skip ROW_NUMBER entirely?

## Dialect SQL table + auto-increment fast path
**Path/Symbol:** `packages/nocodb/src/modules/jobs/migration-jobs/nc_job_005_order_column.ts` — sql template map (:28-32), ai fast path (:221-243), dialect params (:246-269), index creation (:233-239/:273-279); partitioned variant `nc_job_014_link_order_column.ts:partitionedOrderSql` (:44-50) with per-dialect param arrays (:396-438).
**Signature:** `populateOrderValues(dbDriver, tnPath, model, source, newColumn)` — pushes ONE of: `UPDATE ?? SET ?? = ??` (ai copy), or the mysql2/pg/sqlite3 ROW_NUMBER statement; then always a `<table>_order_idx` CREATE INDEX.
**Data Shape:** placeholders are positional per dialect (mysql UPDATE…JOIN vs pg UPDATE…FROM vs sqlite WITH…UPDATE correlated subquery) — the arrays are NOT interchangeable.

### Decisive source
```ts
const sql = {
  mysql2:  `UPDATE ?? SET ?? = ROW_NUMBER() OVER (ORDER BY ?? ASC)`,
  pg:      `UPDATE ?? t SET ?? = s.rn FROM (SELECT ??, ROW_NUMBER() OVER (ORDER BY ?? ASC) rn FROM ??) s WHERE t.?? = s.??`,
  sqlite3: `WITH rn AS (SELECT ??, ROW_NUMBER() OVER (ORDER BY ?? ASC) rn FROM ??)
            UPDATE ?? SET ?? = (SELECT rn FROM rn WHERE rn.?? = ??.??)`,
};
// fast path: an auto-increment column IS already a dense unique ordering
if (aiColumn) {
  source.upgraderQueries.push(dbDriver.raw(`UPDATE ?? SET ?? = ??`, [tnPath, newColumn.column_name, aiColumn.column_name]).toQuery());
  // + CREATE INDEX <table>_order_idx ON …
  return;
}
```

**Flow:** add the system Order column via tableUpdate + Column.insert → if any `c.ai` column exists, copy it straight into the order column (dense by construction, no window function needed) → else run the dialect-specific ROW_NUMBER statement keyed off the first PK → index the new column in the same flush. The v2-junction twin (`_014`, currently UNREGISTERED — its header documents the exact 3-step registration recipe) repeats this with PARTITION BY over each junction FK and wires the two new column ids back onto every COL_RELATIONS row (`fk_mm_child_order_column_id` groups by child col, parent symmetric), invalidating each relation's cache key after the metaUpdate.
**Invariant:** the three dialect statements have different placeholder counts and orders — a porter who shares one param array across dialects produces silent wrong-SQL. The ai fast path must come FIRST (cheaper and correct); falling through to ROW_NUMBER for ai tables still works but wastes a full scan on huge tables. `_014`'s wiring invariant: child-order id pairs with child FK group, not insertion order.
**Probe:** no unit test upstream. Source-grounded probe: template map :28-32 matches params object :246-267 element-for-element; `_014` header :20-37 states "Mirrors nc_job_005 exactly" plus the not-yet-registered warning.
**Coverage caveat:** no in-repo tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "populateOrderValues partitionedOrderSql ROW_NUMBER nc_order", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dialect-template-map + ai-copy fast path for position backfills; adapt column names; omit the partitioned junction variant unless you give links stable per-side ordering.
