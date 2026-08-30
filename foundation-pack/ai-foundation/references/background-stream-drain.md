<!-- capsule-v2 -->
# Background stream drain — how do you guarantee a result stream is consumed even when the user never awaits it, without surfacing duplicate errors?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** When a caller grabs `textStream` but ignores `fullStream`, what stops unhandled rejections and stalled promises?

## consumeStream
**Path/Symbol:** `packages/ai/src/util/consume-stream.ts:13-44` (`consumeStream`); wired into results at `packages/ai/src/generate-text/stream-text.ts:2508/:2608/:2616/:2624` (accessor-triggered auto-drain) and `:2690-2703` (public method).
**Signature:** `consumeStream({stream: ReadableStream, onError?: (error: unknown) => void, abortSignal?: AbortSignal}): Promise<void>`.
**Data Shape:** Consumes everything; returns nothing; resolves on natural end OR after reporting an error via callback; never rejects.

### Decisive source
```ts
const reader = stream.getReader();
const cancelOnAbort = () => {
  reader.cancel().catch(() => {});
};

if (abortSignal?.aborted) {
  cancelOnAbort();                                   // already-aborted ⇒ cancel immediately
} else {
  abortSignal?.addEventListener('abort', cancelOnAbort, { once: true });
}

try {
  while (true) {
    const { done } = await reader.read();
    if (done) break;
  }
} catch (error) {
  onError?.(error);                                  // error becomes data; promise still RESOLVES
} finally {
  abortSignal?.removeEventListener('abort', cancelOnAbort);
  reader.releaseLock();
}
```

**Flow:** The result object calls this automatically whenever ANY result property is first accessed (`get steps() { this.consumeStream(); ... }` — comment: "when any of the promises are accessed, the stream is consumed so it resolves without needing to consume the stream separately"). Errors route to `onError`, which in `DefaultStreamTextResult.consumeStream` also rejects all pending result promises (`rejectResultPromises`) — exactly-once rejection semantics: manual consumption reports through the same path, background drain prevents silent wedging.

**Invariant:** A stream with a consumer is a stream that finishes; every lazy accessor must trigger the drain idempotently. Read errors NEVER reject the returned promise — they are delivered at most once through `onError`. Abort mid-drain cancels the reader rather than leaving reads pending.

**Probe:** Direct suite absent for util (coverage caveat: behavior pinned indirectly by consumers — `packages/ai/src/generate-text/stream-text.test.ts` background-consumption cases and `lazy-result-primitives.md`'s rejection-safety pins). Deterministic check: source lines above show resolve-not-reject catch + once-listener cleanup.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "consumeStream rejectResultPromises", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the drain-with-error-callback shape and accessor-triggered auto-consumption. Adapt the abort wiring if your host streams aren't cancel-friendly. Omit nothing — it is 30 lines of load-bearing semantics.
