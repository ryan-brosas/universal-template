<!-- capsule-v2 -->
# Per-request invoke seam — how do you serve one classified message through a REAL transport and get an HTTP Response back?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What is the minimal composition that reuses protocol dispatch unchanged while making a single exchange value-returning and testable?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/invoke.ts` whole file (:1-71): `InvokeContext` (:26-40), `invoke` (:56-71).
**Signature:** `invoke(server: Server | McpServer, message: JSONRPCRequest | JSONRPCNotification, ctx: InvokeContext): Promise<Response>`.
**Data Shape:** ctx = `{classification (computed ONCE at the entry boundary), request?, authInfo?, responseMode?='auto', keepAliveMs?}`.

### Decisive source
```ts
export async function invoke(server, message, ctx): Promise<Response> {
    const transport = new PerRequestHTTPServerTransport({
        classification: ctx.classification,
        ...(ctx.responseMode !== undefined && { responseMode: ctx.responseMode }),
        ...(ctx.keepAliveMs !== undefined && { keepAliveMs: ctx.keepAliveMs })
    });
    await server.connect(transport);
    return transport.handleMessage(message, {
        ...(ctx.request !== undefined && { request: ctx.request }),
        ...(ctx.authInfo !== undefined && { authInfo: ctx.authInfo })   // strictly pass-through — NEVER derived from headers here
    });
}
```

**Flow:** fresh per-request transport → `server.connect(transport)` (the normal ownership handoff) → inject the classified message through the transport's message callback → dispatch produces handler result / protocol rejection / streamed related messages + result → captured as the returned Response. Request exchanges run teardown on the transport's close chain AFTER the terminal response; notification exchanges resolve 202 immediately and do NOT run the close chain.

**Invariant:** The seam never writes era state — marking factory instances modern and installing modern-only handlers is the CALLING entry's job, done before invoke runs; unmarked instances stay protected (modern traffic gets the protocol-version error). authInfo is caller-validated pass-through: deriving it from headers inside the seam would bypass the middleware plane. Value-returning shape is what makes the whole serving stack independently testable without a real socket.

**Probe:** `packages/server/test/server/invokeSeam.test.ts` :53 ("serves a classified request on a high-level server instance and returns the response value"), :60 (low-level too), :77 ("era-removed method ⇒ method-not-found + HTTP 404"), :88 ("classified notifications ⇒ 202 no body"), :98 ("unmarked instances protected"), :113 ("original request + caller-supplied authInfo reach handler context").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "invoke PerRequestHTTPServerTransport InvokeContext handleMessage", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt connect-inject-capture composition for stateless per-exchange serving; adapt Response shaping to your edge runtime; omit transport internals (`per-request-transport.md` owns them).
