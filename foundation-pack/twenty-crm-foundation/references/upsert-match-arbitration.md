<!-- capsule-v2 -->
# upsert-match-arbitration — When one input row matches several existing rows across different unique keys, which one wins?

**Source:** twenty-crm (AGPL-3.0 — patterns only, never verbatim), main@a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0; Codebase Memory `ext-twenty-crm`. **Question:** What is the exact match → update/insert routing rule and its ambiguity guard?

## upsert-match-arbitration
**Path/Symbol:** `packages/twenty-server/src/engine/api/common/common-query-runners/common-create-many-query-runner/utils/get-matching-record-id.util.ts:getMatchingRecordId` (:13-86) + `utils/categorize-records.util.ts:categorizeRecords` (:8-34).
**Signature:** `getMatchingRecordId(record, conflictingFieldGroups, existingRecords): string | undefined`; `categorizeRecords(records, groups, existing): {recordsToUpdate: (record & {id})[], recordsToInsert}`.
**Data Shape:** match evaluation is per GROUP: all group properties must be defined on the input AND equal (===) on the candidate; first matching candidate per group wins (`Array.find`); group hits collect into `matchingRecordIds`.

### Decisive source
```ts
if ([...new Set(matchingRecordIds)].length > 1) {
  // ...builds "baseFields (path: value, ...); baseFields (...)" diagnostic...
  throw new CommonQueryRunnerException(
    `Multiple records found with the same unique field values for ${conflictingFieldsValues}. Cannot determine which record to update.`,
    CommonQueryRunnerExceptionCode.UPSERT_MULTIPLE_MATCHING_RECORDS_CONFLICT,
    ...
```
(:51-83 — distinct-match-count > 1 is a LOUD throw, not a silent pick.)

**Flow:** per record, scan every conflict group → a group matches when every property is defined and strictly equals the same existing record → collect matched ids → 0 matches ⇒ insert path; ≥1 ⇒ update with the matched id stamped onto the record (`categorizeRecords` :26-31) → **two DIFFERENT ids matched via different keys ⇒ throw UPSERT_MULTIPLE_MATCHING_RECORDS_CONFLICT** with a rendered per-key diagnostic. Note the asymmetry: the SAME id matched by several keys is fine (:146 spec case "returns the matching id if multiple conflicting fields point to the same existing record").
**Invariant:** never guess between two conflicting identities — fail the whole request loudly (the throw happens inside per-record arbitration, aborting the batch). Strict equality means no coercion: `"1" !== 1`. Composite matching requires ALL members, mirroring the DB constraint.
**Probe:** `grep -c 'UPSERT_MULTIPLE_MATCHING_RECORDS_CONFLICT' packages/twenty-server/src/engine/api/common/common-query-runners/common-create-many-query-runner/utils/get-matching-record-id.util.ts` → 2 (code + throw site); direct spec: `src/engine/api/common/common-query-runners/common-create-many-query-runner/utils/__tests__/get-matching-record-id.util.spec.ts` ("throws when conflicting fields match different existing records", "returns undefined when only part of a composite unique field matches").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-twenty-crm", query: "getMatchingRecordId", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the arbitration ladder (per-key first-match → same-id collapse → different-ids throw) and the strict-equality/no-coercion stance. Adapt the exception type to your error taxonomy but keep it user-facing-safe (rendered key values only). Omit Twenty's lingui message wrappers.
