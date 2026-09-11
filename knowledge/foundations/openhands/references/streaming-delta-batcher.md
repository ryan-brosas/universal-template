<!-- capsule-v2 -->
# Streaming delta batcher — committing token floods at most once per frame without letting durable events overtake their own streamed text

**Source:** OpenHands / All-Hands-AI MIT `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How do you coalesce adjacent LLM streaming deltas so a fast model can't force a render per token, while preserving event ordering?

## Connected graph-selected seam
**Path/Symbol:** `src/utils/streaming-delta-batcher.ts:createStreamingDeltaBatcher` (36–75).
**Signature:** `function createStreamingDeltaBatcher(commit: (event: StreamingDeltaEvent) => void, scheduler?: DeltaFlushScheduler): { enqueue(event): void; flush(): void; reset(): void }`.
**Data Shape:** Injected `{schedule(cb)=>handle, cancel(handle)}`; default uses `requestAnimationFrame`, falling back to `setTimeout(…,16)` outside the browser. Buffered deltas merge left-to-right via `mergeStreamingDeltaEvent` (string-concat of `content` and `reasoning_content`, independently, `null`-preserving).

### Decisive source
```ts
const flush = () => {
  cancelFrame();
  if (pending.length === 0) return;
  const batch = pending;
  pending = [];
  commit(batch.reduce((merged, delta) => mergeStreamingDeltaEvent(delta, merged)));
};
return {
  enqueue: (event) => {
    pending.push(event);
    if (frame === null) frame = scheduler.schedule(flush); // ONE frame, not one per delta
  },
  flush,
  reset: () => { cancelFrame(); pending = []; },
};
```
Call-site ordering rule (conversation-websocket-context.tsx):
```ts
if (isStreamingDeltaEvent(event)) { mainDeltaBatcherRef.current?.enqueue(event); return; }
// Flush buffered deltas before this event so it can't overtake them.
mainDeltaBatcherRef.current?.flush();
```

**Flow:** enqueue appends and schedules a single frame if none pending → frame fires → all buffered deltas reduce into ONE merged event (first delta's identity survives) → `commit` writes to the store once → handler of any non-delta event calls `flush()` first so a message/action can never render ahead of its streamed prefix → `reset()` drops buffers silently on unmount/conversation switch (a flush there would leak text into the next conversation).

**Invariant:** Text is byte-for-byte preserved across arbitrary chunk boundaries (concatenation is associative); commits per unit time are bounded by frames, not chunks; a durable event is never committed while deltas that precede it are still buffered.

**Probe:** `__tests__/utils/streaming-delta-batcher.test.ts` — manualScheduler asserts: three enqueues schedule exactly ONE frame; content/reasoning merge independently in order; `flush()` cancels the pending frame (tick must not double-commit); `reset()` commits nothing; and a 5000×1-char flood faster than 60Hz reproduces the stream exactly with commits ≤ frames+1. RUNNER BLOCK: vitest not executable here; decisive ranges read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "createStreamingDeltaBatcher coalesce animation frame flush", limit: 6 });
// executed this pass -> createStreamingDeltaBatcher src/utils/streaming-delta-batcher.ts 36-75,
// flush 50-60, cancelFrame 43-48 (has_more: true)
```

## Verdict
Adopt the injectable-scheduler coalescer, the flush-before-non-delta ordering rule, and silent reset on scope change. Adapt merge fields to your delta shape. Omit the OpenHands event-store fold (see `event-store-dedup-projection`). Coverage: `no_recorded_issue` on source and test paths.
