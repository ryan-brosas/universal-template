<!-- capsule-v2 -->
# Airtable import phase ladder — why must tables→links→records→derived fields execute in that exact order?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** In what order does an Airtable base import run its phases, and which reordering mistakes break or silently corrupt the import?

## Import pipeline phase order
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts`:`AirtableImportService.importBase` (:209–405).
**Signature:** `importBase(ro: IImportAirtableRo, onProgress?: IAirtableImportProgressReporter): Promise<IImportAirtableVo>`.
**Data Shape:** `ro` carries `airtableBaseId`, optional target `baseId`/`spaceId`+`baseName`, flags `importRecords`/`importAttachments` (default true) and `importViewConfig` (default false), optional `shareLink`. Output: `{base, tableIdMap, fieldIdMap, issues}` where both maps key by Airtable id and `issues` is the append-only degradation log threaded through every helper.

### Decisive source
```ts
// Complete the table structure before data with link fields only — they
// follow the relationship Airtable declares. Derived fields (lookups,
// counts) and view configuration are applied AFTER the records, so a field
// that cannot be computed degrades to a reported issue instead of breaking
// record/link writes and aborting the whole import.
progress({ phase: 'creating_links' });
const linkRuntimes = await this.createLinkFields({ plan, tableIdMap, viewIdMap, issues });
...
await this.relaxOversizedSingleLinks({...});
await this.fillLinkValues({...});
...
// Derived fields are computed over the imported data; create them last so a
// single uncomputable field is reported, never fatal to the whole import.
await this.createLookupFields(plan, tableIdMap, issues);
await this.createCountFields(plan, tableIdMap, issues);
await this.createRollupFields(plan, tableIdMap, airtableTables, issues);
await this.createFormulaFields(plan, tableIdMap, issues);
```

**Flow:** fetch_schema → resolve share client + rollup sources (only when importViewConfig) → build plan (`buildAirtableImportPlan`) → create/get base → create tables with phase-1 plain fields + view shells → create link fields only → stream records per table (collecting link rows to spill) → relax oversized single links → fill link values from spill → create lookups → counts → rollups → formulas (dependency passes) → reorder view columns to source field order → apply view configs last.
**Invariant:** A field that cannot be created/computed degrades into an `issues[]` entry; it never aborts record writes or the import. Links are created before records (structure complete first) but FILLED after all records exist because the old→new record-id map must be total. View config runs after every field exists so sorts/groups referencing lookups resolve.
**Probe:** `grep -cF "countall({values})" apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts` from repo root returns 1 (count-as-rollup expression lives in the derived-fields phase, not the table-creation payload). Direct test: `airtable-import.service.spec.ts` pins `decideRelationship` and `applyAiConfig` behavior at the phase boundaries.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"importBase creating_links fillLinkValues","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the phase ordering and degrade-to-issue discipline for any schema-migration-style importer; adapt phase names/progress events to host transport; omit teable's specific SSE wiring if the host streams differently. Coverage: file fully indexed (check_index_coverage no_recorded_issue).
