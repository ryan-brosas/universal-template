<!-- capsule-v2 -->
# upsert-spine-choreography — In what ORDER does an upsert execute its phases, and why can't they be reordered?

**Source:** twenty-crm (AGPL-3.0 — patterns only, never verbatim), main@a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0; Codebase Memory `ext-twenty-crm`. **Question:** What is the full phase choreography of the create/upsert runner (batch cap, conflict probe, categorize, update-before-insert, read-back, result stitching)?

## upsert-spine-choreography
**Path/Symbol:** `packages/twenty-server/src/engine/api/common/common-query-runners/common-create-many-query-runner/common-create-many-query-runner.service.ts:CommonCreateManyQueryRunnerService.run/performUpsertOperation` (:64-131, :279-365); one-record entry `common-create-one-query-runner.service.ts:run` (:36-49) delegates by wrapping `data: [args.data]` and taking `result[0]`.
**Signature:** `run(args: CommonExtendedInput<CreateManyQueryArgs>, ctx): Promise<ObjectRecord[]>`; upsert flag arrives as `args.upsert`; position backfill switches on it (`shouldBackfillPositionIfUndefined: !args.upsert`, :68 and :195).
**Data Shape:** result is a TypeORM-style `InsertResult` assembled MANUALLY across the two write legs (:330-334 empty seed; identifiers/generatedMaps pushed from update leg :528-533 and insert leg :579-581).

### Decisive source
```ts
const { recordsToUpdate, recordsToInsert } = categorizeRecords(args.data, conflictingFieldGroups, existingRecords);
const recordsToInsertWithPosition = await this.backfillPositionForInserts({...});
...
if (recordsToUpdate.length > 0) { await this.processRecordsToUpdate({...}); }
await this.processRecordsToInsert({ recordsToInsert: recordsToInsertWithPosition, ... });
```
(:317-364 — updates are processed BEFORE inserts.)

**Flow:** cap guard (`data.length > QUERY_MAX_RECORDS` throws TOO_MANY_RECORDS_TO_UPDATE with a copy-paste "upsert" message even for plain creates, :68-76) → require flatIndexMaps (:89-95) → non-upsert path: straight `repository.insert` (orm-v2 feature-flagged branch) :236-263 → upsert path: derive conflict groups → ONE probe query for all candidate conflicts → categorize → backfill positions ONLY for insert-leg records (via RecordPositionService with `shouldBackfillPositionIfUndefined: true`) → run UPDATE leg first (stripping system `createdBy` when `isSystem`, re-adding `deletedAt: null` to revive soft-deleted matches :482-493) → INSERT leg → fetch everything back by id IN(...) `.withDeleted().take(QUERY_MAX_RECORDS)` and RE-SORT to input order via a Map index (:611-628) → process nested relations → return.
**Invariant:** (1) update leg precedes insert leg — matched rows must be reconciled before new rows claim positions/keys; (2) returned array order MUST equal input order regardless of DB return order (explicit sort, :624-628) — callers index results positionally; (3) `createdBy` is never updated on existing rows (system-field strip :674-678) — actor provenance belongs to row creation only; (4) read-back includes soft-deleted rows so revived rows appear in the response.
**Probe:** `grep -n 'recordsToUpdate.length > 0' packages/twenty-server/src/engine/api/common/common-query-runners/common-create-many-query-runner/common-create-many-query-runner.service.ts` → line 344 before the unconditional insert call at 356.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-twenty-crm", query: "performUpsertOperation fetchUpsertedRecords", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the phase order and its justifications (cap → metadata gate → probe-once → categorize → position-backfill-inserts-only → update-first → insert → ordered read-back). Adapt batch caps and feature-flag branches to your host. Omit orm-v2 dual-path if you have a single write engine; keep the manual InsertResult stitching and positional-order restoration either way.
