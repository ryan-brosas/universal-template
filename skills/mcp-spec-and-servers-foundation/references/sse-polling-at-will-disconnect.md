<!-- capsule-v2 -->
# SSE polling via server-side at-will disconnect (SEP-1699) — when may a ≤2025-11-25-era Streamable HTTP server close the response stream before the JSON-RPC response, what must the client then do, and what did the 2026-07-28 revision change?

**Source:** modelcontextprotocol/specification MIT `main@57ac4a2e` (+ SEP Final); Codebase Memory projects `modelcontextprotocol` (fresh path-slugged index; the short-name `modelcontextprotocol` project serves a STALE pre-drift graph — see work record [DONE:160]) and `servers`. **Question:** Under which exact conditions can a server drop the SSE connection of an in-flight request without answering it, how must the client poll/resume/cancel, and why does the same "close" mean the opposite thing in the modern era?

## Era ladder: SEP-1699 → 2025-11-25 transports → 2026-07-28 removal
**Path/Symbol:** `seps/1699-support-sse-polling-via-server-side-disconnect.md` (Status: Final, whole); normative text `docs/specification/2025-11-25/basic/transports.mdx` (:105–131 POST-initiated streams, :143–154 GET listen streams, :164–191 Resumability and Redelivery); superseded predecessor `docs/specification/2025-06-18/basic/transports.mdx:107`; modern-era removal `docs/specification/2026-07-28/basic/transports/streamable-http.mdx:97–101` + `:155–158`. Behavioral twin `servers/src/everything/transports/streamableHttp.ts` (`InMemoryEventStore` :11–37, per-session construction :75).
**Signature:** SSE wire events, not callables — priming event `{ id: <string>, data: "" }`; pacing event carrying standard `retry: <ms>` field; resume header `Last-Event-ID: <eventId>` on an HTTP **GET** to the MCP endpoint.
**Data Shape:** Event IDs are server-minted strings, globally unique across all streams within one session (or across all streams of one client when session management is unused), and SHOULD encode enough info to route a `Last-Event-ID` back to its originating stream. The `data` of the priming event is the EMPTY string — legal per the WHATWG SSE standard; conforming clients record the id for `Last-Event-ID` but fire NO event callback.

### Decisive source
```md
<!-- 2025-06-18/basic/transports.mdx:107 — the rule SEP-1699 replaced -->
- The server **SHOULD NOT** close the SSE stream before sending the JSON-RPC _response_

<!-- 2025-11-25/basic/transports.mdx:106–116 — the SEP-1699 mechanism -->
- The server **SHOULD** immediately send an SSE event consisting of an event
  ID and an empty `data` field in order to prime the client to reconnect
  (using that event ID as `Last-Event-ID`).
- After the server has sent an SSE event with an event ID to the client, the
  server **MAY** close the _connection_ (without terminating the _SSE stream_)
  at any time in order to avoid holding a long-lived connection. The client
  **SHOULD** then "poll" the SSE stream by attempting to reconnect.
- If the server does close the _connection_ prior to terminating the _SSE stream_,
  it **SHOULD** send an SSE event with a standard [`retry`] field before
  closing the connection. The client **MUST** respect the `retry` field,
  waiting the given number of milliseconds before attempting to reconnect.

<!-- 2025-11-25/basic/transports.mdx:126–129 — disconnection ≠ cancellation in THIS era -->
     - Disconnection **SHOULD NOT** be interpreted as the client cancelling its request.
     - To cancel, the client **SHOULD** explicitly send an MCP `CancelledNotification`.

<!-- 2025-11-25/basic/transports.mdx:184–187 — redelivery boundary -->
   - The server **MUST NOT** replay messages that would have been delivered on a
     different stream.
   - This mechanism applies regardless of how the original stream was initiated (via
     POST or GET). Resumption is always via HTTP GET with `Last-Event-ID`.

<!-- 2026-07-28/basic/transports/streamable-http.mdx:97–101 + :157 — the modern inversion -->
the core protocol, `notifications/cancelled`, is used only on the
[stdio] transport; on Streamable HTTP, closing the SSE response stream is itself the cancellation
signal and no `notifications/cancelled` message is expected

Resumable SSE streams via `Last-Event-ID` are not supported.
```

**Flow (legacy era ≤2025-11-25, POST-initiated request):**
1. Client POSTs the JSON-RPC request with `Accept: text/event-stream, application/json`.
2. Server chooses SSE; it **SHOULD** immediately write the priming event `{id, data:""}` so the client has a resume cursor BEFORE any payload.
3. Server works; whenever it wants the TCP connection back it **SHOULD** first emit an event with a `retry` field (its chosen backoff hint in ms), then closes the CONNECTION. The SSE *stream* stays logically open.
4. Client sees the disconnect, treats it as transient network failure (NOT cancellation), waits `retry` ms, and re-issues **GET** on the MCP endpoint with `Last-Event-ID: <last received id>`.
5. Server correlates the id to the originating stream and replays/redelivers everything after that cursor on the resumed stream, eventually delivering the JSON-RPC response; after the response it terminates the stream.
6. GET-opened listen streams follow the same polling pattern (:150–153); each message is delivered on exactly ONE connected stream — never broadcast (:159–160).
7. Cancellation in this era is EXPLICIT: a `CancelledNotification` over the wire; a bare disconnect carries no cancel semantics (:128–129).

