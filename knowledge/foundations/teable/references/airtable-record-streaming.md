<!-- capsule-v2 -->
# Airtable record streaming — why are create batches sent reversed, and how does an expired listing resume without duplicates?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How do you stream Airtable records into a target that assigns descending creation order, and how must a pagination-iterator restart dedupe?

## Page loop with reversed batch writes
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts`:`importTableRecords` (:776–908).
**Signature:** `private async importTableRecords(params): Promise<void>` — params include `client`, `tablePlan`, `usersByEmail`, `recordIdMaps`, `linkSpill`, `linkFieldsWithMulti`, `issues`.
**Data Shape:** per-table local `recordIdMap: Map<airtableRecordId, teableRecordId>` registered into the shared `recordIdMaps`; `droppedCollaborators` / `failedAttachments` aggregate per-field counts for end-of-table issue emission; `processedRows` feeds progress.

### Decisive source
```ts
// Teable assigns each create batch a descending order, which flips the
// rows in the view. Send the batch reversed so records keep the source
// order, then map results back by their original index.
const created = await this.recordOpenApiV2Service.createRecords(tableId, {
  fieldKeyType: FieldKeyType.Id,
  typecast: true,
  records: payloads.slice().reverse(),
});
const createdInOrder = created.records.slice().reverse();
records.forEach((record, recordIndex) => {
  const createdRecord = createdInOrder[recordIndex];
  if (createdRecord) recordIdMap.set(record.id, createdRecord.id);
});
...
} catch (error) {
  if (error instanceof AirtableIteratorExpiredError && restarts < maxListRestarts) {
    restarts++; ... continue;
  }
  throw error;
}
```
Plus the restart guard at page top: `const records = page.filter((record) => !recordIdMap.has(record.id));`

**Flow:** while(true) → iterate `client.listRecords` pages (100/page) → skip already-mapped ids → build payloads → reverse-batch create → un-reverse results → zip map old→new ids → collect link cells to spill → on `AirtableIteratorExpiredError` (HTTP 422 `LIST_RECORDS_ITERATOR_NOT_AVAILABLE`) restart listing up to `maxListRestarts = 2`.
**Invariant:** The id-map filter is what makes a mid-stream restart duplicate-free; the double `.slice().reverse()` is symmetric — dropping either one flips row order in every view. Tables that no link points at have their map deleted after import (`linkTargetTables` set) to bound memory to link targets only.
**Probe:** `grep -cF "slice().reverse()" apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts` returns 2 (send + map-back); `grep -cF "maxListRestarts" ...` returns 3.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"importTableRecords AirtableIteratorExpiredError recordIdMap","limit":5,"detail":"ids"}'
```

## Verdict
Adopt reverse-batch creation against any target with descending creation-order semantics and the id-set-filtered iterator restart; adapt batch size and progress events; omit Airtable-specific error typing if the host source has no iterator expiry. Coverage caveat: none — file fully indexed.
