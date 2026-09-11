<!-- capsule-v2 -->
# Physical row duplication (table clone) — how do you clone a table's rows server-side in one INSERT…SELECT?

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does table duplication copy physical rows and junction links without reading them into the app?

## INSERT…SELECT row clone
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresTableRecordRepository.ts:duplicatePhysicalRows` (:1762–1862).
**Signature:** `(context, plan: PhysicalTableDuplicatePlan) => Result<{rowCount, recordIds}, DomainError>`; plan carries `columns: {targetColumn, sourceSql}[]`, `ensureTargetOrderColumns`, `junctionCopies[]`.
**Data Shape:** source columns arrive as quoted SQL fragments; identity check parses `"((?:[^"]|"")*)"$` and unescapes `""`→`"`; result ids come from `RETURNING __id`.

### Decisive source
```ts
const activeColumns = plan.columns.filter((column) => {
  // Constants like `1` are not source column references.
  const sourceColumnMatch = column.sourceSql.match(/^"((?:[^"]|"")*)"$/);
  if (!sourceColumnMatch) return true;
  const sourceColumn = sourceColumnMatch[1]!.replace(/""/g, '"');
  return sourceColumnSet.has(sourceColumn);
});
const result = await sql`
  INSERT INTO ${targetRef} (${sql.raw(targetCols)})
  SELECT ${sql.raw(sourceExprs)} FROM ${sourceRef}
  ORDER BY ${sql.id('__auto_number')}
  RETURNING ${sql.id('__id')}
`.execute(db);
```
Junction twin copies `__order` ONLY when BOTH junction tables physically have it:
```ts
const copyOrder = sourceJunctionColumns.includes('__order')
  && targetJunctionColumns.includes('__order');
// link reads may ignore rows with null order for multi-value relationships
```

**Flow:** ensure target order columns → introspect source columns via information_schema → drop plan columns whose "sourceSql" names a column that no longer exists on the SOURCE (constants pass untouched) → single ordered INSERT…SELECT RETURNING __id → for each junction pair, INSERT…SELECT self/foreign (+__order when both sides have it).
**Invariant:** the ORDER BY `__auto_number` preserves creation-order so restored autoNumbers stay stable; never copy an order column into a junction lacking it. All identifiers go through quote-and-double-quote escaping before `sql.raw`.
**Probe:** no dedicated spec file at this pin (parse_partial flags :1806 template literal) — deterministic coverage caveat; behavior is pinned indirectly by duplicateTable e2e flows (`packages/v2/e2e/src/duplicateTable.e2e.spec.ts`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "duplicatePhysicalRows junctionCopies INSERT SELECT RETURNING __auto_number", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the server-side clone with existence-filtered column plan (a port that re-reads rows client-side will corrupt large tables and lose ordering). Adapt the junction-pair detection to your link storage. Omit teable's `__auto_number` semantics if your tables lack it (then pick another stable order key).
