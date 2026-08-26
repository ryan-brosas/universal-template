<!-- capsule-v2 -->
# Foreach fluid-concurrency queue — fastq worker with kill-on-first-non-success

**Source:** mastra Apache-2.0 `main@502653550fb45d8e72dfdd57732161f9176dbcf2`; Codebase Memory `ext-mastra`. **Question:** How does foreach keep `concurrency` items in flight without batch barriers, and how does it stop?

## Deliberate migration from Promise.all slices to a callback queue
**Path/Symbol:** `packages/core/src/workflows/handlers/control-flow.ts:executeForeach` (:901-1443), queue core :1001-1230.
**Signature:** `const queue = fastq(worker, concurrency)`; worker `(task: {item, k, resumeToUse}, cb: DoneCallback) => Promise<void>`.
**Data Shape:** `inFlight` counter incremented at enqueue (:1219) and decremented in the worker's tail; `resolveCompletion` promise released when the LAST in-flight item drains (`if (inFlight === 0) resolveCompletion?.()` — appears on both cancel and normal paths). Results are index-addressed: `results[k] = result.output` so output order matches input order regardless of completion order.

### Decisive source
```ts
// Use a fastq callback-based queue for fluid concurrency.
// Unlike the previous batch approach (Promise.all on slices), this starts the
// next item as soon as any slot frees up, keeping `concurrency` items running
// at all times instead of waiting for an entire batch to finish.
...
/** Drain all queued (not yet in-flight) tasks and kill the queue. */
const killQueue = () => {
  inFlight -= queue.length();
  queue.kill();
};
```

**Flow:** resolve concurrency → enqueue all non-skipped items (already-succeeded/suspended ones short-circuit :1176-1207) → workers pull as slots free → any non-success (suspended/failed/exit) or thrown error calls `killQueue()` draining queued-but-unstarted tasks → wait for in-flight drain via `resolveCompletion` → classify final status.
**Invariant:** `killQueue` must decrement `inFlight` by `queue.length()` BEFORE killing, otherwise the completion promise never resolves (the count includes queued-not-started tasks). Completion is detected by the in-flight counter hitting zero, not by queue.idle() — because kill() leaves no drain callback. Output array stays order-true by writing `results[k]`, never pushing.
**Probe:** `grep -c 'killQueue()' packages/core/src/workflows/handlers/control-flow.ts` from repo root (=3: handleNonSuccessResult :1089 + catch path :1165 + cancel path inside worker :1117). Direct tests: `packages/core/src/workflows/evented/workflow-event-processor/foreach-concurrency.test.ts`, `foreach-failure-progress.test.ts:143 'preserves successful iterations regardless of concurrent completion order'`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "executeForeach fastq concurrency queue", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: fluid concurrency + kill-drain accounting + index-keyed results. Adapt `fastq` to your queue lib but keep the decrement-before-kill invariant. Omit per-iteration watch-event progress payloads if eventless.
