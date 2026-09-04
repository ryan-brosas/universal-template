<!-- capsule-v2 -->
# On-demand SQL formula expansion — how do you evaluate formula columns via SQL JOINs when formulas may be unparseable, reference missing tables, or hit unsupported constructs?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you lift simple cross-table formulas into SQL without letting a bad formula break the whole query?

## Error-carrying query expansion: select 0 in SQL, substitute error objects in JS after the step
**Path/Symbol:** `app/server/lib/ExpandedQuery.ts:expandQuery` (:43–133); error carrier `ExpandedQuery.constants` (:23–25); post-hoc detail wrapper `getFormulaErrorForExpandQuery` (:135–151).
**Signature:** `function expandQuery(iquery: ServerQuery, docData: DocData, onDemandFormulas: boolean = true): ExpandedQuery`.
**Data Shape:** `ExpandedQuery extends ServerQuery { constants?: {[colId]: [GristObjCode.Exception, string] | [GristObjCode.Pending]}, joins?: string[], selects?: string[] }` — `constants` is NOT SQL; it is a side-channel of JS-substituted values keyed by output column.

### Decisive source
```ts
if (error) {
  // We add a trivial selection, and store errors in the query for substitution later.
  sqlFormula = "0";
  if (!query.constants) { query.constants = {}; }
  query.constants[colId] = [GristObjCode.Exception, error];
}
if (sqlFormula) {
  selects.add(`${sqlFormula} as ${quoteIdent(colId)}`);
}
// ... foreignColumn branch:
const alias = `${query.tableId}_${formula.refColId}`;
joins.add(`LEFT JOIN ${quoteIdent(altTableId)} AS ${quoteIdent(alias)} ` +
  `ON ${quoteIdent(alias)}.id = ${quoteIdent(query.tableId)}.${quoteIdent(formula.refColId)}`);
sqlFormula = `${quoteIdent(alias)}.${quoteIdent(formula.colId)}`;
```

**Flow:** look up `_grist_Tables`/`_grist_Tables_column` meta rows for the queried table → build a `colId → refTableId` map from non-formula columns whose type strips `Ref:` → SELECT the table's id + every data column → for each formula column parse the formula and branch on kind: `foreignColumn` adds one LEFT JOIN per referenced column aliased `<tableId>_<refColId>` (deduped by Set), `column` selects a local data column, `literalNumber` inlines the value, `error`/missing-table/missing-column route to the constants side-channel (`SELECT 0`, remember the message), anything else throws.
**Invariant:** A broken formula must NEVER fail the query — it degrades to a constant `0` selected under the real column alias plus an `[Exception, msg]` entry in `query.constants`; the caller substitutes real error objects after the SQL step because "it is awkward to write a sql selection that constructs an error object". Joins are always LEFT (missing refs yield NULL, not dropped rows) and alias-qualified so self-references to same-named columns can't collide. Only two formula kinds are lifted (`foreignColumn` where the target is itself non-formula, plain `column`); everything else is out of scope by design.
**Probe:** `test/server/lib/DocStorageQuery.ts` exercises the consumer path end-to-end: `"should construct correct query from normally expected fields"` (:49) asserts exact marshalled SQL `SELECT * FROM "foo" LIMIT 4` / filter-IN shape produced from an ExpandedQuery via stubbed `allMarshal`; `getFormulaErrorForExpandQuery` (:135) rebuilds the full expansion just to fetch one column's stored error text ("Not supported in on-demand tables.").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "expandQuery ExpandedQuery onDemandFormulas", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the constants side-channel pattern whenever generated SQL must tolerate per-column failure (bad expressions degrade to sentinel values, errors reattached in host language after the query). Adapt the supported-formula grammar to your expression language; keep join-per-reference aliasing if you port multi-hop lookup. Omit the GristObjCode envelope if your cells carry errors natively.
