<!-- capsule-v2 -->
# Client POST exchange ladder — what is the full header-authority + session-adoption + response-branch contract a Streamable HTTP client transport must implement?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** When porting a client-side streamable HTTP transport, who owns each request header, when may a response mutate connection state, and how are response shapes branched?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/streamableHttp.ts`: `_send` (:934-1175), `RESERVED_REQUEST_HEADER_NAMES` (:260-267), `_applyBodyDerivedHeaders` (:472-505), `_commonHeaders` (:435-462).
**Signature:** `private async _send(message: JSONRPCMessage | JSONRPCMessage[], options, isAuthRetry: boolean, stepUpRetries = 0): Promise<void>`
**Data Shape:** headers assembled as `Headers`; session id from response header `mcp-session-id`; per-request extras arrive via `options.headers` (the SEP-2243 `Mcp-Param-*` carrier).

### Decisive source
```ts
// :967-971 + :979-983 — handshake sheds identity; callers cannot overwrite owned headers
if (isHandshake) { headers.delete('mcp-session-id'); }
for (const [name, value] of Object.entries(options.headers)) {
    if (RESERVED_REQUEST_HEADER_NAMES.has(name.toLowerCase())) continue; // veto
    headers.set(name, value);
}
// :1011-1013 — session adoption ONLY on ok handshake; empty response clears stale id
if (isHandshake && response.ok) {
    this._sessionId = response.headers.get('mcp-session-id') || undefined;
}
```
```ts
// :1125-1158 — branch on PARSED media type essence, not substring matching
const responseMediaType = mediaTypeEssence(contentType);
if (hasRequests) {
    if (responseMediaType === 'text/event-stream') this._handleSseStream(response.body, {...}, false);
    else if (responseMediaType === 'application/json') { /* parse array-or-single, onmessage each */ }
    else throw new SdkError(SdkErrorCode.ClientHttpUnexpectedContent, ...);
}
```

**Flow:** _commonHeaders (bearer token, mcp-session-id, mcp-protocol-version) → body-derived
mcp-protocol-version/mcp-method/mcp-name written only when the message's `_meta` carries a
protocol-version envelope claim (Mcp-Name mirrors params.name or resources/read uri through
encodeMcpParamValue sentinel encoding) → initialize deletes mcp-session-id → per-request headers
merged with reserved names skipped → POST. Response: ok-handshake adopts/clears session id;
401/403 ladders (see step-up-scope-union); 202 + notifications/initialized fires the standalone
GET SSE open; requests branch SSE vs JSON vs unexpected-content error; non-request messages
release the connection body.

**Invariant:** header/body disagreement is impossible from the caller side — reserved names
(authorization, content-type, mcp-protocol-version, mcp-method, mcp-name, mcp-session-id) are
derived from connection state or the body itself, so per-request overrides cannot desynchronize
what the server's cross-checks verify. A failed handshake must never poison the session slot.

**Probe:** `packages/client/test/client/streamableHttp.test.ts` :90-265 (adopt on ok init;
reject-without-adopt on 400 carrying a poisoned id; preset id cleared by sessionless handshake and
replaced by a returned one; non-initialize success ignores mcp-session-id). Header authority:
`packages/client/test/client/mcpParamMirroring.test.ts` :480-489 (Mcp-Method stays tools/call,
authorization override dropped, Mcp-Param-* passes) and :470-478 (non-ASCII Mcp-Name sentinel).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "typescript-sdk", query: "_applyBodyDerivedHeaders RESERVED_REQUEST_HEADER_NAMES", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the header-authority split and ok-handshake-only session adoption with clear-on-empty;
adapt the reserved-name set to your host's standard headers; omit the legacy-era fallbacks only if
you target a single protocol era. Coverage: all cited paths no_recorded_issue / metadata_match at
the pin (pass 8).
