<!-- capsule-v2 -->
# Modern-era 400 in-band delivery — how are HTTP validation-ladder rejections surfaced as protocol errors without breaking legacy error matching?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** When an inbound validation ladder rejects a request with HTTP 400 + JSON-RPC error body, where does that error surface on the client, and what gates keep old callers working?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/streamableHttp.ts`: gate in `_send` (:1088-1099); predicate `_isModernEnvelopedRequest` (:513-518).
**Signature:** `private _isModernEnvelopedRequest(message): boolean` — single JSON-RPC request whose `params._meta[PROTOCOL_VERSION_META_KEY]` is a modern protocol version string.
**Data Shape:** 400 body = one JSON-RPC error response (`{jsonrpc, id, error}`) whose id matches an outstanding request of THIS exchange.

### Decisive source
```ts
// :1088-1095 — modern-era only, id-matched, delivered in-band via onmessage
if (response.status === 400 && typeof text === 'string' && this._isModernEnvelopedRequest(message)) {
    try {
        const parsed = JSONRPCMessageSchema.parse(JSON.parse(text));
        const requests = (Array.isArray(message) ? message : [message]).filter(m => isJSONRPCRequest(m));
        if (isJSONRPCErrorResponse(parsed) && requests.some(r => r.id === parsed.id)) {
            this.onmessage?.(parsed); // Protocol._onresponse turns it into a typed ProtocolError
            return;
        }
    } catch { /* fall through to generic SdkHttpError */ }
}
throw new SdkHttpError(SdkErrorCode.ClientHttpNotImplemented, `Error POSTing to endpoint: ${text}`, {...});
```

**Flow:** server validation ladders (SEP-2243 header checks etc.) reject modern-era requests with
400 + JSON-RPC error body → client parses the body, matches the error id against THIS send's
request ids → delivers via onmessage so Protocol correlation converts it to a rejected promise
carrying the typed ProtocolError → any mismatch (unparseable body, foreign id, legacy-era message)
falls through to the generic SdkHttpError with status 400.

**Invariant:** era-gating keeps the changeset claim "legacy-era paths are unchanged" true — a
legacy exchange still surfaces 400 as SdkHttpError, so existing
`e instanceof SdkHttpError && e.status === 400` handling never silently stops matching. The gate
is the SAME predicate that emits body-derived headers, keeping classification single-sourced.

**Probe:** `packages/client/test/client/mcpParamMirroring.test.ts` :491-509 (modern-enveloped
tools/call resolves with onmessage carrying HEADER_MISMATCH error code for id 1; a following
legacy-shape call rejects with \`{status: 400}\`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "typescript-sdk", query: "isModernEnvelopedRequest PROTOCOL_VERSION_META_KEY in-band 400", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt era-gated in-band delivery with strict id matching; adapt the error taxonomy names to your
SDK; omit the legacy branch only when no legacy clients exist. Direct-test evidence at :491-509;
coverage no_recorded_issue at the pin.
