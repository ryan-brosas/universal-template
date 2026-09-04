<!-- capsule-v2 -->
# user-snapshot-select-json — How are CreatedBy/LastModifiedBy cells selected without joining a users table?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What SQL rebuilds the user object from stored snapshot columns?

## buildUserJsonObjectFromSnapshot(snapshotRef, idFallbackRef) — no join, snapshot first, id fallback
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/providers/pg-record-query-dialect.ts:buildUserJsonObjectFromSnapshot` (:313-329) + `userTitleFromSnapshot` (:307-312); caller `field-select-visitor.ts:selectSystemUserSnapshot` (:196-204).
**Signature:** `buildUserJsonObjectFromSnapshot(snapshotRef: string, idFallbackRef?: string): string`.
**Data Shape:** snapshot column stores JSON `{id,title,...}` (or text); fallback column is the bare `__created_by` / `__last_modified_by` id.

### Decisive source
```ts
// field-select-visitor:
const expr = this.dialect.buildUserJsonObjectFromSnapshot(snapshotRef, idFallbackRef);
this.state.setSelection(field.id, expr);
return this.qb.client.raw(expr);
```
Upstream direct spec pins the shape: `pg-record-query-dialect.spec.ts` "builds CreatedBy/LastModifiedBy display JSON without users joins" and "builds formula display text from snapshot with system id fallback".

**Flow:** select visitor takes the physical snapshot selector + system id selector → dialect builds a jsonb object preferring the snapshot's fields and degrading to the raw id when the snapshot is empty/malformed → expression registered in selectionMap so filters/sorts on user fields resolve.
**Invariant:** zero joins — user identity at read time comes from write-time snapshots, so renamed/deleted users never change historical cells; the id fallback keeps rows queryable when snapshots predate the format. Any ported schema must store the snapshot or accept id-only display.
**Probe:** upstream direct spec `providers/pg-record-query-dialect.spec.ts:49-70`; static byte-exact: `grep -n 'selectSystemUserSnapshot' field-select-visitor.ts` → :196.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"buildUserJsonObjectFromSnapshot","limit":3,"detail":"ids"}'
```

## Verdict
Adopt join-free snapshot reads with id fallback. Adapt snapshot format. Omit nothing.
