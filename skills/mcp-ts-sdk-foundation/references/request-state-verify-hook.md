<!-- capsule-v2 -->
# requestState.verify hook — where does integrity verification of attacker-controlled round-trip state attach, and what may the hook resolve?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How do you plug HMAC/AEAD verification into request handling without letting a malformed state bypass it or a wrong return value poison the handler's view?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/server.ts`: `ServerOptions.requestState.verify` docblock (:153-192), non-string gate (:607-612), `_verifyRequestState` (:705-719), `withRequestStateValue` ctx rewrite (:613-619).
**Signature:** `verify?: (state: string, ctx: ServerContext) => unknown | Promise<unknown>` — resolved value is LOAD-BEARING.
**Data Shape:** Wire field `requestState: string | undefined`; hook resolves the decoded payload or `undefined`.

### Decisive source
```ts
const rawRequestState: unknown = ctx.mcpReq.requestState();
if (rawRequestState !== undefined && typeof rawRequestState !== 'string') {
    // A malformed value cannot bypass verification regardless of hook configuration:
    throw new ProtocolError(ProtocolErrorCode.InvalidParams,
        'Invalid or expired requestState', { reason: 'invalid_request_state' });
}
let ctxForHandler = ctx;
if (typeof rawRequestState === 'string') {
    const decoded = await this._verifyRequestState(rawRequestState, ctx, method);
    if (decoded !== undefined) {
        ctxForHandler = withRequestStateValue(ctx, decoded);   // handler reads VERIFIED state via ctx.mcpReq.requestState<T>()
    }
}
// _verifyRequestState catch arm:
this.onerror?.(new Error(`requestState verification rejected ${method}: ...`));  // reason → onerror ONLY
throw new ProtocolError(ProtocolErrorCode.InvalidParams, 'Invalid or expired requestState',
    { reason: 'invalid_request_state' });                       // wire message FROZEN
```

**Flow:** type gate (runs even when NO hook is configured) → hook (if configured) → on throw: reason surfaces via `onerror` only, wire answers the frozen `-32602` with `data.reason:'invalid_request_state'` → on success with non-undefined value: ctx is rewritten so the typed accessor returns the verified payload (no second decode); resolving `undefined` keeps the raw wire string.

**Invariant:** The SDK provides NO default verification — unconfigured means passthrough of attacker-controlled input. The frozen message exists so attackers cannot distinguish failure reasons; never interpolate expected/actual values onto the wire. A verifier that is not also the decoder MUST resolve `undefined` — an incidental truthy return (e.g. a boolean flag) silently replaces what handlers read.

**Probe:** `packages/server/test/server/inputRequired.test.ts` :380 ("called with echoed state and ctx, before the handler"), :395 ("throw becomes frozen -32602, not isError; reason to onerror only"), :423 ("not called without requestState"), :436 ("resolved payload backs ctx.mcpReq.requestState<T>()"), :458 ("unconfigured ⇒ raw passthrough").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "withRequestStateValue requestState verify invalid_request_state", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt the hook placement + frozen-wire/verbose-onerror split + load-bearing-resolve contract; adapt reason codes; pair with the HMAC codec (`request-state-codec.md`) whose `verify` drops in directly.
