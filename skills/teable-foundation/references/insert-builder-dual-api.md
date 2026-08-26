<!-- capsule-v2 -->
# RecordInsertBuilder — how do you compile a record INSERT (plus its link/attachment side-effects) into the exact SQL the repository would run, without executing it?

**Source:** teable AGPL-3.0 `develop@06a4461e2bc5`; Codebase Memory `teable`. **Question:** What is the full column/SQL construction contract for inserting one record — system columns, computed-field ladder, link-relationship SQL matrix, and the lock/exclusivity metadata returned alongside?

## Compiled-vs-data dual API
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/insert/RecordInsertBuilder.ts:buildInsertData` (:192–436) and `:build` (:442–471).
**Signature:** `buildInsertData({table, fieldValues: ReadonlyMap<string, unknown>, context: RecordInsertBuilderContext}): Result<RecordInsertDataResult, DomainError>`; `build(...)` wraps `buildInsertData` and compiles the main INSERT via kysely (`mainInsert` + `additionalStatements` + `linkedRecordLocks`). `static executeStatements(db, statements)` runs additional statements sequentially.
**Data Shape:** `RecordInsertDataResult = { values: Record<string, unknown>; additionalStatements: CompiledSqlStatement[]; linkedRecordLocks; exclusivityConstraints; extraSeedRecords; userFieldColumns }`. `CompiledSqlStatement = { description, compiled }`. Context defaults: `createdTime ?? now`, `createdBy ?? actorId`, `lastModifiedTime === undefined ? createdTime : context.lastModifiedTime` (**explicit null survives; undefined defaults**) — same ternary for lastModifiedBy. `version ?? 1`, `__auto_number` only spread in when `typeof context.autoNumber === 'number'`.

### Decisive source
```ts
const lastModifiedTime =
  context.lastModifiedTime === undefined ? createdTime : context.lastModifiedTime;
...
const values: Record<string, unknown> = {
  [RECORD_ID_COLUMN]: context.recordId,
  [CREATED_TIME_COLUMN]: createdTime,
  [CREATED_BY_COLUMN]: createdBy,
  [LAST_MODIFIED_TIME_COLUMN]: lastModifiedTime,
  [LAST_MODIFIED_BY_COLUMN]: lastModifiedBy,
  [VERSION_COLUMN]: context.version ?? 1,
  ...(typeof context.autoNumber === 'number' ? { __auto_number: context.autoNumber } : {}),
};
```

**Flow:** seed system columns → iterate ALL table fields → per field branch: computed-system / plain-computed skip / user-audit snapshot / visitor values → collect link SQLs, locks, exclusivity, extra seeds → optional missing-title fill expression overwrites `values[dbFieldName]` → attachment insert query appended → return raw values (+ compiled form in `build`).
**Invariant:** The builder NEVER executes; repositories execute inside their transaction. Every field iteration must terminate in exactly one of: value written to `values`, statement appended, or silent `continue` — a porter who drops a branch silently loses data.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/insert/RecordInsertBuilder.spec.ts` (recording Kysely driver captures compiled SQL without a DB).

## Computed/system-field write ladder
**Path/Symbol:** `RecordInsertBuilder.ts:buildInsertData` field loop (:231–326).
**Signature:** per-field decision ladder keyed on `FieldType` + `field.computed()`.
**Data Shape:** non-system computed fields are ALWAYS skipped (computed columns fill from DB); system-computed fields (createdTime/lastModifiedTime/createdBy/lastModifiedBy/autoNumber) ARE written explicitly.

