<!-- capsule-v2 -->
# Per-request micro-transport — how does a stateless server serve one HTTP exchange on a real, disposable Transport?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What lifecycle and response-shaping rules let a fresh server instance handle exactly one request — including mid-call SSE upgrades and origin-keyed HTTP statuses?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/perRequestTransport.ts`: `PerRequestHTTPServerTransport` (:122+), `_dispatchWindowOpen` (:143, :216-220), `_terminalDelivered` latch (:133, :261-264), `send` status mapping (:240-325), `handleMessage` single-use gate (:185-232).
**Signature:** `handleMessage(message: JSONRPCRequest|JSONRPCNotification, extra?: {request?, authInfo?}): Promise<Response>`; `send(message, options?)` implements the Transport interface toward the connected server.
**Data Shape:** Strictly single-use (`_used`), start-once, connect-required. Response modes: `'json'` | `'sse'` | `'auto'`. authInfo is strictly pass-through — NEVER derived from request headers.

### Decisive source
```ts
// The HTTP status is keyed on the error's ORIGIN, not on its bare code: only
// errors produced inside the dispatch window … are answered with the mapped
// ladder status. Handler-produced errors, whatever their code, stay in-band
// on HTTP 200 — except MissingRequiredClientCapability (-32021) … Must agree
// with httpStatusForErrorCode (core-internal), which is deliberately NOT called
// here: its ?? 400 ladder fallback would wrongly map window codes outside the table.
const ladderStatus = errorCode !== undefined &&
    (this._dispatchWindowOpen || errorCode === ProtocolErrorCode.MissingRequiredClientCapability)
        ? LADDER_ERROR_HTTP_STATUS[errorCode] : undefined;
```

**Flow:** handleMessage → abort check → deferred Response promise → dispatch-window OPEN (synchronous delivery to protocol layer; pre-handler gates answer inside it) → forced-SSE upgrades after gates pass → handler output: terminal response settles JSON 200 or finalizes the stream; mid-call notifications/server-to-client requests upgrade to SSE and ride it (dropped in 'json' mode with a construction-time warning); unrelated-request-id sends are dropped (no session-wide stream exists). Notifications answer 202 no-body. Client disconnect ⇒ close ⇒ pending promise rejects ConnectionClosed ⇒ entry answers 499.

**Invariant:** The window flag is what makes "ladder-originated vs handler-produced" OBSERVABLE: gates run synchronously during delivery; handlers always run after (microtask). One terminal response per exchange (`_terminalDelivered`); once a stream is committed, status errors ride the stream instead of the HTTP line. Late writes after close are silently dropped.

**Probe:** `packages/server/test/server/perRequestTransport.test.ts` :85 ("serves exactly one exchange"), :99 ("answers notification POST bodies with 202"); streaming shapes via `perRequestStreaming.test.ts`; carrier pin `classificationCarrierPin.test.ts`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "PerRequestHTTPServerTransport _dispatchWindowOpen _terminalDelivered", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt the per-exchange transport + dispatch-window flag pattern for stateless RPC serving; adapt response modes to your runtime's streaming support; omit the 499 bridge if your framework reports disconnects differently.
