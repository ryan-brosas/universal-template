<!-- capsule-v2 -->
# SSE event stream contract — how do you stream a bus over Server-Sent Events without losing events during connection setup, and how must the stream terminate and stay alive?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** How does an SSE endpoint subscribe to an event bus so that events published while the HTTP body is still starting are never lost, filter per-instance, terminate on instance disposal, and survive proxies?

## Eager-subscribe stream kernel
**Path/Symbol:** `packages/opencode/src/server/routes/instance/httpapi/handlers/event.ts` (`eventResponse` :25-87, `eventData` :12-19); bus id-stamp at `packages/opencode/src/bus/global.ts:14-19`; disposed schema at `packages/opencode/src/server/event.ts:6-10`.
**Signature:** `eventResponse(events: EventV2.Interface) → Effect<HttpServerResponse (text/event-stream)>`; `GlobalBus.emit("event", GlobalEvent{directory?, project?, workspace?, payload}) → boolean`.
**Data Shape:** wire event `{id, type, properties}`; unbounded `Queue<EventV2.Payload>` per connection; GlobalEvent carries optional routing fields used for filtering.

### Decisive source
```ts
// handlers/event.ts:29-32 — register the listener BEFORE the body fiber starts:
// Listener registration is eager, so events published after this point cannot
// be lost while the HTTP body fiber is starting or emitting server.connected.
const queue = yield* Queue.unbounded<EventV2.Payload>()
const unsubscribe = yield* events.listen((event) => Effect.sync(() => Queue.offerUnsafe(queue, event)))
yield* Effect.addFinalizer(() => unsubscribe)
// :37-38 — per-instance filter:
event.location?.directory === instance.directory &&
(event.location.workspaceID === undefined || event.location.workspaceID === workspaceID),
```

**Flow:** eager queue+listen ⇒ first emitted frame is synthetic `server.connected` ⇒ main stream filters by directory (+workspace) ⇒ merged with a GlobalBus listener that converts same-directory `server.instance.disposed` payloads into terminal frames via `Stream.merge(disposed, {haltStrategy:"left"})` + `Stream.takeUntil(type==="server.instance.disposed")` (:59-62) ⇒ heartbeat `Stream.tick("10 seconds")` merged left-halting keeps the connection alive (:63-66) ⇒ `Sse.encode()` channel + `Stream.encodeText`, response headers `Cache-Control: no-cache, no-transform`, `X-Accel-Buffering: no`, `X-Content-Type-Options: nosniff` (:77-84).
**Invariant:** Subscription precedes any emission — no gap between connect and listen. Every GlobalBus payload carries an `id`: emit() stamps ascending `evt_` ids when absent (`payload.id = payload.syncEvent?.id ?? Identifier.create("evt","ascending")`). The stream ends ONLY on the instance-disposed frame; heartbeats continue otherwise. Proxy-defeating headers are part of the contract.
**Probe:** `packages/opencode/test/server/httpapi-event.test.ts` — ":45 serves event stream" pins 200 + all four headers + first frame `server.connected`; ":80 delivers instance events after the initial event" pins POST /session → next frame `session.created`; source pin:
```bash
grep -n "Listener registration is eager" packages/opencode/src/server/routes/instance/httpapi/handlers/event.ts
```
expect exactly 1 hit at :29.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "subscribe server.connected event stream SSE instance disposed heartbeat", limit: 8 });
```

## Verdict
Adopt eager-subscribe-then-stream, directory/workspace filtering, disposed-frame termination, and the heartbeat/proxy-header set; adapt the filter key to your tenancy model; omit opencode's specific EventV2 payload schema and `evt` id alphabet.
