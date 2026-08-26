<!-- capsule-v2 -->
# Update-event timestamp authority — "Whose `updatedAt` wins when the RETURNING clause and the event snapshot disagree?"

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `ext-twenty-crm`. **Question:** How do you force DB-computed columns into a RETURNING-limited UPDATE and decide which observed value is authoritative for published events?

## Two halves: forced columns + returned-timestamp override
**Path/Symbol:** `packages/twenty-server/src/engine/twenty-orm-v2/repository/utils/update-event-records.util.ts:getUpdateEventColumnsToReturn,mergeReturnedUpdateTimestamps` (:7-13, :15-35).
**Signature:** `getUpdateEventColumnsToReturn(columnsToReturn: string[], tableShape): string[]`; `mergeReturnedUpdateTimestamps(eventRecords, returnedRecords): ObjectRecord[]`.
**Data Shape:** First fn: requested column list + workspace table shape (has `columnShapeByColumnName`). Second fn: event records (full merged snapshots) + TypeORM generatedMaps rows (only the columns RETURNING emitted). Output = event records with updatedAt possibly replaced.

### Decisive source
```ts
isDefined(tableShape.columnShapeByColumnName.updatedAt)
  ? [...new Set([...columnsToReturn, 'id', 'updatedAt'])]
  : [...new Set([...columnsToReturn, 'id'])]
```
```ts
return eventRecords.map((eventRecord) => {
  const returnedRecord = isNonEmptyString(eventRecord.id)
    ? returnedRecordsById.get(eventRecord.id)
    : undefined;
  const returnedUpdatedAt = returnedRecord?.updatedAt;
  return isDefined(returnedUpdatedAt)
    ? { ...eventRecord, updatedAt: returnedUpdatedAt }
    : eventRecord;
});
```

**Flow:** At every update site the RETURNING list becomes columnsToReturn PLUS id PLUS updatedAt (when the object has one) so the DB's trigger-maintained timestamp comes back → post-write snapshot re-read happens separately (may not observe the final committed value) → merge order: getUpdateEventRecords pairs before/after, then set-values overlay, THEN mergeReturnedUpdateTimestamps stamps the RETURNED updatedAt over whatever the snapshot read saw.
**Invariant:** The RETURNING row is the authority for updatedAt; the snapshot read never overrides it — but only when actually returned (`isDefined` gate keeps event data otherwise untouched; spec pins "keeps the event timestamp when the mutation did not return one"). `id` is force-added unconditionally because both pairing and timestamp merge key on it. Set-dedupe via `new Set` because callers pass overlapping lists per input record.
**Probe:** `grep -n 'isDefined(tableShape.columnShapeByColumnName.updatedAt)' packages/twenty-server/src/engine/twenty-orm-v2/repository/utils/update-event-records.util.ts` → line 11; direct test `src/engine/twenty-orm-v2/repository/utils/__tests__/update-event-records.util.spec.ts` (both directions pinned).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-twenty-crm","query":"mergeReturnedUpdateTimestamps","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the two-contract split (forced-return columns vs authoritative-value overlay) whenever events must reflect DB-side computed values that a limited RETURNING would hide. Adapt which columns are "authority" per host (here updatedAt; same shape works for any trigger-maintained column). Omit the v1/v2 dual-repo plumbing. Direct unit specs exist upstream.
