<!-- capsule-v2 -->
# Batch update SQL composition seam — how do the transposed columns and system columns become the single UPDATE...FROM(VALUES) statement, and where does the repository take over?

**Source:** teable AGPL-3.0 `develop@06a4461e2bc5`; Codebase Memory `teable`. **Question:** How exactly does `buildBatchUpdateSql` get invoked by the repository (who supplies `returnedOldFields`), and what does the builder guarantee about record coverage, presence flags, and version bumping?

## Builder-side contract (composition view)
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/update/BatchUpdateSqlBuilder.ts:buildBatchUpdateSql` (:110–370); `collectBatchUpdateReturnedOldFields` (:41–80).
**Signature:** `buildBatchUpdateSql({tableName, columnUpdateData, systemColumns, table, db, returnedOldFields?}): Result<CompiledQuery, DomainError>`.
**Data Shape:** errors on empty columns (`validation.batch_update.empty_columns`) / zero records (`validation.batch_update.empty_records`). Record universe = union across ALL columns (:127–135) — sparse updates never lose rows. Constant-NULL detection requires EVERY record to EXPLICITLY carry a nullish value; missing ⇒ not constant-null (:169–192).

### Decisive source
```ts
// Case 2&3: varying columns ride VALUES rows with a presence flag per column:
//   v.__has_<i> AND SET col = CASE WHEN v.__has_i THEN v.col ELSE t.col END
// Case 1 (all-constant-NULL): no VALUES rows at all — plain WHERE __id = ANY(...)
// Both cases share the CTE skeleton:
WITH matched AS (SELECT __id AS matched_id, __version AS old_version <,old field cols>
                 FROM tbl WHERE __id = ANY(ARRAY[<escaped ids>]))
UPDATE tbl AS t SET ... FROM matched <, (VALUES ...) AS v(...)>
WHERE t.__id = v.__id AND t.__id = matched.matched_id <AND noop-guard OR-ladder>
RETURNING t.__id AS record_id, t.__version AS new_version, matched.old_version <, old_*>;
```
Value literal ladder per varying cell (:288–305): compilable kysely expression → rebase its `$n` placeholders onto the outer parameter array (`rebaseSqlPlaceholders`, :443–449); else `FieldSqlLiteralVisitor` type-aware literal; else `__row_*` numeric double-precision literal; else escaped text. Identifiers always `"double-quote-escaped"`; schema-qualified names split-and-quoted (:485–506). Tracked lastModified fields are excluded from both old-value collection and the no-op WHERE ladder (:384–421).
**Flow:** validate → union record ids → split constant-NULL vs varying → build old-value select list → emit case-1 (no VALUES) or case-2/3 (VALUES + presence CASE) with shared CTE.
**Invariant:** `__version = t.__version + 1` is emitted ONLY in SET (never in payload); explicit-null clears vs omitted keeps is decided by the presence flag, NOT nullness — conflating them silently wipes cells. The no-op guard (`IS DISTINCT FROM` OR-ladder) makes matched-but-identical updates skip row rewrites while still RETURNING nothing for them.
**Probe:** `update/BatchUpdateSqlBuilder.spec.ts` :357 (empty-columns error), :381 (single-quote escaping), :418 'preserves omitted sparse values by emitting presence-aware assignments', :458 'rebases parameters for raw SQL expressions embedded in VALUES rows'.

## Repository-side handoff
**Path/Symbol:** `PostgresTableRecordRepository.ts:updateManyStream` batch loop (:2564–2680).
**Data Shape:** repository calls `collectBatchUpdateReturnedOldFields(table, columnUpdateData, beforeImagePlan.trackedFields)` passing EXPLICIT extraFields from the before-image capture plan, then `buildBatchUpdateSql({...returnedOldFields})`, executes raw, and reads RETURNING rows into `updatedRecords` (record_id/new_version/old_version/old_*). Heavy-batch logging at ≥100 records / ≥50k SQL bytes / any locks / any additional statements.

### Decisive source
```ts
const returnedOldFields = collectBatchUpdateReturnedOldFields(batchTable, columnUpdateData,
  beforeImageCapturePlan.value.trackedFields.map(({fieldId, dbFieldName}) =>
    ({fieldId: fieldId.toString(), dbFieldName})));
const updateSqlResult = buildBatchUpdateSql({ tableName, columnUpdateData, systemColumns,
  table: batchTable, db, returnedOldFields });
const queryResult = await db.executeQuery(updateSqlResult.value);
```
**Invariant:** When callers supply `returnedOldFields`, the default derivation is BYPASSED — the before-image plan is authoritative for which old columns must come back; porters who ignore this break undo snapshots for tracked fields.
**Probe:** `PostgresTableRecordRepository.update.spec.ts` :1677 flow asserts restore-mode query shapes end-to-end; `updateMany.pglite.spec.ts` :406–615 pins runtime RETURNING behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildBatchUpdateSql collectBatchUpdateReturnedOldFields rebaseSqlPlaceholders", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-case emission strategy (constant-NULL-only shortcut, presence-flag VALUES path, CTE old-image join) plus placeholder rebasing and the caller-authoritative returned-old-fields rule. This capsule COMPOSES WITH `sparse-batch-update-engine`/`cte-before-image-bulk-update` (pass 10 mined the SQL semantics; THIS capsule pins the builder/repository API boundary and invocation choreography they sit behind). Adapt escaping helpers to your driver; omit teable-specific logging thresholds. Coverage caveat: direct spec file exists and was read line-exactly; suites not executed here (deterministic evidence only).
