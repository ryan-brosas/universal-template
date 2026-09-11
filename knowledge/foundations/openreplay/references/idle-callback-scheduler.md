<!-- capsule-v2 -->
# requestIdleCb FIFO scheduler — why replace requestIdleCallback with a rAF-chained queue?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What scheduling discipline batches commit work off the hot path without starving?

## In-source Clarity-inspired polyfill: FIFO + one task per frame
**Path/Symbol:** `tracker/tracker/src/main/utils.ts` — `FIFOTaskScheduler` (:~230–289), `requestIdleCb(callback)` (:290–300), consumers `App._nCommit` (`app/index.ts:991`) and `flushBuffer` (:1773).
**Signature:** `addTask(task)`; internal `runTasks()` chains via `requestAnimationFrame`.
**Data Shape:** single queue; `isRunning` latch; next task starts on the NEXT animation frame after the previous promise settles.

### Decisive source
```ts
const executeNextTask = () => {
  if (this.taskQueue.length === 0) { this.isRunning = false; return }
  const nextTask = this.taskQueue.shift()
  Promise.resolve(nextTask()).then(() => {
    requestAnimationFrame(() => executeNextTask())
  })
}
```
```ts
export function requestIdleCb(callback: () => void) {
  // performance improvement experiment;
  scheduler.addTask(callback)
  /**
   * This is a brief polyfill that suits our needs
   * I took inspiration from Microsoft Clarity polyfill on this one
```

**Flow:** commit tick → serialize messages → addTask → worker postMessage happens on its own frame slot → long tasks can't pile up because each awaits completion before scheduling the next rAF.
**Invariant:** Strict FIFO — no priority jumps, or timestamp ordering in a batch breaks replay. The latch prevents concurrent drains from double-posting a batch.
**Probe:** `grep -c 'class FIFOTaskScheduler' tracker/tracker/src/main/utils.ts` → `1`; `grep -c 'Microsoft Clarity polyfill' tracker/tracker/src/main/utils.ts` → `1`; direct tests: none upstream for scheduler (grep-pinned); exercised indirectly by batchWriter e2e suite.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "FIFOTaskScheduler requestIdleCb runTasks", limit: 10 });
```

## Verdict
Adopt frame-chained FIFO. Adapt to scheduler.yield if available. Omit if commit volume is trivial.
