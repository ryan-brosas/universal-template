<!-- capsule-v2 -->
# Symmetric-link planned seeding — how do you cover the far side of a link edit before the write commits?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When a cell write changes a Link field value, how do the symmetric field and foreign-table records enter the impact set?

## plannedForeignRecordIds pre-seed
**Path/Symbol:** `apps/nestjs-backend/src/features/record/computed/services/computed-dependency-collector.service.ts:collect` (:1560–1633).
**Signature:** internal step of `collect()`; produces entries in `plannedForeignRecordIds[foreignTableId]` merged into `explicitSeeds` before the first link closure.

### Decisive source
```ts
// Also include symmetric link fields (if any) on the foreign table so their values   // :1560
// are refreshed as well. The link fields themselves are already included by SQL union...
for (const lf of linkFields) {
  const optsLoose = this.parseOptionsLoose<ILinkOptionsWithSymmetric>(lf.options);
  ...
  // Also pre-seed foreign impacted recordIds using planned link targets
  // Extract ids from both oldValue and newValue to cover add/remove                  // :1586
  const toIds = (v: unknown) => { ...arr.map((x) => (x && typeof x === 'object' ? (x as {id?:string}).id : undefined))... };
  toIds(ctx.oldValue).forEach((id) => targetIds.add(id));
  toIds(ctx.newValue).forEach((id) => targetIds.add(id));
```

**Flow:** changed Link fields are located among the incoming cell contexts; their options are parsed loosely (`parseOptionsLoose` accepts object-or-string, returns null on malformed :213–224); if a `symmetricFieldId` exists, it is added to the FOREIGN table's field set, and BOTH old and new link-target ids become explicit seeds for the foreign table (:1588–1604). This matters because junction rows may not exist yet (new link) or were deleted (removed link) — pure junction-walking would miss both directions.
**Invariant:** Old-value ids are load-bearing for removals: a record unlinked this transaction would vanish from junction-derived sets but must still refresh its now-stale symmetric display. Seeding happens BEFORE `computeLinkClosure`, so downstream conditional/link expansion covers them normally.
**Probe:** needle verified at this pin (`toIds(ctx.oldValue)` :1598); exercised by `packages/v2/e2e/src/createRecordLink.e2e.spec.ts` (link add/remove symmetry); graph retrieval `resolveRelatedLinkFieldIds` resolves :584–614.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "resolveRelatedLinkFieldIds", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt old∪new seed extraction for relationship edits; adapt option parsing strictness (loose-parse + null-skip beats throw for legacy rows); omit the specific field-type names.
