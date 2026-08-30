<!-- capsule-v2 -->
# Terminal-error latch in streamObject — what happens when an error chunk and a later finish chunk disagree?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551e...`; Codebase Memory `ai`. **Question:** After a stream errors mid-flight, why must the finish reason be forced to `error` and the result promises rejected, even though the provider also sent a terminal frame?

## First-error-wins latch + eager rejection
**Path/Symbol:** `packages/ai/src/generate-object/stream-object.ts` — latch `terminalError` (:668), error-chunk case (:765–773), finish-reason override (:783–785, :803–805), `addStream` onError (:903), `rejectResultPromises` (:931–939), `markPromiseAsHandled` (:71).
**Signature:** `rejectResultPromises(error: unknown): void` — rejects object/usage/providerMetadata/warnings/request/response/finishReason delayed promises; `markPromiseAsHandled(promise)` awaits with empty catch.
**Data Shape:** `terminalError: { error: unknown } | undefined` — undefined means stream still healthy.

### Decisive source
```ts
case 'error': {
  if (terminalError === undefined) {
    const wrappedError = wrapGatewayError(chunk.error);
    terminalError = { error: wrappedError };
    self.rejectResultPromises(wrappedError);   // reject ALL promises NOW
  }
  controller.enqueue(chunk);                   // part still forwarded
  break;
}
// at finish:
finishReason = terminalError === undefined ? chunk.finishReason.unified : 'error';
if (terminalError !== undefined) break;        // no success completion after error
```

**Flow:** first error chunk latches the wrapped error and rejects every lazy result promise immediately (un-awaited consumers can never hang); subsequent error chunks are deduped (latch) but still forwarded; when the provider's finish frame arrives anyway it is overridden to `'error'` and the success path is skipped.
**Invariant:** An errored stream can never report a successful finishReason or leave any result promise pending — the latch makes the FIRST error authoritative. `markPromiseAsHandled` wraps rejections in the drain paths so intentionally-unobserved promises don't become unhandled rejections.
**Probe:** deterministic probes: `grep -c markPromiseAsHandled packages/ai/src/generate-object/stream-object.ts` → `2`; `grep -c "this.rejectResultPromise({ delayedPromise:" …ts` → `7` (the seven result properties). Direct tests: `stream-object.test.ts` regression suite from #18934/#19187 ("settle streamObject results", callback-throw cases).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "rejectResultPromises stream-object", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 DefaultStreamObjectResult.rejectResultPromises :931-939
```

## Verdict
Adopt first-error-latch + eager all-promise rejection + finish-reason override as one inseparable behavior; adapt which properties count as "result promises" to your result shape; omit nothing — dropping any leg leaves either hung consumers or false success. Companion: `stream-continuation-engine.md` owns generateText-side continuation.
