<!-- capsule-v2 -->
# Bounded concurrency map — how do you parallelize async tasks while preserving result order?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What is the shared-cursor worker-pool primitive the importer uses for attachment transfers, and what must it guarantee?

## mapWithConcurrency
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts`:`mapWithConcurrency` (:98–115).
**Signature:** `const mapWithConcurrency = async <T, R>(items: T[], limit: number, task: (item: T) => Promise<R>): Promise<R[]>`.
**Data Shape:** results preallocated to `items.length`; a shared `next` cursor hands out indexes; `Math.min(limit, items.length)` workers.

### Decisive source
```ts
/** Runs tasks with bounded concurrency, preserving the result order. */
const mapWithConcurrency = async <T, R>(
  items: T[],
  limit: number,
  task: (item: T) => Promise<R>
): Promise<R[]> => {
  const results: R[] = new Array(items.length);
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (true) {
      const index = next++;
      if (index >= items.length) return;
      results[index] = await task(items[index]);
    }
  });
  await Promise.all(workers);
  return results;
};
```

**Flow:** spin up min(limit, N) workers → each claims the next index with `next++` (single-threaded event loop makes this race-free without locks) → writes land at the CLAIMED index so output order equals input order regardless of completion order → Promise.all joins. The importer uses it with `attachmentConcurrency = 3` over attachment cells; failures are caught INSIDE the task (per-cell try/catch feeding failedAttachments), so one bad CDN file never rejects the pool.
**Invariant:** Order preservation comes from index-claimed writes, not from awaiting in sequence. Concurrency is bounded but work-stealing — a fast cell never waits for a slow sibling's slot. This is the same shape recorded fleet-side as `order-preserving-concurrency-map` (outbox redrive/anomaly sweeps reuse it).
**Probe:** `grep -cF "results[index] = await task(items[index])" apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts` returns 1; `grep -cF "attachmentConcurrency" ...` returns 2 (definition + use).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"mapWithConcurrency attachmentConcurrency","limit":5,"detail":"ids"}'
```

## Verdict
Adopt as-is (~18 lines, zero deps) anywhere you need ordered bounded-parallel async work; adapt limit; omit nothing. Coverage caveat: none.
