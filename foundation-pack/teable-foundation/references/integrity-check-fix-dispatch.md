<!-- capsule-v2 -->
# Integrity fix dispatcher — why does the check→fix loop re-derive everything through one switch?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does teable guarantee every detectable link-corruption class has exactly one repair path?

## linkIntegrityFix + linkIntegrityCheck
**Path/Symbol:** `apps/nestjs-backend/src/features/integrity/link-integrity.service.ts:linkIntegrityCheck` (:57–199) and `:linkIntegrityFix` (:925–995).
**Signature:** `linkIntegrityCheck(baseId, tableId?): Promise<IIntegrityCheckVo>`; `linkIntegrityFix(baseId, tableId?): Promise<IIntegrityIssue[]>` (the FIX RESULTS).
**Data Shape:** Issues are `{type: IntegrityIssueType, fieldId, tableId?, message}` — fieldId is overloaded as TABLE id for MissingPrimary (in-source comment at :982–983).

### Decisive source
```ts
const checkResult = await this.linkIntegrityCheck(baseId, tableId || '');
const fixResults: IIntegrityIssue[] = [];
for (const issues of checkResult.linkFieldIssues) {
  for (const issue of issues.issues) {
    switch (issue.type) {
      case IntegrityIssueType.MissingRecordReference: { ... foreignKeyIntegrityService.fix ... }
      case IntegrityIssueType.InvalidLinkReference:   { ... linkFieldIntegrityService.fix ... }
      case IntegrityIssueType.ForeignKeyNotFound:
      case IntegrityIssueType.ForeignKeyHostTableNotFound: { ...fixMissingForeignKeyColumns... }
      case IntegrityIssueType.SymmetricFieldNotFound:  { ...fixOneWayLinkField... }
      ...
```
(The checker's scope is deliberately wider than per-table loops:)
```ts
const crossBaseLinkFieldsQuery = this.dbProvider.optionsQuery(FieldType.Link, 'baseId', baseId);
const crossBaseLinkFields = crossBaseLinkFieldsRaw.filter(
  (field) => !tables.find((table) => table.id === field.tableId));
```

**Flow:** Check aggregates SEVEN detectors (per-table link-field structural audit incl. host-table/column existence via `checkTableExist`, symmetric-field presence, one-way consistency; unique-index presence; reference-graph dangling rows; empty-string cells; invalid filter operators; invalid/missing primary fields) across base tables PLUS cross-base inbound links → Fix re-runs check then routes each issue type to its single repairer; unknown types fall through silently (default: break).
**Invariant:** Check is the ONLY source of work items — fixes never scan independently — so repair cannot disagree with detection. Cross-base inbound fields must be checked from the HOST base too, else a remote base's broken link renders as silent data loss. The `fieldId:=tableId` overload for MissingPrimary is load-bearing for the dispatcher.
**Probe:** `grep -cF 'optionsQuery(FieldType.Link' apps/nestjs-backend/src/features/integrity/link-integrity.service.ts` → ≥1; `grep -cF 'IntegrityIssueType.UniqueIndexNotFound' <same>` → present in both check+fix arms.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "linkIntegrityCheck linkIntegrityFix dispatcher issues", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt check-as-single-work-generator + exhaustive type switch; adapt issue taxonomy; omit cross-base scanning if your model forbids cross-base links.
