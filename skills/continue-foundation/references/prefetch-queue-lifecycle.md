<!-- capsule-v2 -->
# PrefetchQueue — the chain store that stopped prefetching; abort-swap lifecycle

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** What does the singleton PrefetchQueue actually own, and what is the correct abort/clear/re-arm sequence a porter must reproduce?

## Key facts
**Path/Symbol:** `core/nextEdit/NextEditPrefetchQueue.ts` (whole, 152L) — class docstring :13-17, `process` loop (:63-109), `abort` (:112-118), `clear` (:121-124).
**Signature:** `PrefetchQueue.getInstance(prefetchLimit=3)` (singleton); `enqueueUnprocessed(RangeInFile)` / `dequeueProcessed(): ProcessedItem | undefined` / `process(ctx): Promise<void>` / `abort(): void`; `ProcessedItem = {location: RangeInFile, outcome: NextEditOutcome}`.
**Data Shape:** two FIFOs: `unprocessedQueue: RangeInFile[]` (locations to predict) and `processedQueue: ProcessedItem[]` (built outcomes waiting for the user to navigate into range); `usingFullFileDiff` flag set via `initialize()`.

### Decisive source
```ts
// :14-17 — upstream's confession about what this class became:
// "Think of it as a regular queue, but being a singleton because we need one
// source of truth for the chain. I originally intended this to be a separate
// data structure to handle prefetching next edit outcomes from the model in
// the background. Due to subpar results ... I scratched the idea."

// :112-118 — abort = signal + drain + FRESH controller in one call:
abort(): void {
  this.abortController.abort();
  this.clear();
  this.abortController = new AbortController();   // re-arm for next cycle
}
```
```ts
// :63-68 — process() gates: work available ∧ under limit ∧ not aborted
while (this.unprocessedQueue.length > 0 &&
       this.processedQueue.length < this.prefetchLimit &&
       !this.abortController.signal.aborted) {
```

**Flow:** diff-group router enqueues built outcomes (`enqueueProcessed`, see nextedit-diff-group-router) while legacy `process()` drains unprocessed locations by calling back into `NextEditProvider.provideInlineCompletionItemsWithChain`; errors break the loop only when NOT aborted. Consumers pop processed items with `dequeueProcessed()`/`peekProcessed()` when the cursor enters a queued location's range.

**Invariant:** `abort()` must do all three things atomically — aborting the controller alone leaves stale outcomes that would replay after re-arm; clearing without aborting lets an in-flight `process()` repopulate. The default `prefetchLimit=3` caps MEMORY of built-but-unclaimed suggestions, not LLM calls. The class persists as chain source-of-truth even though its background-prediction role was abandoned mid-project — deleting it breaks deleteChain's `PrefetchQueue.getInstance().abort()` teardown contract.

**Probe:** `grep -c 'this.abortController = new AbortController()' core/nextEdit/NextEditPrefetchQueue.ts` → 2 (:30 field-init in constructor, :117 abort re-arm — getInstance delegates to the constructor); `grep -c 'I scratched the idea' core/nextEdit/NextEditPrefetchQueue.ts` → 1; `grep -c 'provideInlineCompletionItemsWithChain' core/nextEdit/NextEditPrefetchQueue.ts` → 1; `grep -c 'prefetchLimit: number = 3' core/nextEdit/NextEditPrefetchQueue.ts` → 2 (constructor + getInstance).

**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "continue", query: "PrefetchQueue enqueueProcessed abort prefetchLimit", limit: 8 })`

## Verdict
Adopt the two-queue shape and the abort→clear→re-arm triple as one indivisible operation. Omit resurrecting background prediction until suggestion-location algorithms improve (upstream's own verdict); keep the singleton alive if you keep chains.