### Decisive source
```ts
if (field.computed().toBoolean()) {
  if (!isSystemComputedField) continue;          // formula/rollup/lookup: DB fills these
}
// CreatedBy/LastModifiedBy store user snapshot JSON built FROM CONTEXT:
values[dbFieldName] = userId == null ? null : buildUserFieldJsonValue({
  userId, userName: ..., userEmail: ... });      // {id,title,email,avatarUrl} JSON string
// time fields: JSON-typed cols get JSON.stringify(resolvedValue), else raw
```
User snapshot shape (from `buildUserFieldJsonValue` :701–716): `{ id, title: name??userId, email: email??null, avatarUrl: '/api/attachments/read/public/avatar/<id>' }`.
**Flow:** computed? → system-computed only → generated-column probe skips (see `generated-column-insert-strip`) → user fields become pre-built snapshot strings (NO per-row subquery) → time/autoNumber get fallback-or-context values with JSON-type stringify.
**Invariant:** Porters routinely generate per-row `jsonb_build_object(... SELECT from users)` subqueries for CreatedBy/LastModifiedBy — upstream deliberately builds snapshots once from execution context instead (batch INSERT cost). The deprecated static `buildUserFieldUpdateStatement` (:668–698) still emits that old subquery form — never adopt it for new code.
**Probe:** `insert/RecordInsertBuilder.userFields.spec.ts` :107–154 asserts exact snapshot JSON incl. avatarUrl; :156–191 asserts NO `jsonb_build_object`/`public.users` appears in compiled SQL; :223–280 asserts generated-meta omission.

## Link-relationship SQL matrix
**Path/Symbol:** `RecordInsertBuilder.ts:buildLinkFieldSqls` (:489–665).
**Signature:** `private buildLinkFieldSqls(field: LinkField, rawValue: unknown, recordId): Result<LinkFieldSqlsResult, DomainError>` where `LinkFieldSqlsResult = { statements, linkedRecordLocks, exclusivityConstraint?, extraSeedRecords }`.
**Data Shape:** storage location by relationship: `manyMany || (oneMany && isOneWay)` → junction table rows; oneMany two-way → single set-based UPDATE on foreign table; manyOne/oneOne → FK column already in main `values` (no extra SQL).

### Decisive source
```ts
const usesJunctionTable =
  relationship === 'manyMany' || (relationship === 'oneMany' && field.isOneWay());
// junction path: PER ITEM delete-then-insert pair, order = i+1 when hasOrderColumn()
// oneMany two-way path: ONE bulk UPDATE ... FROM (VALUES ...) AS v:
const updateSql = sql`update ${sql.table(foreignTableName)} as t set ${sql.ref(selfKeyName)} =
  ${sql.ref('v.record_id')} ... from (values ${valuesSql}) as v(id, record_id)
  where ${sql.ref('t.__id')} = ${sql.ref('v.id')}`;
// every junction item pushes linkedRecordLocks FIRST (deadlock prevention)
```
Junction order column is written as literal `order = i+1` following array position; empty `linkItems.length===0` returns early with nothing. `fkHostTableName().split({defaultSchema:'public'})` yields `schema.table` qualified names everywhere.
**Flow:** parse items → validate ids into `RecordId` VOs → collect extraSeedRecords for ALL types (symmetric-field recompute needs them even when no SQL emitted) → exclusivity constraint if `requiresExclusiveForeignRecord()` → emit per-relationship SQL.
**Invariant:** oneMany-two-way backfill MUST be a single set-based UPDATE...FROM VALUES (per-row updates deadlock under concurrency); locks are collected for junction AND oneMany paths but NOT for manyOne/oneOne (FK lives in own row — no foreign row touched). Extra-seed collection happens regardless of relationship because concurrent inserts linking the same foreign record must trigger its symmetric computed update deterministically.
**Probe:** `RecordInsertBuilder.spec.ts` :192–209 (no `__order` when hasOrderColumn=false), :211–241 (oneMany order column present; parameters `[rec_one, rec_main, 1, rec_two, rec_main, 2]`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "RecordInsertBuilder buildInsertData buildLinkFieldSqls", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual compiled/raw API, the computed-ladder (skip non-system computed; context-snapshot user fields; explicit-null-wins defaults), and the relationship×storage SQL matrix with lock/exclusivity/extraSeed metadata returned beside the SQL. Adapt kysely compilation and the `Table` domain entity accessors to host equivalents. Omit the deprecated `buildUserFieldUpdateStatement` subquery form and teable's schema-qualified table-name plumbing specifics. Coverage caveat: builder logic itself is pinned by recording-driver specs; the SQL's runtime behavior against real Postgres is covered by repository-level pglite suites, not by these unit specs.
