<!-- capsule-v2 -->
# Stream start buffering + speculative auth retry — how do you retry an auth-failed stream before any real event leaks into session history?

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** The SDK emits a synthetic `start` event before the HTTP request is even sent — a 401 then leaves a phantom empty assistant bubble unless the retry boundary sits ahead of that event.

## Start-buffered stream wrapper with one-shot auth recovery
**Path/Symbol:** `src/stream.ts:227-472` (`streamSimpleKimi` retry loop); credential ladder `resolveKimiApiKey` 207-212 + `getStoredKimiAccessToken` 203-205; header merge `mergeKimiRequestHeaders` 220-225; per-attempt options closure `buildPatchedOptions` 281-325.
**Signature:** `(model: Model<Api>, context: Context, options?: SimpleStreamOptions) => AssistantMessageEventStream`; internal `while (true)` loop with `attempt`, `currentKey`, `prefixBuffer`.
**Data Shape:** returns a NEW filtered event stream; upstream events are re-pushed into it only after proof-of-life; retry replaces the key and rebuilds patched options.

### Decisive source
```ts
// streamAnthropic emits a synthetic "start" event synchronously,
// before the for-await loop begins iterating and therefore before
// the HTTP request is actually made.  If the request 401s, the loop
// throws and the catch block emits "error".  Without buffering, the
// "start" event (which carries an empty AssistantMessage) leaks into
// the session history and the TUI, leaving a phantom empty assistant
// bubble.  We buffer "start" events and only flush them once we see
// a non-error event that proves the stream is alive.
if (event.type === "start") {
  prefixBuffer.push(event);
  continue;
}
if (
  attempt === 0 &&
  event.type === "error" &&
  isKimiAuthErrorMessage(event.error?.errorMessage)
) {
  ...
  const refreshed = await refreshKimiAuthToken(currentKey);
  if (refreshed && refreshed !== currentKey) {
    currentKey = refreshed;
    shouldRetry = true;
    break; // discard prefixBuffer — don't leak the stale start
  }
}
```
```ts
function resolveKimiApiKey(apiKey: string | undefined): string {
  if (apiKey !== undefined && KIMI_API_KEY_ENV_REFERENCES.has(apiKey)) {
    return process.env.KIMI_API_KEY?.trim() || getStoredKimiAccessToken();
  }
  return apiKey || process.env.KIMI_API_KEY || getStoredKimiAccessToken();
}
```

**Flow:** resolve initial key (literal `$KIMI_API_KEY`/`${KIMI_API_KEY}` passthrough → env → stored OAuth credential) → build patched options per attempt: merged headers (caller values win; `null` entries RETAINED so pi-ai strips suppressed headers itself), uploader bound to the current key, onPayload chain applying Kimi mutations then rewriting `model:"kimi-for-coding"` to the discovered wire id, original caller onPayload still consulted last → iterate filtered upstream: buffer `start`s; first auth-flavored error on attempt 0 ⇒ refresh once, retry with new key and DISCARD the buffer; any other first real event ⇒ flush buffered starts then forward; catch path mirrors the same single-refresh ladder when the SDK throws instead of emitting an error event, else forwards a fully-populated zero-usage error message.
**Invariant:** At most ONE refresh+retry per stream call, gated on attempt===0 AND the refreshed token differing; buffered starts are flushed only after a non-error event proves the stream is alive, and are discarded on retry so stale-session phantom messages can never enter history; the caller's explicit apiKey is never overridden with an empty string.

**Probe:** `tests/payload.test.ts:987-1050` (`streamSimpleKimi` model-capability selection at request time) and `tests/oauth-kimi-lock.test.ts` for the refresh side; header precedence pinned at `tests/payload.test.ts:971-986` ("adds Kimi identity headers while preserving caller overrides").
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "streamSimpleKimi prefixBuffer refreshKimiAuthToken", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the ordering contract: credential resolution ladder → per-attempt option closure → start-event proof-of-life buffering → single difference-gated refresh retry covering both error-event and thrown paths. Adapt the auth-error classifier, env-reference syntax, and wire-id rewrite trigger. Omit pi-ai-specific compat flags (forceAdaptiveThinking/allowEmptySignature) unless your host keys protocol quirks off model metadata the same way. Coverage caveat: the thrown-error retry branch (stream.ts:420-436) has no dedicated test file; its in-stream sibling is pinned, and the branch mirrors it — treat as reviewed-but-unpinned at this pin.
