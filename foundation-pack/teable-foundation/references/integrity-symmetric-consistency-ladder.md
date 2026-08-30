<!-- capsule-v2 -->
# Symmetric-link consistency ladder — what structural facts must hold between a link field, its twin, and its FK storage?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Which checks decide a link field's options JSON is structurally broken, and how is one-wayness repaired instead of fabricating a twin?

## checkTableLinkFields + fixOneWayLinkField
**Path/Symbol:** `apps/nestjs-backend/src/features/integrity/link-integrity.service.ts:checkTableLinkFields` (:326–435), `:fixOneWayLinkField` (:1197–1234); data-plane twins in `link-field.service.ts:getIssues` (:21–49)/`fix` (:144–207) via dbProvider `integrityQuery().checkLinks/fixLinks`.
**Signature:** `checkTableLinkFields(table: {id; name; fields: Field[]}): Promise<IIntegrityIssue[]>`.
**Data Shape:** Options parsed from the field row's JSON (`ILinkFieldOptions`: foreignTableId, fkHostTableName, selfKeyName, foreignKeyName, symmetricFieldId?, isOneWay?).

### Decisive source
```ts
if (options.symmetricFieldId) {
  const symmetricField = await this.prismaService.field.findFirst({
    where: { id: options.symmetricFieldId, deletedTime: null }});
  if (!symmetricField) { issues.push({ type: IntegrityIssueType.SymmetricFieldNotFound, ... }); }
}
if (!options.isOneWay && !options.symmetricFieldId) {
  issues.push({ ... message: `Symmetric is missing for link field ...` });
}
```
```ts
if (!options.isOneWay && !options.symmetricFieldId) {
  // repair = declare one-way rather than inventing a twin
  await this.prismaService.field.update({ where: { id: fieldId },
    data: { options: JSON.stringify({ ...options, isOneWay: true }) } });
}
if (options.isOneWay && options.symmetricFieldId) {
  // contradictory state: drop the stale symmetric reference
  ... options: JSON.stringify({ ...options, isOneWay: undefined }) ...
}
```

**Flow:** Per link field: foreign table exists → host TABLE exists (`checkTableExist`, routed through the DATA executor for BYODB safety) → both key COLUMNS exist (only then can deeper checks run — `canCheckLinks`) → symmetric twin exists when referenced → non-one-way fields must carry a twin. Data-plane check then compares cell JSON against junction/FK truth (`checkLinks`) and rewrites cells from storage (`fixLinks`). Repair of missing-twin is a DECLARATION flip to one-way (never synthesizes the other field); contradictory isOneWay+twin drops the dangling reference.
**Invariant:** Structural preflights gate semantic checks (missing columns would crash comparison SQL). One-way conversion is the only safe fix for a vanished twin because creating a real symmetric field requires base-duplication machinery (primary-field lookup — see primary-promotion capsule).
**Probe:** `grep -cF 'checkColumnExist' apps/nestjs-backend/src/features/integrity/link-integrity.service.ts` → ≥2; direct test `link-field.service.spec.ts` (:9–66 'checks/fixes link data through the data database') pins integrityQuery routing + meta-db isolation (`expect(metaQueryRawUnsafe).not.toHaveBeenCalled()`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "checkTableLinkFields fixOneWayLinkField symmetricFieldId", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt existence-gated structural ladder + declare-one-way repair + storage-over-JSON cell rewrite; adapt to your options schema; omit BYODB routing if single-database.
