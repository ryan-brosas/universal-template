<!-- capsule-v2 -->
# WebSocket replay buffer + listener hygiene — how do outbound messages survive reconnects, and why does listener removal order matter for GC?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Which messages replay after a drop, when are they evicted, and what cleanup pattern prevents closure accumulation across reconnect storms?

## UUID-keyed CircularBuffer with server-confirmed eviction
**Path/Symbol:** `src/cli/transports/WebSocketTransport.ts`: `write` buffer branch (:660-681), `replayBufferedMessages`/:574-634, `removeWsListeners`/:360-378, `doDisconnect`/:380-395.
**Signature:** `messageBuffer = new CircularBuffer<StdoutMessage>(1000)`; only uuid-bearing messages buffered; `lastSentId` tracks newest uuid.
**Data Shape:** Node 'ws' exposes upgrade-response header `x-last-request-id` ⇒ evict confirmed prefix by findIndex(uuid===lastId) then REBUILD buffer with remainder. Bun's native WS exposes no upgrade headers ⇒ replay ALL, rely on server-side UUID dedup.

### Decisive source
```ts
for (const message of messagesToReplay) {
  const success = this.sendLine(jsonStringify(message) + '\n')
  if (!success) { this.handleConnectionError(); break }
}
// Do NOT clear the buffer after replay — messages remain buffered until
// the server confirms receipt on the NEXT reconnection. This prevents
// message loss if the connection drops after replay but before the
// server processes the messages.
```
```ts
// Remove listeners BEFORE close() so the old WS + closures can be GC'd
// promptly instead of lingering until the next mark-and-sweep. Handlers
// are stable class-property arrows so removeEventListener/off can match them;
// each runtime detaches with ITS API (removeEventListener vs .off).
this.removeWsListeners(this.ws); this.ws.close(); this.ws = null
```

**Flow:** write(uuid msg) → buffer+lastSentId even while disconnected → on open: Node reads server's confirmed id and evicts through it; Bun replays everything → replay sends serially, aborting into handleConnectionError on first failed send → buffer persists past replay until next confirmation cycle.
**Invariant:** Replay is at-least-once; end-to-end exactly-once comes from server UUID dedup — client MUST NOT clear the buffer optimistically. Listener arrays are the leak surface under reconnect storms: same handler references in/out, matching runtime API, removal strictly before close().
**Probe:** `grep -n "removeWsListeners(this.ws)" src/cli/transports/WebSocketTransport.ts` (`:391`), `grep -n "message.uuid === lastId" src/cli/transports/WebSocketTransport.ts` (`:582`), `grep -n "Do NOT clear the buffer after replay" src/cli/transports/WebSocketTransport.ts` (`:630`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "replayBufferedMessages removeWsListeners CircularBuffer", limit: 5 });
```

## Verdict
Adopt confirm-then-evict replay and detach-before-close hygiene. Adapt buffer size and confirmation channel (header vs ack frame). Omit Bun dual-path if single-runtime.
