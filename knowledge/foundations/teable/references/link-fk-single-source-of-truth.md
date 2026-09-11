<!-- capsule-v2 -->
# FK single-source-of-truth parse — why must old link keys be read from the FK storage, never from the cell JSON?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does the v1 engine derive old-vs-new link state per relationship without trusting denormalized cell values?

## getFkRecordMap / parseFkRecordItem
**Path/Symbol:** `apps/nestjs-backend/src/features/calculation/link.service.ts:getFkRecordMap` (:849–904) → `:parseFkRecordItem` (:728–848).
**Signature:** `getFkRecordMap(fieldMap, cellContexts): Promise<IFkRecordMap>`; `parseFkRecordItem(field, cellContexts, foreignKeys): Record<string, IFkRecordItem>` where `IFkRecordItem = { oldKey: string|string[]|null; newKey: string|string[]|null }`.
**Data Shape:** Foreign keys come from `getForeignKeys` (:618–637) — a knex query on `fkHostTableName` selecting `{id: selfKeyName, foreignId: foreignKeyName}` with `whereIn(self, recordIds).orWhereIn(foreign, linkRecordIds)` and NOT-NULL guards on both columns.

### Decisive source
```ts
/**
 * Tip: for single source of truth principle, we should only trust foreign key recordId
 *
 * 1. get all edited recordId and group by fieldId
 * 2. get all exist foreign key recordId
 */
```
(OneMany/OneOne build a REVERSE index first:)
```ts
const foreignKeysReverseIndexed =
  relationship === Relationship.OneMany || relationship === Relationship.OneOne
    ? groupBy(foreignKeys, 'foreignId')
    : undefined;
```
(Old keys for ManyMany/OneMany come from storage, not the request:)
```ts
const oldKey = foreignKeys?.map((key) => key.foreignId) ?? null;
const newKey = newCellValue?.map((item) => item.id) ?? null;
```

**Flow:** Group contexts by field → for OneOne/ManyOne: reject array newValues, reject >1 stored FK (`Foreign key duplicate`), no-op when unchanged, then reverse-index check throws before any write if the target record is already linked elsewhere; for ManyMany/OneMany: oldKey = stored rows, newKey = requested array, every ADDED id is checked against the reverse index (where defined) to block double-linking.
**Invariant:** `oldKey` truth lives in FK storage (junction row or FK column), because cell JSON can be stale/absent (symmetric fields may not persist a column at all — see integrity plane). A porter who derives oldKey from `oldValue` will corrupt symmetric back-patches and skip deletions.
**Probe:** `grep -cF 'single source of truth' apps/nestjs-backend/src/features/calculation/link.service.ts` → 1; direct test `apps/nestjs-backend/src/features/calculation/link.service.spec.ts` ('reads link junction rows from the data database', :25–56) asserts junction reads route through the DATA db (`queryDataPrismaForTable('tblForeign', …)` called once, meta `$queryRawUnsafe` never called).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getFkRecordMap parseFkRecordItem foreign key", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt storage-as-truth for old link state + relationship-shaped validation (scalar vs array) + pre-write duplicate rejection; adapt error taxonomy; omit teable's i18n context payloads.
