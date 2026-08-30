<!-- capsule-v2 -->
# StdioServerTransport stream discipline — newline framing, drain-gated backpressure, and listener-count-conditional stdin pause

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What does a correct stdio JSON-RPC transport do on stdout error, write backpressure, close, and shared-stdin coexistence?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/stdio.ts`: `StdioServerTransport` whole (:19-154) — arrow-function handlers (:44-62), `processReadBuffer` loop (:80-93), `close` with listenerCount gate (:95-117), settle-once `send` (:119-153).
**Signature:** `send(message): Promise<void>` resolving on full write OR 'drain'; `maxBufferSize` option (default 10 MB) via ReadBuffer.
**Data Shape:** Newline-delimited JSON over process stdio (`ReadBuffer.readMessage()` null = need more data).

### Decisive source
```ts
async close(): Promise<void> {
    ...
    // Check if we were the only data listener
    const remainingDataListeners = this._stdin.listenerCount('data');
    if (remainingDataListeners === 0) {
        // Only pause stdin if we were the only listener — prevents interfering
        // with other parts of the application that might be using stdin.
        this._stdin.pause();
    }
    this._readBuffer.clear();
    this.onclose?.();
}
```
```ts
// send(): settled-once latch; resolve on synchronous write OR the later 'drain';
// reject if stdout errors first. Handlers detach BOTH listeners on either outcome.
let settled = false;
const onError = (error) => { if (settled) return; settled = true; /* off both */ reject(error); };
const onDrain  = ()        => { if (settled) return; settled = true; /* off both */ resolve(); };
this._stdout.once('error', onError);
if (this._stdout.write(json)) { ...resolve(); } else if (!settled) { this._stdout.once('drain', onDrain); }
```

**Flow:** start subscribes `_ondata/_onerror/_onstdouterror` (double-start throws with a steer — Server.connect calls start automatically) → append+drain loop emits messages until readMessage() returns null → per-message parse errors report but do NOT kill the stream, while append/overflow errors DO close → stdout error reports + closes exactly once (onclose idempotence test). Send after closed rejects immediately.

**Invariant:** Parse-failure vs stream-failure are different classes: one message failing must not tear down a healthy pipe; a buffer overflow or stdout EPIPE must. The pause-only-if-last-listener rule is what makes embedding an MCP server in a larger CLI safe. The settled latch prevents double-settle when error and drain race.

**Probe:** `packages/server/test/server/stdio.test.ts` :27 (start/close clean), :44 (not reading until started), :70 (multiple messages), :106/:125 (stdout error fires onerror once, no double onclose), :141 ("reject send() when stdout errors before drain" — EPIPE), :162 (reject after close), :183 (custom maxBufferSize), :206 (overflow ⇒ onerror + close).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "StdioServerTransport ReadBuffer processReadBuffer maxBufferSize", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt newline-framed read loop + once-latched drain/error send + conditional-pause close for any Node stdio protocol transport; adapt buffer limits; omit shim-level `process` indirection.
