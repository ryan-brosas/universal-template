<!-- capsule-v2 -->
# Push-API era guard — how do you retire server→client requests on an instance that can no longer send them?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When a protocol revision removes the server→client request channel, how do deprecated push APIs fail without ever touching the wire?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/server.ts`: `_assertPushApiInServedEra` (:741-752); call sites `ping` (:1027-1030), `createMessage` impl (:1076), `elicitInput` (:1160), `listRoots` (:1279).
**Signature:** `private _assertPushApiInServedEra(method: string): void` — throws `SdkError(SdkErrorCode.MethodNotSupportedByProtocolVersion, …, { method, era: '2026-07-28' })`.
**Data Shape:** Synchronous local throw BEFORE `this.request(...)`; no transport traffic.

### Decisive source
```ts
private _assertPushApiInServedEra(method: string): void {
    if (this._servedModernEra()) {
        throw new SdkError(
            SdkErrorCode.MethodNotSupportedByProtocolVersion,
            `Server-to-client requests are not available on protocol revision ${this._negotiatedProtocolVersion}: ` +
                `'${method}' cannot be sent while serving a request on that revision. ` +
                `Return inputRequired({ ... }) from the handler instead — the client fulfils the embedded ` +
                `requests and retries the original request (multi round-trip requests).`,
            { method, era: '2026-07-28' });
    }
}
```

**Flow:** push-style call → guard first (BEFORE capability checks) → modern-era instance throws typed error carrying the migration steer; legacy-era instances keep working unchanged. The base protocol layer would ALSO reject these methods on the modern era (its wire registry has no such request) — this guard runs FIRST only to carry the actionable steer.

**Invariant:** The guard is checked per CALL, not per instance construction: a factory serving both eras produces instances where these APIs work or throw depending on which era got pinned. Error messages are migration documentation: name the replacement API (`inputRequired(...)`) and the mechanism (client fulfils + retries).

**Probe:** `packages/server/test/server/inputRequired.test.ts` :476+ ("ctx.mcpReq.elicitInput rejects before any wire traffic… catch-all surfaces the inputRequired() steer as isError"); `serveStdio.test.ts` :759 ("outbound era gate on a modern-pinned connection").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "_assertPushApiInServedEra MethodNotSupportedByProtocolVersion createMessage elicitInput", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt guard-before-capability-check ordering + typed local errors with migration steers for removed capabilities; adapt error codes to your SDK taxonomy; omit deprecation-window policy prose (spec-level).
