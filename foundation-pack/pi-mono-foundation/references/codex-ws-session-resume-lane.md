<!-- capsule-v2 -->
# codex-ws-session-resume-lane — How do I bridge a WebSocket Responses transport into the shared stream kernel with connection reuse and delta continuations?

**Source:** pi-mono (MIT) `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** How does the Codex adapter select between WS and SSE, survive transport failures without corrupting a half-streamed turn, and resume conversations over one connection?

## Dual-transport FSM + connection cache
**Path/Symbol:** `packages/ai/src/api/openai-codex-responses.ts` (1650L) — `stream` :230-490, `streamSimple` :492-513; cache plane `connectWebSocket` :1038-1114, `acquireWebSocket` :1116-1211, expiry reaper :1024-1036, delta continuation `getCachedWebSocketInputDelta` :1401-1421 / `buildCachedWebSocketRequestBody` :1423-1440, event generator `parseWebSocket` :1270-1386, `startWebSocketOutputOnFirstEvent` :1442-1454, `processWebSocketStream` :1456-1543.
**Signature:** `async function acquireWebSocket(url, headers, sessionId?: string, accountId: string, signal?, connectTimeoutMs?, env?): Promise<{ socket; entry?; reused: boolean; release: (options?: { keep?: boolean }) => void }>`; `async function processWebSocketStream(url, body, headers, output, stream, model, onStart, idleTimeoutMs?, websocketConnectTimeoutMs?, cacheSessionId?, accountId, grammarToolInputProperties, options?): Promise<void>`.
**Data Shape:** cache `Map<sessionId, Map<accountId, {socket, busy, createdAt, idleTimer?, continuation?: {lastRequestBody, lastResponseId, lastResponseItems}}>>`; consts: connect timeout 15s default, TTL reaper closes code 1000 `"idle_timeout"`, age-limit close `"connection_age_limit"`, close 1009 = message too big.

### Decisive source
```ts
// stream(): sticky per-session fallback + bounded one-shot retries
const websocketDisabledForSession = transport !== "sse" && isWebSocketSseFallbackActive(cacheSessionId);
...
} catch (error) {
    const aborted = options?.signal?.aborted;
    const connectionLimitBeforeStart = !websocketStarted && isWebSocketConnectionLimitReachedError(error);
    const previousResponseNotFound = isPreviousResponseNotFoundError(error);
    if (!aborted && previousResponseNotFound && !retriedMissingWebSocketContinuation) { retriedMissingWebSocketContinuation = true; continue; }
    if (!aborted && connectionLimitBeforeStart && !retriedWebSocketConnectionLimit) { retriedWebSocketConnectionLimit = true; continue; }
    if (aborted || (isCodexNonTransportError(error) && !connectionLimitBeforeStart)) throw error;
    appendAssistantMessageDiagnostic(output, createAssistantMessageDiagnostic("provider_transport_failure", error, {...}));
    recordWebSocketFailure(cacheSessionId, error);
    if (websocketStarted) throw error;      // never downgrade mid-stream
    recordWebSocketSseFallback(cacheSessionId); break;  // sticky → SSE for this session
}
```

**Flow:** `transport: "auto"` tries WS first unless the session already fell back. WS attempt: acquire socket (cached per session+account when not busy; a BUSY cached entry never queues — a fresh parallel socket opens; expired-age idle entries close with `connection_age_limit`) → send `{type:"response.create", ...body}` where body may be a DELTA (`previous_response_id` + suffix input) only when `requestBodiesMatchExceptInput` (JSON-equal ignoring input/previous_response_id) AND current input strictly extends baseline `[lastInput ++ lastResponseItems]` by exact prefix — otherwise continuation drops and full context sends. Events flow `parseWebSocket` (queue+single-waiter async generator; done latch on `response.completed|done|incomplete`; close-after-completion clean vs before-completion failure; invalid JSON → CodexProtocolError carrying payload; optional idle watchdog) → `mapCodexEvents` → the SAME shared `processResponsesStream` slot machine SSE uses, wrapped so `start` emits on first real event via one `startEmitted` latch shared across transports. Success stores next continuation from the assistant's own items (minus `*_tool_call_output`) + `responseId`; any error clears continuation and closes. Release({keep:false}) or unusable socket ⇒ silent close + identity-checked map prune; keep ⇒ busy=false + TTL reschedule. Backend rejects `store:true`, so resume state lives in the CONNECTION, not the server store.
**Invariant:** A turn that already emitted events must fail loudly rather than silently restart on another transport (no duplicated/partial replay); at most ONE retry each for missing-continuation and pre-start connection-limit; the SSE fallback latch is per cacheSessionId and permanent for that session. SSE path zstd-compresses the request body once (`process.getBuiltinModule("node:zlib")`, level 3, null-safe fallback to plain JSON) while WS always sends uncompressed frames; its own retry loop defaults maxRetries 0, refuses terminal rate limits even on 429 (usage/quota/billing regex), validates server retry-after against maxRetryDelayMs by throwing, and sleeps abort-aware.
**Probe:** No unit runner exists — `packages/ai/test/codex-websocket-cached-probe.ts` is a credential-gated live probe (main() drives real ChatGPT backend). Assertions pinned by whole-file direct reads of :256-515, :1038-1211, :1270-1440, :1456-1543 at pin. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", query: "codex websocket connection reuse idle expiry delta input continuation response items", limit: 10, fields: ["signature", "name", "file"] });
```
Live result at pin: `getCachedWebSocketInputDelta` #1 (-26.76) followed by the codex-websocket-cached-probe cluster. Adversarial RED observed: generic vocabulary "websocket acquire cache session continuation previous_response_id release keep" retrieves ZERO openai-codex-responses symbols in its top 10 — retrieval requires this capsule's vocabulary.

## Verdict
Adopt the transport-selection FSM (sticky fallback, bounded one-shot retries, no mid-stream downgrade), the busy-bypasses-cache connection pool with TTL/age reapers and identity-checked pruning, and exact-prefix delta continuation guarded by request-equality checks. Adapt the continuation baseline to your wire (pi reuses its own converter to rebuild assistant items). Omit zstd compression if your endpoint rejects Content-Encoding; keep the uncompressed-frame-on-WS asymmetry only if your backend matches Codex's contract.
