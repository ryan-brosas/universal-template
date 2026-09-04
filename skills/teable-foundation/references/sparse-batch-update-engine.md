<!-- capsule-v2 -->
# Sparse batch UPDATE engine — how do you update N records × M columns in ONE statement when each record touches a different sparse subset, without clobbering untouched cells?

## UPDATE … FROM (VALUES …) with per-column presence flags + CASE-keep SET clauses; constant-NULL fast path; no-op WHERE ladder
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/update/BatchUpdateSqlBuilder.ts` — `buildBatchUpdateSql(params)` (:110–370), `collectBatchUpdateReturnedOldFields` (:41–80), constant-null split (:169–192), presence-flag VALUES rows (:256–313), CASE SET clauses (:319–325), distinct-where ladders `buildConstantNullDistinctWhereClause` (:392–402) / `buildValuesDistinctWhereClause` (:404–421), placeholder rebasing (:443–449). Tests: `BatchUpdateSqlBuilder.spec.ts` 'preserves omitted sparse values by emitting presence-aware assignments' (:418), 'rebases parameters for raw SQL expressions embedded in VALUES rows' (:458), 'escapes single quotes in values' (:381).
**Signature:** input `columnUpdateData: Map<columnName, Array<{recordId, value}>>` (SPARSE: absent entry = don't touch) + `systemColumns {lastModifiedTime, lastModifiedBy, versionIncrement}`; output raw CompiledQuery.

### Decisive source
```sql
WITH matched AS (SELECT __id AS matched_id, __version AS old_version /*+ old_<f> */ FROM t WHERE __id = ANY(ARRAY[...]))
UPDATE t SET
  colA = CASE WHEN v.__has_0 THEN v."colA" ELSE t."colA" END,   -- presence flag keeps omitted cells
  __version = t.__version + 1,
  __last_modified_time = v.__last_modified_time
FROM matched, (VALUES ('rec1', TRUE, 'x', ts, user), ('rec2', FALSE, NULL, ts, user)) AS v(__id, __has_0, "colA", ...)
WHERE t.__id = v.__id AND t.__id = matched.matched_id
  AND ((v.__has_0 AND t."colA" IS DISTINCT FROM v."colA"))      -- no-op guard per row/column
RETURNING t.__id AS record_id, t.__version AS new_version, matched.old_version, matched.old_0 ...
```

**Flow:** union all record ids across every column map → split columns into constant-NULL (EVERY present value nullish — missing counts as NOT null-ish, :180–186) vs varying → varying columns get a companion boolean presence column; each row emits `TRUE/FALSE` + the value → SET uses `CASE WHEN v.has THEN v.col ELSE t.col END` so omitted values preserve stored cells while explicit null still clears → the WHERE appends an OR-ladder of `IS DISTINCT FROM` predicates (skipping lastModified fields) so rows whose requested values already match are not rewritten → RETURNING pairs post-images with CTE before-images.
**Invariant:** THE trap this design exists for: in a VALUES join, a missing cell is indistinguishable from NULL — without presence flags, batch-updating record A's title would silently NULL record B's description. Constant-NULL columns bypass VALUES entirely (`SET col = NULL`, :207–210) because a whole-column clear needs no per-row data. Embedded kysely expressions (sql.ref sub-values) are compiled and their `$n` placeholders REBASED into the shared parameter array (:432–449) — naive splicing corrupts parameter order. Values ride FieldSqlLiteralVisitor type-aware literals with escaped-string fallback; identifiers double-quote-escaped.
**Probe:** BatchUpdateSqlBuilder.spec.ts :418/:458/:381 pin presence semantics, rebase math, escaping.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildBatchUpdateSql collectBatchUpdateReturnedOldFields presenceAlias", limit: 5 });
```
## Verdict
Adopt verbatim for multi-record sparse writes to wide row stores: presence-flagged VALUES joins + CASE-keep SETs + distinct-FROM no-op guards; adapt literal/escaping layers to your dialect.
