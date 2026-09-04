<!-- capsule-v2 -->
# Coalescing advisory-lock funnel — "How do two concurrent event batches coalesce without double-inserting the same merge identity?"

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `ext-twenty-crm`. **Question:** How is a read-then-merge-or-insert coalescing window (10 minutes) made race-free across workers?

## Sorted transaction-scoped pg advisory locks around read + write
**Path/Symbol:** `packages/twenty-server/src/modules/timeline/repositories/timeline-activity.repository.ts:ACQUIRE_TIMELINE_ACTIVITY_MERGE_LOCK,acquireMergeLocks` (:27-29, :160-189).
**Signature:** lock names = `JSON.stringify(['timeline-activity-merge', workspaceId, objectSingularName, payload.recordId, payload.workspaceMemberId ?? null, payload.timelineActivityTypeId])`, deduped, `.sort()`ed; one raw query: `SELECT pg_advisory_xact_lock(hashtextextended("lockName", 0)) FROM unnest($1::text[]) WITH ORDINALITY ... ORDER BY "ordinality"`.
**Data Shape:** Batch of TimelineActivityPayload; per-payload lock identity = (workspace, object, recordId, member|null, typeId) — deliberately COARSER than the full merge-key which also includes timelineActivityTypeSnapshot fields.

### Decisive source
```ts
const lockNames = [...new Set(payloads.map((payload) =>
  JSON.stringify(['timeline-activity-merge', workspaceId, objectSingularName,
    payload.recordId, payload.workspaceMemberId ?? null,
    payload.timelineActivityTypeId]),
))].sort();
await transactionScope.executeRawQuery(ACQUIRE_TIMELINE_ACTIVITY_MERGE_LOCK, [lockNames]);
```

**Flow:** runInWorkspaceTransaction begins → acquireMergeLocks blocks until EVERY distinct merge identity in the batch is locked (xact-scoped: auto-released at commit/rollback) → only then findRecentTimelineActivities reads the 10-minute window → merge-or-insert decision → update+insert writes inside the SAME transaction. Two workers racing the same record: the second waits on the first's transaction, then sees the fresh row and merges instead of duplicating.
**Invariant:** (1) Lock names sorted lexicographically BEFORE acquisition — batch-order-independent deadlock prevention (direct spec feeds payloads out of order and asserts sorted JSON array). (2) The recent-row READ happens strictly after ALL locks are held — reading before locking reintroduces the duplicate-insert race this closes (618fe500). (3) Snapshot-differentiated payloads share one lock so both variants serialize.
**Probe:** `grep -cF 'pg_advisory_xact_lock' packages/twenty-server/src/modules/timeline/repositories/timeline-activity.repository.ts` → 1 (single statement constant); direct test `src/modules/timeline/repositories/__tests__/timeline-activity.repository.spec.ts` "locks merge identities in a stable order before reading recent rows".

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-twenty-crm","query":"pg_advisory_xact_lock unnest ordinality locks","limit":5,"detail":"ids"}'
```

## Verdict
Adopt sorted-lock-then-read-then-write as THE pattern for any check-then-insert coalescing ledger under concurrency. Adapt lock naming to host (any deterministic string key works; hashtextextended maps it to the bigint lock space). Omit nothing. Direct test exists upstream and pins both sort order and read-after-lock sequencing.
