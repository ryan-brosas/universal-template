<!-- capsule-v2 -->
# SSE resume & reconnect kernel — when may an interrupted SSE stream reconnect, and what must never resurrect one?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** What is the complete predicate deciding reconnect vs stream-end vs silence, and how do server retry hints and custom schedulers fit without breaking cancellation?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/streamableHttp.ts`: `_handleSseStream` (:707-847), `_scheduleReconnection` (:666-705), `_getNextReconnectionDelay` (:645-658), `close` (:911-919).
**Signature:** `private _handleSseStream(stream: ReadableStream<Uint8Array> | null, options: StartSSEOptions, isReconnectable: boolean): void`
**Data Shape:** options carry resumptionToken, onresumptiontoken, replayMessageId, requestSignal, onRequestStreamEnd; parser events yield {id?, event?, data?}; server retry hint captured from SSE \`retry:\\` field into _serverRetryMs.

### Decisive source
```ts
// :789-807 — the three-gate resume decision after graceful close (same shape in the catch)
const canResume = isReconnectable || hasPrimingEvent;   // GET stream, or POST saw an event id
const needsReconnect = canResume && !receivedResponse;   // response (result OR error) ends it
if (needsReconnect && this._abortController && !isIntentionalAbort()) {
    this._scheduleReconnection({ resumptionToken: lastEventId, ... }, 0);
} else if (!isIntentionalAbort()) {
    onRequestStreamEnd?.();                              // terminal non-resumable outcome
}
// :686 — backoff must not resurrect a torn-down stream
if (this._abortController?.signal.aborted || options.requestSignal?.aborted) return;
// :647-657 — server retry hint fully replaces backoff; else capped exponential growth
if (this._serverRetryMs !== undefined) return this._serverRetryMs;
return Math.min(initialDelay * Math.pow(growFactor, attempt), maxDelay);
```

**Flow:** binary stream → TextDecoderStream → EventSourceParserStream(onRetry captures retry ms)
→ per event: record lastEventId + fire onresumptiontoken, skip empty data (priming/keep-alive),
parse message; result-or-error marks receivedResponse and remaps id to replayMessageId before
onmessage. Stream end or reader throw evaluates the gate: schedule reconnect at attempt 0 with
lastEventId, else fire onRequestStreamEnd. Deliberate aborts (transport close OR per-request
requestSignal) are silent: no onerror, no reconnect, no stream-end callback. Exhausted retries
fire onerror ONCE then onRequestStreamEnd.

**Invariant:** an intentional abort can never produce a resurrected stream — both the immediate
gate and the post-backoff callback re-check BOTH signals; close() cancels any pending
reconnection first (`finally { abort(); onclose(); }`). A POST-initiated stream without a priming
event is NOT resumable (nothing to replay from).

**Probe:** `packages/client/test/client/streamableHttp.test.ts` Reconnection Logic :1188-1900
(GET-fails reconnects; POST-fails does NOT; priming event enables POST reconnect; received
response suppresses; per-request abort silent; streamEnd callbacks on graceful end/exhaustion/
error; no resurrection after close), SSE retry field :2325-2465, scheduler :2604-2739 (receives
reconnect/delay/attemptCount; late-firing reconnect after close ignored).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "typescript-sdk", query: "_handleSseStream hasPrimingEvent receivedResponse isIntentionalAbort", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-gate resume predicate and dual-signal abort silence; adapt backoff constants and
scheduler to your platform; omit replayMessageId remapping only if you never resume mid-request
streams. Direct-test matrix cited above; coverage no_recorded_issue at the pin.
