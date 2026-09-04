<!-- capsule-v2 -->
# Bounded batch loop — processInBatches with an honest hasMore signal

**Source:** dub AGPL-3.0-or-later (EE dirs separately licensed) `main@873edc5a9727317513c966b8d9b9171794fc89f8`; Codebase Memory `dub`. **Question:** How does a cron/worker chew through a huge row set without exceeding a function timeout — and how does it tell the caller whether work REMAINS?

## processInBatches
**Path/Symbol:** `packages/utils/src/functions/process-in-batches.ts:processInBatches` (4–26).
**Signature:** `processInBatches(maxBatches: number, processBatch: () => Promise<{ count: number }>): Promise<{ hasMore: boolean }>`.
**Data Shape:** `processBatch` returns the number of rows it actually processed (e.g. Prisma `updateMany`/`deleteMany` result `count`); the loop's only completion signal is `count === 0`.

### Decisive source
```ts
if (maxBatches <= 0) throw new Error("maxBatches must be greater than 0.");
for (let batch = 0; batch < maxBatches; batch++) {
  const { count } = await processBatch();
  if (count === 0) return { hasMore: false };   // drained
}
// Exhausted allowed batches. There may still be work left.
return { hasMore: true };
```

**Flow:** run up to `maxBatches` invocations of the caller-supplied batch step; stop early when a batch reports zero affected rows; if the budget expires first, return `hasMore: true` so the caller can re-enqueue/re-schedule instead of pretending completion. Errors from `processBatch` propagate immediately (no swallowing).
**Invariant:** each batch step must itself be LIMITed (the caller's query carries the page size); `hasMore` is a truthful tri-state of "drained" vs "budget exhausted" — never derived from exceptions; `maxBatches ≤ 0` is rejected before any call.
**Probe:** direct test exists — `apps/web/tests/misc/process-in-batches.test.ts` pins: empty-first-batch ⇒ `{hasMore:false}` + 1 call (:5–10); mid-run empty batch stops early (:14–25); full budget with remaining work ⇒ `{hasMore:true}` (:27–34); `maxBatches: 0` rejects (:36–43); errors propagate (:45–52).
**Coverage caveat:** `tests/` is excluded from the graph index by design; probe verified against the on-disk test file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "processInBatches maxBatches hasMore", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt count-driven termination, the hasMore contract for re-scheduling, and the upfront argument guard; adapt what `count` means per ORM and where re-enqueue happens. Omit concurrency inside the loop (deliberately serial). Direct test present.
