<!-- capsule-v2 -->
# Legacy SSE client connect bracket — how does a deprecated half-duplex client transport bracket connect/auth so retries neither recurse nor trust cross-origin endpoints?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** Where does start() actually resolve, how does the 401 restart ladder avoid infinite recursion, and why is the endpoint event origin-checked?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/sse.ts`: `_startOrAuth` (:187-281), `SseError` (:28-63), `close` (:340-344), `_send` (:350-413).
**Signature:** `private _startOrAuth(): Promise<void>`; `new EventSource(url.href, { ...eventSourceInit, fetch: wrapped })`
**Data Shape:** server announces POST endpoint via SSE \`event: endpoint\` data URL; auth state captured from the 401 response headers into \`_last401Response\`, \`_resourceMetadataUrl\`, \`_scope\`.

### Decisive source
```ts
// :249-266 — resolve ONLY on endpoint event, AFTER same-origin check
this._eventSource.addEventListener('endpoint', (event: Event) => {
    try {
        this._endpoint = new URL(messageEvent.data, this._url);
        if (this._endpoint.origin !== this._url.origin) {
            throw new Error(\`Endpoint origin does not match connection origin: ${this._endpoint.origin}\`);
        }
    } catch (error) {
        reject(error); this.onerror?.(error as Error); void this.close(); return;
    }
    resolve();
});
// :214-238 — 401 restart: close ES first, single retry via isAuthRetry-free fresh bracket
if (event.code === 401 && this._authProvider && this._authProvider.onUnauthorized && this._last401Response) {
    const response = this._last401Response; this._last401Response = undefined;
    this._eventSource?.close();
    this._authProvider.onUnauthorized({ response, ... }).then(
        () => this._startOrAuth().then(resolve, reject),          // one fresh attempt
        error => { markAuthSeamEscape(error); this.onerror?.(error); reject(error); });
    return;
}
```

**Flow:** start() builds an EventSource whose fetch wrapper merges bearer headers and captures
the 401 (status + WWW-Authenticate params) before returning the response → onopen resolves
nothing; the 'endpoint' event names the POST target, which must be same-origin → afterwards
onmessage parses JSON-RPC frames. POST _send mirrors the modern transport's 401 ladder
(onUnauthorized once, then SdkHttpError 'Server returned 401 after re-authentication') minus
step-up. close() aborts the controller then closes the ES, firing onclose unconditionally.

**Invariant:** the connect promise settles exactly once — via endpoint-origin-checked resolve,
via the single 401 restart chain, or via typed rejection (UnauthorizedError / branded SseError
carrying the ErrorEvent). Capturing the 401 response in the fetch wrapper (not the onerror) is
what lets onUnauthorized receive real headers while EventSource keeps its own lifecycle.

**Probe:** `packages/client/test/client/sse.test.ts` :507-553 (auth flow on 401 during SSE
connect / during POST), :1586-1600 (no onUnauthorized → UnauthorizedError; circuit breaker on
double-401 throws SdkHttpError after one call), :1649+ (connect 401 retry does not poison future
401s). Caveat recorded honestly: the same-origin endpoint check (:253-256) is source-visible but
has no direct test in sse.test.ts — port it from source, pin it yourself.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "typescript-sdk", query: "SSEClientTransport _startOrAuth endpoint origin _last401Response", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt endpoint-event resolution with same-origin enforcement and the capture-response-then-restart
401 ladder; adapt EventSource to your platform's SSE client; omit step-up here only because the
deprecated transport never had it — do not add it silently. Coverage no_recorded_issue at the pin.
