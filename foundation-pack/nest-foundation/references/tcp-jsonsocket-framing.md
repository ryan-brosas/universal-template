<!-- capsule-v2 -->
# TCP JsonSocket framing — how do you carry length-prefixed JSON over a raw TCP stream without recursion, multi-byte corruption, or unbounded buffers?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** What is the minimal state machine that reassembles pipelined, chunked, UTF-8-split JSON frames from TCP segments and fails closed on every malformed input?

## `${charLength}#${json}` with an iterative reassembly loop
**Path/Symbol:** `packages/microservices/helpers/json-socket.ts:JsonSocket.handleData` (30-84) + `formatMessageData` (92-97); base latch `packages/microservices/helpers/tcp-socket.ts:TcpSocket` (7-75); client flush `packages/microservices/client/client-tcp.ts:ClientTCP.handleClose` (160-171).
**Signature:** `protected handleData(dataRaw: Buffer | string)`; `private formatMessageData(message: any): string`; `sendMessage(message: any, callback?)`.
**Data Shape:** state = `contentLength: number | null` + `buffer: string`; frame on the wire is `<length-in-decoded-characters>#<JSON text>`; `maxBufferSize` default `(512*1024*1024)/4` chars; errors: `MaxPacketLengthExceededException(bufferLength)`, `CorruptedPacketLengthException(raw)`, `InvalidJSONFormatException`.

### Decisive source
```ts
protected handleData(dataRaw: Buffer | string) {
  const data = Buffer.isBuffer(dataRaw) ? this.stringDecoder.write(dataRaw) : dataRaw;  // multi-byte safe
  this.buffer += data;
  // Iterative loop replaces recursion to prevent stack overflow on pipelined
  // TCP messages (e.g. many small frames arriving in one read event).
  while (true) {
    if (this.buffer.length > this.maxBufferSize) {                       // EVERY iteration, before parsing
      const bufferLength = this.buffer.length;
      this.buffer = '';
      throw new MaxPacketLengthExceededException(bufferLength);
    }
    if (this.contentLength === null) {
      const i = this.buffer.indexOf(this.delimiter);                     // '#' — may itself be split!
      if (i === -1) break;
      this.contentLength = parseInt(this.buffer.substring(0, i), 10);
      if (isNaN(this.contentLength)) { this.contentLength = null; this.buffer = ''; throw new CorruptedPacketLengthException(...); }
      this.buffer = this.buffer.substring(i + 1);
    }
    if (this.contentLength !== null) {
      const length = this.buffer.length;
      if (length === this.contentLength) { this.handleMessage(this.buffer); }        // resets both
      else if (length > this.contentLength) {
        const message = this.buffer.substring(0, this.contentLength);
        const rest = this.buffer.substring(this.contentLength);
        this.handleMessage(message);                                     // resets buffer to ''
        this.buffer = rest;                                              // restore remainder, keep looping
        continue;
      } else break;                                                      // incomplete — wait for more data
    } else break;
  }
}
```

**Flow:** bytes → StringDecoder → append → loop: parse header when a `#` exists (a missing `#` may mean the length digits themselves are split across chunks), then wait for exactly `contentLength` characters; exact ⇒ emit and reset; surplus ⇒ emit prefix, KEEP the remainder, continue the same tick (pipelined frames drain in order in one pass). Any throw inside the base class's `onData` try/catch becomes socket `'error'` emission + `socket.end()` FIN — fail-close, never half-alive. The base latch (`isClosed`: true on close/error, false on connect) makes `sendMessage` invoke `callback(NetSocketClosedException)` instead of writing into a dead socket.
**Invariant:** message ORDER equals arrival order through the reassembly queue (spec pipes 100 numbered messages over a real loopback socket and asserts strict `lastNumber+1`); the buffer can never grow past maxBufferSize; no exception path leaves stale partial state that could mis-parse later frames.
**Probe:** `packages/microservices/test/json-socket/message-parsing.spec.ts` (`'13#"Hello there"'`, `'5#"hey"4#true'` two frames one packet, chunked `'13#"Hel'+'lo there"'`, U+0629 split mid-codepoint via raw byte arrays, corrupted `wtf#...`, invalid complete frame → error event + FIN); `max-buffer-size.spec.ts` (default/custom limits, chunked delimiter-less accumulation trips the guard, buffer cleared after throw, limit-0 rejects everything, exactly-at-limit passes); `connection.spec.ts` (ping/pong round-trip, long special-char payload, ordered 100-message pipeline, isClosed flips).
**Runner caveat:** direct test execution blocked (deps uninstalled); expectations quoted from spec source read directly.

## Client/server lifecycle around the codec
`ClientTCP`: event listeners registered before connect are PARKED in `pendingEventListeners` and drained FIFO once the socket exists; `connectionPromise` memoizes connect; `handleClose` flushes EVERY routingMap callback with `Error('Connection closed')` then clears (same fail-close contract as redis). `ServerTCP`: lookup pattern = raw string or `JSON.stringify(packet.pattern)`, normalized at lookup by base `getRouteFromPattern`; requests without handler get `{id, status:'error', err:NO_MESSAGE_HANDLER}` written back; `handleClose` retries `listen` after `retryDelay` until `retryAttempts` is exhausted (manual termination disables retrying).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", name_pattern: "JsonSocket.*", fields: ["lines"], limit: 10 });
// live @ pin: rank#1 JsonSocket Class helpers/json-socket.ts 13-98
await mcp.codebase_memory.trace_path({ project: "nest", function_name: "handleData", direction: "inbound", depth: 2 });
// live @ pin: single caller TcpSocket.onData — all failures funnel through its fail-close catch
```

## Verdict
Adopt the character-counted `len#json` framing with iterative reassembly verbatim for any newline-free binary-safe channel; adopt "check the cap every iteration BEFORE parsing" and "fail-close on codec exceptions" as non-negotiable invariants. Adapt the StringDecoder boundary to your runtime's streaming decoder and consider byte-length headers if your transport guarantees whole-codepoint delivery (character counting here matches the decoded-string buffer, not raw bytes). Omit the closed-latch callback rejection only if your senders are guaranteed post-connect.
