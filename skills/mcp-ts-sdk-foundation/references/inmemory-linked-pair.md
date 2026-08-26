<!-- capsule-v2 -->
# In-memory linked transport pair — how does a same-process client/server pair queue pre-start messages and close symmetrically?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What contract must a loopback transport keep so test harnesses behave like real transports?

## Linked pair
**Path/Symbol:** `packages/core-internal/src/util/inMemory.ts`: class `InMemoryTransport` (:73-130), `createLinkedPair` (:86-92), queued-start (:94-100), chained close (:102-113).
**Signature:** `static createLinkedPair(): [InMemoryTransport, InMemoryTransport]`; `send(message, options?: {relatedRequestId?, authInfo?})`.
**Data Shape:** pre-start sends queue in FIFO `_messageQueue`; authInfo rides the message extra (test-only auth scenarios); not-connected send throws `SdkError(NotConnected)`.

### Decisive source
```ts
// :94-113 drain-on-start + peer-chained teardown
async start(): Promise<void> {
    while (this._messageQueue.length > 0) {
        const queuedMessage = this._messageQueue.shift()!;
        this.onmessage?.(queuedMessage.message, queuedMessage.extra);
    }
}
async close(): Promise<void> {
    if (this._closed) return;            // idempotent latch
    this._closed = true;
    const other = this._otherTransport;
    this._otherTransport = undefined;
    try { await other?.close(); } finally { this.onclose?.(); }
}
```

**Flow:** either side may be created and sent-to before its Protocol starts — messages buffer until `start()` drains them in order. Closing one side closes the PEER first (`other?.close()`), then fires its own onclose; the `_closed` latch makes double-close inert and the peer link is severed BEFORE awaiting so re-entrant closes can't loop.

**Invariant:** onclose must fire even when the peer's close throws — hence try/finally ordering; a porter who awaits the peer outside finally loses their own shutdown signal on partial failure. Queue-before-start is what lets tests construct both protocols THEN connect without dropping early notifications.

**Probe (direct tests):** `packages/core-internal/test/inMemory.test.ts` pins pair creation, queue-drain-on-start, and close chaining.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "InMemoryTransport createLinkedPair queue close", limit: 3 });
```

## Verdict
Adopt for test harnesses only (the doc comment steers production to Streamable HTTP against localhost); adapt queue bounds if you need backpressure signals; omit nothing.
