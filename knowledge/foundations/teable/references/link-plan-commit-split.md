<!-- capsule-v2 -->
# Plan/commit FK split — why does the engine sometimes derive link changes WITHOUT persisting foreign keys?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How can a consumer capture pre-FK-write old values for computed events inside one transaction, and what must the commit phase rebuild?

## getDerivateByCellContexts / planDerivateByLink / commitForeignKeyChanges
**Path/Symbol:** `apps/nestjs-backend/src/features/calculation/link.service.ts:getDerivateByCellContexts` (:1112–1182), `:planDerivateByLink` (:1741–1791), `:commitForeignKeyChanges` (:1792–1804).
**Signature:** `getDerivateByCellContexts(..., persistFk: boolean): Promise<{cellChanges: ICellChange[]; fkRecordMap: IFkRecordMap}>`.
**Data Shape:** `cellChanges` = `{tableId, recordId, fieldId, oldValue, newValue}` diffs of link cells; `fkRecordMap` = fieldId → recordId → {oldKey,newKey} plan.

### Decisive source
```ts
if (persistFk) {
  await this.saveForeignKeyToDb(fieldMap, fkRecordMap);
  const refreshedRecordMapStruct = this.getRecordMapStruct(...);
  updatedRecordMapByTableId = await this.fetchRecordMap(...); // RE-READ after write
} else {
  updatedRecordMapByTableId = await this.updateLinkRecord(
    tableId, fkRecordMap, fieldMapByTableId, originRecordMapByTableId
  ); // in-memory symmetric patch
}
```
```ts
/**
 * Plan link derivations without persisting foreign keys.
 * ... Useful when consumers need to capture old values
 * for computed events before the FK writes are visible in the same tx.
 */
```

**Flow:** Build projection struct → parse fkRecordMap from storage+contexts → fetch ORIGIN records (overlaying user input for non-link fields) → EITHER (persist path) write FKs then RE-FETCH to observe DB truth incl. symmetric effects, or (plan path) apply `updateLinkRecord`'s relationship-dispatched IN-MEMORY symmetric patches → diff origin vs updated into cellChanges. Commit later re-resolves the field map (accepting caller-supplied TableDomain cache) and calls `saveForeignKeyToDb` alone.
**Invariant:** The two paths must produce IDENTICAL cellChanges semantics — the in-memory patchers (`updateForeignCellFor{ManyMany,ManyOne,OneMany,OneOne}` :265–506 + `fixLinkCellTitle` :507) exist precisely so planning doesn't need the writes; skipping them on the plan path yields phantom/missing symmetric diffs. Re-fetch on the persist path is mandatory because DB triggers/cascades may alter rows.
**Probe:** `grep -cF 'planDerivateByLink' apps/nestjs-backend/src/features/calculation/link.service.ts` → 2 (declaration + doc-comment block).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "planDerivateByLink commitForeignKeyChanges updateLinkRecord", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt plan-vs-commit as the reusable contract for "derive side-effects before writing them"; adapt to your transaction model; omit teable's TableDomain caching plumbing if you lack a domain layer.
