<!-- capsule-v2 -->
# Async-iterable stream duality — how does one object serve both ReadableStream consumers and for-await loops with correct teardown on every exit path?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What cleanup must run when a for-await loop breaks, throws, completes, or re-enters — and why does the wrapper come in two variants?

## createAsyncIterableStream / asAsyncIterableStream
**Path/Symbol:** `packages/ai/src/util/async-iterable-stream.ts:15-20` (`createAsyncIterableStream`), `:39-123` (`asAsyncIterableStream`).
**Signature:** `createAsyncIterableStream<T>(source: ReadableStream<T>): AsyncIterableStream<T>` (fresh pipe); `asAsyncIterableStream<T>(stream: ReadableStream<T>): AsyncIterableStream<T>` (in-place augmentation, fresh+unlocked streams only).
**Data Shape:** `AsyncIterableStream<T> = AsyncIterable<T> & ReadableStream<T>` — UI-message streams, agent UI streams, and result streams all expose this type.

### Decisive source
```ts
// iterator state: one reader + one finished latch
let finished = false;
async function cleanup(cancelStream: boolean) {
  if (finished) return;                 // idempotent: return() after completion is a no-op
  finished = true;
  try {
    if (cancelStream) await reader.cancel?.();
  } finally {
    try { reader.releaseLock(); } catch {}
  }
}
return {
  async next() {
    if (finished) return { done: true, value: undefined };   // no second iteration after break
    let result: ReadableStreamReadResult<T>;
    try {
      result = await reader.read();
    } catch (error) {
      await cleanup(false);            // read error: release lock but DON'T cancel — error is the stream's own
      throw error;
    }
    const { done, value } = result;
    if (done) { await cleanup(true); return { done: true, value: undefined }; }
    return { done: false, value };
  },
  async return() { await cleanup(true);  return { done: true, value: undefined }; }, // break
  async throw(err) { await cleanup(true); throw err; },                              // throw into loop
};
// and the two constructors:
export function createAsyncIterableStream(source) {
  // Pipe through a TransformStream to ensure a fresh, unlocked stream.
  return asAsyncIterableStream(source.pipeThrough(new TransformStream<T, T>()));
}
```

**Flow:** The in-place variant exists because of a documented production bug (source comment): piping an ALREADY-piped upstream through an extra transform surfaces a spurious unhandled `undefined` rejection on early consumer cancel under Node.js 26 — so `asAsyncIterableStream` is for known-fresh streams, `createAsyncIterableStream` adds the freshness transform for possibly-shared/locked inputs. Terminal states: `break` ⇒ `return()` ⇒ cancel+release; thrown body ⇒ `throw()` ⇒ cancel+release+rethrow; natural end ⇒ `next()` gets `done` ⇒ cancel+release; read error ⇒ release only, error propagates to ALL concurrent readers via the shared promise.

**Invariant:** Exactly-once cleanup guarded by the `finished` latch; post-break iteration yields `done` forever (test-pinned "should not allow iterating twice after breaking"); early-exit MUST reach the source's `cancel(reason)` or producers (model HTTP bodies!) leak. Error path distinction matters: cancelling on a failed stream would mask the original error.

**Probe:** `packages/ai/src/util/async-iterable-stream.test.ts:52` ("should cancel stream on early exit from for-await loop" — asserts source `cancel()` ran), `:88` (cancel on exception inside loop), `:152` ("should not allow iterating twice after breaking"), `:243` ("should not throw when return is called after the stream completed"), `:277/:314/:338` (error propagation + single release).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createAsyncIterableStream Symbol.asyncIterator releaseLock", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt both variants plus the latch-based cleanup; keep the two-constructor split with its runtime-version rationale. Adapt only if your host has no TransformStream (then document why the freshness guarantee changed).