**Flow (modern era 2026-07-28):** none of the above survives. No GET stream endpoint (405), no `Mcp-Session-Id`, and an inbound `Last-Event-ID` header is IGNORED ("streams are not resumable", :687). Conversely, closing the SSE response stream IS the cancellation signal on HTTP — the mirror image of the legacy rule. Dual-era servers therefore run two opposite close-semantics against the same transport verb.

**Invariant:**
1. At-will close is legal ONLY after at least one event-with-id reached the client — closing an unprimed stream strands the request with no resume cursor (that is precisely what the priming event buys).
2. Disconnect ≠ cancel in the ≤2025-11-25 eras; explicit `CancelledNotification` is the only cancel channel. Modern era inverts this: stream-close = cancel, notification reserved for stdio. Porting a client across eras with the wrong half makes every server restart look like a user abort (or vice versa).
3. Clients MUST honor `retry` ms before reconnecting — hammering violates the contract the SEP exists to create.
4. Redelivery NEVER crosses streams: replay only messages that belonged to the disconnected stream, resume always via GET + `Last-Event-ID` regardless of how the original stream opened.
5. The behavioral twin keeps this true by construction wiring, not discipline: `new InMemoryEventStore()` is created INSIDE the per-session branch (:75) — one store instance per session is what makes its flat Map scan safe; hoisting the store to module scope would replay another session's messages and break invariant 4. (Caveat: entries are never evicted — fine for the reference server, a leak in a long-lived process.)

### Twin excerpt (what a porter must replicate structurally)
```ts
// servers/src/everything/transports/streamableHttp.ts:15–36
async storeEvent(streamId: string, message: unknown): Promise<string> {
  const eventId = randomUUID();
  this.events.set(eventId, { streamId, message });   // streamId stored…
  return eventId;
}
async replayEventsAfter(lastEventId, { send }) {
  const entries = Array.from(this.events.entries());
  const startIndex = entries.findIndex(([id]) => id === lastEventId);
  if (startIndex === -1) return lastEventId;         // unknown cursor ⇒ no replay
  let lastId = lastEventId;
  for (let i = startIndex + 1; i < entries.length; i++) {
    const [eventId, { message }] = entries[i];       // …but scan ignores it:
    await send(eventId, message);                    // safe ONLY under per-session stores
    lastId = eventId;
  }
  return lastId;
}
```
Note the deliberate asymmetry: `storeEvent` records `streamId` yet `replayEventsAfter` scans the whole map ignoring it — correct here because the store is session-scoped (:75), a latent cross-stream bug if reused globally. That pairing (flat map + scoped construction site) IS the port.

**Probe:** No upstream test drives `replayEventsAfter` through a real disconnect/reconnect cycle (`servers/src/everything/__tests__/server.test.ts` exercises the HTTP surface only) — coverage caveat stands. Deterministic probes: line anchors above grep-verified verbatim at HEAD `57ac4a2e`; graph retrievals below resolve the twin symbols; `check_index_coverage` = `no_recorded_issue` + `metadata_match` on all five cited paths (draft page lives at `transports/streamable-http.mdx`, NOT `transports.mdx` — there is no draft-era single-file transports page).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project servers \
  --query 'InMemoryEventStore replay events resumability' --detail ids --limit 8
# → src/everything/transports/streamableHttp.ts : replayEventsAfter 21-36 · storeEvent 15-19 · Class 11-37
codebase-memory-mcp cli search_code --project modelcontextprotocol \
  --pattern 'Last-Event-ID' --file-pattern '*.mdx' --limit 4
# → docs/seps/1699-support-sse-polling-via-server-side-disconnect.mdx :47;49 (+transports.mdx)
# pass-20 note: search_graph BM25 noise-label filtering returns ZERO on this multi-word doc-page
# query; text grep (search_code) is the working primitive on spec prose pages
```

## Verdict
Adopt the era-aware ladder itself: prime-before-close, retry-paced polling, GET+`Last-Event-ID` resumption, per-session event-store scoping, explicit-notification cancellation for ≤2025-11-25 peers. Adapt the store implementation (in-memory Map → your durable queue/redis stream) and the backoff policy values. Omit for pure modern-era targets: the entire machinery is REMOVED in 2026-07-28 — there you ignore `Last-Event-ID`, return 405 on GET, mint no session IDs, and treat response-stream closure as cancellation; keep this capsule for dual-era dispatch (see `dual-era-server-dispatch`) where both readings of "close" coexist deliberately.
