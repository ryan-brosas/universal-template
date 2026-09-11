<!-- capsule-v2 -->
# StdioConnectionChannel drain latch — how do you discard an optimistic instance without dropping a client request it already accepted?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** A disposable channel wraps the shared wire transport — what bookkeeping lets a probe instance be closed while guaranteeing its in-flight answers reach the wire first?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/serveStdio.ts`: `StdioConnectionChannel` (:146-277) — `_pendingRequests` Set + `_drainWaiters` (:152-154), settle-on-answer `send` (:174-193), cancel-settling `deliver` (:200-219), `whenRequestsAnswered` (:230-245), close ordering (:247-261); probe-discard consumer `discardProbeInstance` (:539-570) with `DISCARD_ANSWER_TIMEOUT_MS = 3000` (:137).
**Signature:** `whenRequestsAnswered(timeoutMs: number): Promise<boolean>` — `false` only when the bound elapsed with requests still unanswered.
**Data Shape:** `_pendingRequests: Set<RequestId>` (ids delivered, not yet answered); waiters released when set empties OR channel closes.

### Decisive source
```ts
async send(message, options) {
    if (isJSONRPCResultResponse(message) || isJSONRPCErrorResponse(message)) {
        const { id } = message;
        if (id !== undefined) this._settle(id);   // settle whether or not the wire write succeeds
    }
    if (this._closed) return;                      // discarded instance: late sends DROPPED
    if (this._outboundIntercept?.(message) === 'handled') return;
    return this._wire.send(message, options);
}
// deliver(): by protocol contract a CANCELLED request may legitimately go unanswered —
// a delivered cancellation settles the id it names so nothing waits forever.
```
```ts
// The probe instance served only the discover exchange; closing its channel must not tear
// down the connection. Let the in-flight DiscoverResult reach the wire before the instance
// is closed... bounded as a backstop so nothing can wedge the connection's pump.
const answered = await instance.channel.whenRequestsAnswered(DISCARD_ANSWER_TIMEOUT_MS);
if (!answered) reportError(new Error(`Discarded the probe instance with requests still unanswered after ...`));
await instance.product.close();
```

**Flow:** deliver adds request ids / settles cancelled ones → instance answers through send → send settles THEN writes → discard path drains (bounded 3s backstop) → product.close() → channel.close() clears pending, releases waiters, fires `_onInstanceClose` then `onclose` (the `discarding` guard in `onInstanceClosed` prevents a probe discard from tearing down the whole connection).

**Invariant:** Settle-before-write: an answer counts as given even if the wire write fails (write failures surface via wire error reporting). The outbound intercept ('handled') lets the entry own specific messages (listen fan-out) — order matters: closed-check BEFORE intercept BEFORE wire write. Every wait is bounded; unbounded drains would let one edge freeze the inbound pump.

**Probe:** `packages/server/test/server/serveStdio.test.ts` :256-495 (probe window incl. pipelined requests answered before discard); :816+ (legacy shim through the stdio entry — channel delivery under re-entry).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "StdioConnectionChannel whenRequestsAnswered _pendingRequests _settle", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt pending-set + settle-on-send/cancel + bounded-drain-before-dispose for any proxy-channel over a shared transport; adapt timeout constants; omit the listen-router intercept details (`listen-router.md`).
