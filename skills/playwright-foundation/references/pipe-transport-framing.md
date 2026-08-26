<!-- capsule-v2 -->
# Length-prefixed pipe framing — how do you turn a raw byte stream into whole messages without re-entrancy or post-close writes?

**Source:** playwright (microsoft/playwright) Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `playwright`. **Question:** When a peer speaks a length-prefixed protocol over stdio fds, how do you frame partial reads into messages, deliver them outside the read stack, and fail fast after close?

## PipeTransport incremental state machine
**Path/Symbol:** `packages/utils/pipeTransport.ts:PipeTransport` (class lines 32-104; `_dispatch` 77-103); `packages/utils/task.ts:makeWaitForNextTask` (lines 18-55).
**Signature:** `new PipeTransport(pipeWrite, pipeRead, closeable?, endian: 'be'|'le' = 'le')`; `send(message: string): void`; callbacks `onmessage?: (message: string) => void`, `onclose?: () => void`.
**Data Shape:** Accumulator `_data: Buffer` + remaining-bytes counter `_bytesLeft`; wire format = **4-byte unsigned length prefix** (endianness-selectable; Chromium speaks LE here by default) followed by that many UTF-8 bytes.

### Decisive source
```ts
_dispatch(buffer: Buffer) {
  this._data = Buffer.concat([this._data, buffer]);
  while (true) {
    if (!this._bytesLeft && this._data.length < 4) break;        // need header
    if (!this._bytesLeft) {
      this._bytesLeft = this._endian === 'be' ? this._data.readUInt32BE(0) : this._data.readUInt32LE(0);
      this._data = this._data.slice(4);
    }
    if (!this._bytesLeft || this._data.length < this._bytesLeft) break; // need body
    const message = this._data.slice(0, this._bytesLeft);
    this._data = this._data.slice(this._bytesLeft);
    this._bytesLeft = 0;
    this._waitForNextTask(() => { if (this.onmessage) this.onmessage(message.toString('utf-8')); });
  }
}
send(message: string) {
  if (this._closed) throw new Error('Pipe has been closed');
  ... write 4-byte length then payload ...
}
close() { /* Let it throw. */ this._closeableStream!.close(); }
```
`makeWaitForNextTask` picks the delivery task per runtime: `setImmediate` on Node ≥11, `setTimeout(0)` under Electron (Electron v12 bug), and a nested `setImmediate` drain loop on Node <10 to defeat the Node task/microtask ordering bug — each delivery leaves the stream's 'data' call stack before user code runs.

**Flow:** chunk arrives → concat → loop: parse header if absent → wait until body complete → hand off via next-task → repeat with remainder. `'close'` on the read side sets `_closed` and fires `onclose`. Writes after close throw immediately.
**Invariant:** A message handler must never run synchronously inside the read event (it may call `send()`, which must not interleave with the parser); every send after close throws rather than silently buffering.
**Probe:** No dedicated upstream unit test file exists beside `pipeTransport.ts`; behavior is pinned indirectly through library suites driving pipe-launched browsers (see `tests/library/browsertype-launch.spec.ts`). Coverage caveat recorded in-capsule.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "playwright", query: "PipeTransport length prefix dispatch endian", limit: 10 });
// resolves PipeTransport (utils/pipeTransport.ts 32-104), makeWaitForNextTask (utils/task.ts)
```

## Verdict
Adopt the two-counter incremental framer, endianness parameter, next-task delivery, and throw-on-closed-send as portable contracts. Adapt the prefix width/endianness to your wire protocol and the task scheduler to your runtime. Omit the legacy Node<11 fallback unless you must support it.
