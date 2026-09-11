<!-- capsule-v2 -->
# ORM update-event pairing — "Which record does an update event's `after` snapshot come from when RETURNING didn't return it?"

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `ext-twenty-crm`. **Question:** How are pre-write and post-write records paired so internal events never publish a stale or misaligned `recordsAfter` snapshot?

## getUpdateEventRecords — id-keyed pairing over before/after arrays
**Path/Symbol:** `packages/twenty-server/src/engine/twenty-orm/utils/merge-records-with-update-values.util.ts:getUpdateEventRecords` (:42-57).
**Signature:** `getUpdateEventRecords<TRecord>(recordsBefore: TRecord[], recordsAfter: TRecord[]): TRecord[]`.
**Data Shape:** Two flat ObjectRecord arrays (unformatted/noFormatting snapshots). Output length === recordsBefore.length; element i is either the post-write row sharing before[i]'s id, or before[i] itself as fallback.

### Decisive source
```ts
return recordsBefore.map((recordBefore, index) =>
  isNonEmptyString(recordBefore.id)
    ? (recordsAfterById.get(recordBefore.id) ?? recordBefore)
    : (recordsAfter[index] ?? recordBefore),
);
```

**Flow:** Build Map(id → after-record) filtering to non-empty-string ids first (null/undefined ids can never collide) → map BEFORE array positionally → string-id records resolve by id lookup, missing = keep before-row verbatim → non-string-id records fall back to positional index pairing.
**Invariant:** Event output is anchored on the BEFORE array, never AFTER: a stale/partial post-write read shrinks nothing — unmatched records pass through as their pre-write selves (spec pins exactly this: second record keeps "Second before"). Positional fallback only applies when ids are unusable.
**Probe:** `grep -n 'getUpdateEventRecords(before, after)' packages/twenty-server/src/engine/twenty-orm/repository/workspace-update-query-builder.ts` → line 276 (legacy batch-update after-merge input); direct test `src/engine/twenty-orm/utils/__tests__/merge-records-with-update-values.util.spec.ts` ("matches post-write records to pre-write records by id", "falls back to the pre-write record when the post-write read is stale").

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-twenty-crm","query":"getUpdateEventRecords","limit":3,"detail":"ids"}'
```

## Verdict
Adopt id-keyed pairing with before-array anchoring and pass-through fallback whenever emitting before/after event pairs from separate reads. Adapt the id field name per host schema. Omit nothing behavioral — the util is self-contained. Direct unit specs exist upstream; port them too.
