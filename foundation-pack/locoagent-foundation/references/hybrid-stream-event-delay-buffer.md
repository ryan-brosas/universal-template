<!-- capsule-v2 -->
# Hybrid stream_event delay buffer — how do you batch high-volume streaming deltas without reordering them against control messages?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Where do 100ms-buffered `stream_event` deltas sit relative to immediate writes, and what exactly happens to them on close()?

## Delay buffer with ordering-preserving flush points
**Path/Symbol:** `src/cli/transports/HybridTransport.ts`: `write` (:117-133), `takeStreamEvents`/:155-163, `close`/:171-195; constants :12-22.
**Signature:** `override async write(message: StdoutMessage): Promise<void>` — resolves IMMEDIATELY for stream_event (callers don't await deltas), awaits enqueue+flush for everything else.
**Data Shape:** `streamEventBuffer: StdoutMessage[]` + single timer; BATCH_FLUSH_INTERVAL_MS=100; CLOSE_GRACE_MS=3000 race against uploader.flush().

### Decisive source
```ts
if (message.type === 'stream_event') {
  this.streamEventBuffer.push(message)
  if (!this.streamEventTimer) {
    this.streamEventTimer = setTimeout(() => this.flushStreamEvents(), BATCH_FLUSH_INTERVAL_MS)
  }
  return
}
// Immediate: flush any buffered stream_events (ordering), then this event.
await this.uploader.enqueue([...this.takeStreamEvents(), message])
return this.uploader.flush()
```
```ts
// close(): sync return; buffered-but-unenqueued deltas are DROPPED;
// already-enqueued batches get a bounded grace drain.
this.streamEventTimer && clearTimeout(this.streamEventTimer); this.streamEventBuffer = []
void Promise.race([uploader.flush(), new Promise<void>(r => { graceTimer = setTimeout(r, CLOSE_GRACE_MS) })])
  .finally(() => { clearTimeout(graceTimer); uploader.close() })
super.close()
```

**Flow:** stream_event → buffer (+arm timer once); any non-stream write or writeBatch or explicit flush() first TAKES the buffer (clearing the timer) and enqueues it AHEAD of itself → per-message ordering preserved; timer fire enqueues buffer alone.
**Invariant:** Ordering: buffered events always enqueue before the triggering immediate event. Backpressure note: bridge callers use `void transport.write()`, so maxQueueSize here is a memory bound (100_000), not real backpressure — awaiting callers are the documented follow-up. close() drops undelivered 100ms-window deltas by design (archive-before-close upstream is the primary drain window; the 3s race is a last resort).
**Probe:** `grep -n "BATCH_FLUSH_INTERVAL_MS = 100" src/cli/transports/HybridTransport.ts` (`:12`), `grep -n "takeStreamEvents(), message" src/cli/transports/HybridTransport.ts` (`:131`), `grep -n "CLOSE_GRACE_MS = 3000" src/cli/transports/HybridTransport.ts` (`:22`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "HybridTransport stream_event delay buffer flushStreamEvents", limit: 5 });
```

## Verdict
Adopt take-before-enqueue ordering and the sync-close-with-grace-drain shape. Adapt the 100ms window to your delta volume. Omit the drop-on-close only if your callers await every write.
