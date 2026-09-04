<!-- capsule-v2 -->
# Legacy SSE transport — how does the deprecated SSE+POST transport bracket its lifecycle, and which close path must not double-fire onclose?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When porting an SSE server transport (or any half-duplex stream transport), what are the start/post/close invariants a reimplementation gets wrong?

## Lifecycle bracket & header validation
**Path/Symbol:** `packages/server-legacy/src/sse/sse.ts`: class `SSEServerTransport` (:39-195), `validateRequestHeaders` (:56-76), `start()` (:78-102), `handlePostMessage` (:104-164), `close()` (:178-182), `send()` (:184-190).
**Signature:** `new SSEServerTransport(endpoint: string, res: ServerResponse, options?: { allowedHosts?, allowedOrigins?, enableDnsRebindingProtection? })`; `sessionId = randomUUID()`.
**Data Shape:** wire frames `event: endpoint\ndata: <path>?sessionId=…\n\n` then `event: message\ndata: <JSON-RPC>\n\n`; POSTs answer 202 'Accepted' / 400 / 403 / 500; `MAXIMUM_MESSAGE_SIZE = '4mb'`.

### Decisive source
```ts
// :98-101 vs :178-182 — two onclose paths, one guard each
this.res.on('close', () => {
    this._sseResponse = undefined;
    this.onclose?.();
});
// ...
async close(): Promise<void> {
    this._sseResponse?.end();
    this._sseResponse = undefined;
    this.onclose?.();
}
```
```ts
// :56-59 DNS-rebinding protection is OPT-IN and host-list-driven
if (!this._options.enableDnsRebindingProtection) return undefined;
if (this._options.allowedHosts && this._options.allowedHosts.length > 0) {
    const hostHeader = req.headers.host;
    if (!hostHeader || !this._options.allowedHosts.includes(hostHeader)) return `Invalid Host header: ${hostHeader}`;
```

**Flow:** `start()` writes SSE headers + the endpoint event (session id appended via URL API against a dummy base so relative endpoints, query params, and hashes all compose — sse.test.ts :57-137 pins five shapes), latches `_sseResponse`, registers the close listener; double-start throws. `handlePostMessage`: not-started ⇒ 500 AND throw; opt-in rebinding checks (host allowlist deny-on-missing, origin checked only when present) ⇒ 403; content-type must parse as application/json (charset honored via raw-body) else 400; schema-invalid messages 400; accepted messages 202. `send()` throws 'Not connected' when torn down.

**Invariant:** every teardown path clears `_sseResponse` BEFORE invoking `onclose` — a porter who leaves the field set after client disconnect makes a later `close()` call `.end()` a dead response and fire `onclose` TWICE (double protocol shutdown). Header protection here is the DEPRECATED in-class form: modern code moves it to framework middleware (the JSDoc says exactly that); adopt the middleware route for anything new.

**Probe (direct tests):** `packages/server-legacy/test/sse/sse.test.ts` — :139 'should throw if started twice', :149 'should return 500 if server has not started', :161/:176 content-type/schema 400s, :237 'should call onclose' (close method), DNS block :283-446 (host/origin/both/disabled matrices).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "SSEServerTransport handlePostMessage sessionId endpoint", limit: 3 });
```

## Verdict
Adopt the clear-before-callback teardown ordering and opt-in rebinding posture; adapt frame formatting to your streaming primitives; omit this transport entirely for new work — Streamable HTTP superseded it (see `transports` capsule).
