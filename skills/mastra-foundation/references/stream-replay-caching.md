<!-- capsule-v2 -->
# stream replay cache — how do you add disconnect/reconnect chunk replay to a live workflow stream without switching to PubSub?

**Source:** mastra Apache-2.0 `main@3d2ff0d0a959792331f7cfb12dab6d08506676e7`; Codebase Memory `ext-mastra`. **Question:** How can a TransformStream transparently persist every chunk it forwards so a reconnecting client gets history-then-live with no gaps or duplicates?

## Cache-on-transform + history-first replay reader
**Path/Symbol:** `packages/core/src/stream/caching-transform-stream.ts` : `createCachingTransformStream` (:51-92), `createReplayStream` (:116-192), `withStreamCaching` (:217-252).
**Signature:**
```typescript
createCachingTransformStream<T>(opts: { cache: MastraServerCache; cacheKey: string; serialize?, deserialize? }): { transform, getHistory(offset?), clearCache };
createReplayStream<T>(opts: { history: T[]; liveSource: ReadableStream<T>; cache?, cacheKey?, serialize? }): ReadableStream<T>;
```
**Data Shape:** cache contract = `listPush(key, value)` (append) + `listFromTo(key, from[, to])` (Redis-LRANGE-inclusive slice) + `delete(key)`. Chunks cached AFTER `serialize` (default identity); replayed chunks pass through `deserialize`. `withStreamCaching` returns a factory so each `pipeThrough()` call mints a FRESH transform (a consumed TransformStream cannot be reused).

### Decisive source
```typescript
// createReplayStream.pull — the gap-free handoff:
async pull(controller) {
  if (!historyComplete) {
    if (historyIndex < history.length) {          // 1) drain cached history first,
      controller.enqueue(history[historyIndex]!); //    one chunk per pull
      historyIndex++;
      return;
    }
    historyComplete = true;
    liveReader = liveSource.getReader();           // 2) attach live ONLY after
  }                                                //    history is exhausted
  if (liveReader) {
    const { done, value } = await liveReader.read();
    if (done) return controller.close();
    if (cache && cacheKey) {
      const serialized = serialize(value);
      cache.listPush(cacheKey, serialized).catch(() => {});  // fire-and-forget
    }
    controller.enqueue(value);
  }
}
cancel(reason) {  // forward to whichever stage owns progress right now
  if (liveReader) return liveReader.cancel(reason);
  return liveSource.cancel(reason);
}
```

**Flow:** production path = `source.pipeThrough(transform)` caches every passing chunk (listPush failures swallowed — streaming must never die because caching did) → client disconnects → server keeps caching → on reconnect `getHistory(0)` → `createReplayStream({ history, liveSource: freshWorkflowStream })` emits all history then attaches live → continued caching re-arms for the next disconnect. The full loop is integration-tested as "Disconnect/Reconnect Scenario".
**Invariant:** History is emitted strictly before the live reader is created (`getReader()` only after `historyComplete`) so a chunk can never be delivered twice or skipped at the seam; cancel during history-only phase must still reach the live source (test :311). Cache writes are best-effort by design.
**Probe:** `packages/core/src/stream/__tests__/caching-transform-stream.test.ts`: `should emit history first then live chunks` (:176), `should handle empty history` (:206), `should forward cancellation to the live reader` (:268), `should cancel the live source during history replay` (:311), `should support full disconnect/reconnect workflow` (:444).
**Coverage caveat:** none — dedicated vitest suite covers both factories plus the reconnect scenario.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "createReplayStream createCachingTransformStream getHistory", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pull-based history-then-live ReadableStream and the cache-error-swallowing transform; adopt the Redis-LRANGE inclusive-index convention if your cache has one. Adapt `MastraServerCache` to any list-append store (the abstract base in `cache/base.ts` documents INCR-style atomic counters as the index generator for distributed setups). Omit nothing — this file is self-contained. Porters who create the live reader eagerly (before draining history) reintroduce the duplicate/lost-chunk race this structure exists to kill.
