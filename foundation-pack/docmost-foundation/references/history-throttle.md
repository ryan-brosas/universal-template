<!-- capsule-v2 -->
# History throttle — how do you snapshot version history for live docs without a snapshot per save?

**Source:** docmost AGPL-3.0 `main@549cf7c0053bb4f4c3c4e08d588b1f0c69297daf`; Codebase Memory `ext-docmost`. **Question:** How does a delayed, deduplicated queue job produce at-most-one snapshot per activity window, and when is the delay shortened?

## jobId dedupe + age-based fast interval
**Path/Symbol:** `apps/server/src/collaboration/extensions/persistence.extension.ts`:`enqueuePageHistory` (lines 246–258); `apps/server/src/collaboration/processors/history.processor.ts`:`process` (lines 38–123); constants in `apps/server/src/collaboration/constants.ts` (lines 1–3).
**Signature:** `enqueuePageHistory(page: Page): Promise<void>`; BullMQ options `{ jobId: page.id, delay }`.
**Data Shape:** Constants: `HISTORY_INTERVAL = 5min`, `HISTORY_FAST_INTERVAL = 1min`, `HISTORY_FAST_THRESHOLD = 5min` (page age).

### Decisive source
```ts
const pageAge = Date.now() - new Date(page.createdAt).getTime();
const delay = pageAge < HISTORY_FAST_THRESHOLD ? HISTORY_FAST_INTERVAL : HISTORY_INTERVAL;
await this.historyQueue.add(QueueJob.PAGE_HISTORY, { pageId: page.id }, { jobId: page.id, delay });
```
Processor side: skip if no history AND `isEmptyParagraphDoc(page.content)`; compare `isDeepStrictEqual(lastHistory.content, page.content)` before snapshotting; on save failure re-add contributors and RE-THROW so BullMQ retries.

**Flow:** each store flush (re)adds job `page.id` with a fresh delay → dedupe key means only one pending job exists; every flush postpones the snapshot → worker fires after quiet-period → re-checks content equality (flushes raced the enqueue) → snapshots or exits.
**Invariant:** `jobId: page.id` is the throttle — without it every debounced store would queue an unbounded history job per save. The processor must re-verify content equality because jobs are delayed, not serialized against saves. Empty first-version pages never create a baseline history entry.
**Probe:** `grep -cF 'jobId: page.id' apps/server/src/collaboration/extensions/persistence.extension.ts` (=1), `grep -cF 'HISTORY_FAST_THRESHOLD = 5 * 60 * 1000' apps/server/src/collaboration/constants.ts` (=1), `grep -cF 'isEmptyParagraphDoc(page.content as any)' apps/server/src/collaboration/processors/history.processor.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-docmost", query: "enqueuePageHistory HISTORY_INTERVAL jobId delay history", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt deduped delayed-job throttling keyed by entity id + quiet-period content re-check as the portable versioning throttle; adapt queue tech; omit docmost's specific watcher/notification fan-out. No upstream direct test for the processor; pinned by source read + probes.
