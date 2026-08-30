<!-- capsule-v2 -->
# Airtable link fill — how do spilled cells become link writes with honest drop/truncate accounting?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** In what order are spilled link rows remapped and written, and which three issue classes must the fill produce?

## fillLinkValues streaming fill
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts`:`fillLinkValues` (:1579–1685).
**Signature:** `private async fillLinkValues(params): Promise<void>` — consumes `linkSpill`, `recordIdMaps`, `linkRuntimes`.
**Data Shape:** writes batch at `linkUpdateBatchSize = 100` via updateRecords (`typecast: false` — ids must already be exact); three accounting maps: `droppedByField` (foreign record not found), `truncatedByField` (single-link over-capacity), `missingByField` (field never created).

### Decisive source
```ts
// Only write link fields that actually exist; one that failed to
// materialize is skipped and reported, never fatal to the import.
const existingFieldIds = new Set((await this.fetchFieldMeta(tableId)).keys());
...
const foreignMap = recordIdMaps.get(runtime.plan.airtableForeignTableId);
const mappedIds = cell.ids.map((id) => foreignMap?.get(id)).filter((id): id is string => id != null);
const droppedCount = cell.ids.length - mappedIds.length;
if (droppedCount > 0) droppedByField.set(...);
if (mappedIds.length === 0) continue;
const isSingle = runtime.relationship === Relationship.ManyOne;
if (isSingle && mappedIds.length > 1) {
  // The Airtable field declared single links but the data disagrees.
  truncatedByField.set(..., mappedIds.length - 1);
}
fields[teableFieldId] = isSingle ? { id: mappedIds[0] } : mappedIds.map((id) => ({ id }));
```

**Flow:** per table with links → re-fetch live field existence (a failed create in the earlier phase must not receive writes) → stream rows back from the spill part-by-part → remap each cell's airtable ids through the foreign table's old→new map → count unmapped as dropped, skip empty results → single-link cells keep only mappedIds[0] and COUNT the truncation → batched updates of 100 → flush tail → emit all three issue classes.
**Invariant:** The runtime's relationship may have been relaxed to ManyMany by `relaxOversizedSingleLinks` before fill (conversion while the field is still empty is trivially safe); a failed relaxation falls back to truncate-and-report here. Memory stays flat: rows stream from storage, nothing accumulates. Link values write with typecast:false because every id was minted by this import.
**Probe:** `grep -cF "existingFieldIds.has(teableFieldId)" apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts` returns 1; direct test `airtable-schema-mapper.spec.ts` covers planning; service-level spec pins relationship semantics via `decideRelationship`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"fillLinkValues linkUpdateBatchSize truncatedByField","limit":5,"detail":"ids"}'
```

## Verdict
Adopt streamed remap-and-fill with three-way accounting for any deferred-relation materialization; adapt batch size; omit teable's specific update API shapes. Coverage caveat: none.
