<!-- capsule-v2 -->
# Physical row duplication plan — how does server-side table copy work as INSERT…SELECT…RETURNING with junction twins, and which columns survive?

## filter plan.columns against REAL target catalog → INSERT INTO target SELECT expr ORDER BY __auto_number RETURNING __id → conditional __order-preserving junction copies
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `duplicatePhysicalRows(context, plan)` (:1762–1862): active-column filter (:1785–1793, regex `/^\"((?:[^\"]|\"\")*)\"$/` unescape :1787–1791), core statement (:1806–1812), junction `copyOrder` gate (:1825–1834), two junction insert shapes (:1836–1856). Companion capsules: `field-duplicate-sql` (meta-plane twin), `view-order-bootstrap`.
**Signature:** `plan: PhysicalTableDuplicatePlan {sourceTableName, targetTableName, columns: [{targetColumn, sourceSql}], ensureTargetOrderColumns, junctionCopies[]}`.

### Decisive source
```ts
const activeColumns = plan.columns.filter(column => {
  const sourceColumnMatch = column.sourceSql.match(/^\"((?:[^\"]|\"\")*)\"$/);   // bare quoted col?
  if (!sourceColumnMatch) return true;          // constants like `1` always pass
  const sourceColumn = sourceColumnMatch[1]!.replace(/\"\"/g, '\"');
  return sourceColumnSet.has(sourceColumn);     // else drop if missing from SOURCE catalog
});
const result = await sql`
  INSERT INTO ${targetRef} (${sql.raw(targetCols)})
  SELECT ${sql.raw(sourceExprs)} FROM ${sourceRef}
  ORDER BY ${sql.id('__auto_number')}
  RETURNING ${sql.id('__id')}`.execute(db);
```

**Flow:** ensure target view-order columns exist → list SOURCE physical columns → keep only plan columns that reference existing sources (or non-column constants) → run one INSERT…SELECT ordered by `__auto_number` (preserving creation order so autoNumber continuity reads naturally) capturing new ids via RETURNING → for each junction twin, copy self↔foreign pairs, including `__order` ONLY when BOTH junction tables physically have it.
**Invariant:** THREE porting traps: (1) The catalog cross-check runs against the SOURCE table's actual columns, not the meta plan — duplicated plans from drifted metas degrade gracefully instead of failing the whole copy mid-DDL. (2) `ORDER BY __auto_number` inside INSERT…SELECT is what keeps restored/duplicated tables' autoNumber ordering stable; dropping it scrambles default sort. (3) Junction `__order` copying is CONDITIONAL on both hosts having the column because link reads may ignore null-order rows for multi-value relationships (:1823–1824 comment) — copying nothing beats copying NULLs that hide links.
**Probe:** deterministic grep :1787–1791/:1810/:1833–1834.
**Coverage caveat:** exercised via table-duplicate flows; no dedicated unit spec isolates duplicatePhysicalRows — noted.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "duplicatePhysicalRows junctionCopies PhysicalTableDuplicatePlan", limit: 5 });
```
## Verdict
Adopt for physical copies of dynamic-schema tables: catalog-filtered column plans, order-preserving INSERT…SELECT…RETURNING, capability-probed junction twins.
