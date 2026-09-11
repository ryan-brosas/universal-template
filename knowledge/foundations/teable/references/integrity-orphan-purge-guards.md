<!-- capsule-v2 -->
# Dangling-reference purge + junction orphan delete — how are stale graph rows and dead FK pairs removed safely?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does teable clean metadata reference rows pointing at deleted/missing fields, and junction rows pointing at deleted records?

## fixReferenceField (link-integrity) + ForeignKeyIntegrityService
**Path/Symbol:** `apps/nestjs-backend/src/features/integrity/link-integrity.service.ts:fixReferenceField` (:996–1013) + detector `checkReferenceField` (:266–325); `apps/nestjs-backend/src/features/integrity/foreign-key.service.ts:getIssues` (:21–67), `checkInvalidReferences` (:68–122), `fix` (:123–173), `deleteMissingReferences` (:174–199).
**Signature:** `fixReferenceField(fieldId): Promise<IIntegrityIssue|undefined>`; `deleteMissingReferences({fkHostTableName, targetTableName, keyName, routingTableId}): Promise<number>`.
**Data Shape:** Detector returns deleted-but-referenced and referenced-but-nonexistent field ids separately (`deletedFields` vs `cannotFindFields`).

### Decisive source
```ts
const deleted = await this.prismaService.reference.deleteMany({
  where: { OR: [{ fromFieldId: fieldId }, { toFieldId: fieldId }] },
});
if (deleted.count <= 0) return;
```
```ts
if (!fkHostTableName.split('.')[1].startsWith('junction_')) {
  throw new Error(`fkHostTableName: ${fkHostTableName} is not a junction table`);
}
const deleteQuery = this.knex(fkHostTableName)
  .whereNotExists(
    this.knex.select('__id').from(targetTableName)
      .where('__id', this.knex.ref(`${fkHostTableName}.${keyName}`))
  )
  .delete()
  .toQuery();
```

**Flow:** Reference repair = bulk delete BOTH directions of edges for the dead field, no-op when count 0. FK repair = per side (self key → own table, foreign key → foreign table, skipped when that side IS the junction host), anti-join DELETE of junction rows whose target `__id` vanished; P2010 raw-query errors on missing columns are swallowed with a console note in the CHECK path only.
**Invariant:** The junction-name guard (`junction_` prefix after schema dot) is a hard throw — running the anti-join against a data table would mass-delete records. `knex.ref` keeps the correlated column reference unambiguous inside whereNotExists. Fixes return undefined when nothing changed so the dispatcher reports honestly.
**Probe:** `grep -cF 'is not a junction table' apps/nestjs-backend/src/features/integrity/foreign-key.service.ts` → 1; `grep -cF 'whereNotExists' <same>` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "deleteMissingReferences whereNotExists junction", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt bidirectional reference purge + guarded anti-join orphan deletion; adapt the naming guard to your junction convention; omit the P2010 tolerance if your checks always preflight columns.
