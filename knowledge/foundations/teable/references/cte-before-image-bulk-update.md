<!-- capsule-v2 -->
# CTE before-image bulk update — how do you return BOTH old and new values (plus old/new versions) from a single bulk UPDATE statement?

**Source:** teable AGPL `develop@06a4461e`. **Question:** Postgres RETURNING sees only post-UPDATE rows — what SQL shape captures before-images for computed propagation without a pre-SELECT?

## WITH matched AS (SELECT old) UPDATE … FROM matched RETURNING old+new
**Path/Symbol:** `PostgresTableRecordRepository.ts` `updateMany` (:2332–2393) — `matchedSelects` (:2333), `returningSelects` (:2341), the `.with('matched', …).updateTable(tableName).from('matched')` chain (:2350–2361), version normalization :2379–2384. Tests: `PostgresTableRecordRepository.updateMany.pglite.spec.ts` 'updates matching rows with a single update-set-where statement' (:318), 'updates explicit recordIds without touching other rows' (:428).
**Signature:** input: where-expression + setClauses + trackedFields (`{fieldId, dbFieldName, oldValueAlias}`); output rows carry `record_id, new_version, old_version, old_<fieldId>…`.

### Decisive source
```ts
const matchedSelects = [
  sql.ref('__id').as('matched_id'), sql.ref('__version').as('old_version'),
  ...trackedFields.map(({dbFieldName, oldValueAlias}) => sql.ref(dbFieldName).as(oldValueAlias)),
];
const returningSelects = [
  sql.ref('__id').as('record_id'), sql.ref('__version').as('new_version'),
  sql.ref('matched.old_version').as('old_version'),
  ...trackedFields.map(({oldValueAlias}) => sql.ref(`matched.${oldValueAlias}`).as(oldValueAlias)),
];
db.with('matched', qb => qb.selectFrom(tableName).select(matchedSelects).where(whereExpression))
  .updateTable(tableName)
  .from('matched')                                   // join the frozen pre-image
  .set(setClauses)
  .whereRef('__id', '=', 'matched.matched_id')
  .returning(returningSelects).execute();
```

**Flow:** CTE snapshots the exact rows the filter matches (ids + versions + tracked field values) BEFORE any mutation → the UPDATE joins that snapshot row-by-row so each target row's pre-image is available in the same statement → RETURNING emits post-images alongside the CTE's pre-image columns.
**Invariant:** The CTE and the UPDATE run in ONE statement — under READ COMMITTED the CTE sees the same snapshot as the DML, so there is no TOCTOU gap between "select victims" and "update them" (a two-statement port needs FOR UPDATE plus re-check). Version fallback math (:2379–2384): non-finite newVersion→0, non-finite oldVersion→new−1 clamped ≥0 — defensive against null `__version` on exotic tables. Tracked fields are caller-chosen (before-image plan capsule), so the CTE selects ONLY needed columns.
**Probe:** updateMany.pglite.spec.ts :318/:428 pin single-statement semantics and untouched non-matching rows.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "updateMany matched returning old_version trackedFields", limit: 5 });
```
## Verdict
Adopt the CTE-before-image UPDATE shape verbatim whenever bulk writes must feed old+new values to downstream recomputation in one round-trip.
