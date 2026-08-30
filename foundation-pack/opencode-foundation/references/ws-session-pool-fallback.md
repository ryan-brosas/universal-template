<!-- capsule-v2 -->
# WebSocket session pool with HTTP fallback — how do you multiplex OpenAI Responses streams over one pooled socket per conversation, and when must it fall back to HTTP?

**Source:** opencode (Slate-licensed monorepo) @ `dev@0352100` (NEW plane: `plugin/openai/ws-pool.ts` + `ws.ts`, drift wave 4643e65→0352100). **Question:** How does a fetch-compatible wrapper route POST /responses streaming calls onto a per-session WebSocket while guaranteeing the request still succeeds when WebSockets are unavailable?

## The fetch-wrapper pool
**Path/Symbol:** `packages/opencode/src/plugin/openai/ws-pool.ts` (`createWebSocketFetch` :31-196, `PoolEntry` :17-24, `socket()` :217-242, `invalidate()` :244-251, `prune()` :170-179).
**Signature:** `createWebSocketFetch({httpFetch?, url?, connectTimeout?=15_000, idleTimeout?=300_000, maxConnectionAge?=3_300_000, streamRetries?=5}) → fetch-compatible fn + {close(), remove(sessionID)}`.
**Data Shape:** `pool: Map<"sessionID:conversation", PoolEntry{socket?, connectedAt?, lastUsedAt, busy, fallback, streamFailures}>`. Route gate: ONLY `POST …/responses` with JSON body `stream:true`, WITHOUT internal title header, WITH a session-affinity header (`x-session-affinity` or `session-id`) rides the socket; everything else goes straight to `httpFetch`.

### Decisive source
```ts
// ws-pool.ts:75-79 — fallback latch and busy lane both degrade to HTTP, never queue
if (entry.fallback) return httpFetch(input, httpInit)
if (entry.busy) return httpFetch(input, httpInit)
// ws-pool.ts:164-168 — retry budget counts ATTEMPTS-1 (Codex semantics), then latches
function recordStreamFailure(entry: PoolEntry) {
  entry.streamFailures++
  if (entry.streamFailures > streamRetries) entry.fallback = true
}
```

**Flow:** eligible request ⇒ claim lane (`busy=true`) ⇒ reuse socket if OPEN and age < 55min else invalidate+reconnect (15s connect timeout) ⇒ `streamResponsesWebSocket` returns an SSE-shaped Response; the FIRST event decides the outcome — wrapped API error (status ∉ [200,300)) is re-served as an HTTP-style Response with that status (:134-141), first-event failure resolves `false` ⇒ if fallback latched, replay via httpFetch, else return the failed SSE response. Terminal frames (`response.completed/done`) keep the socket healthy and reset `streamFailures=0`; any other terminal invalidates the socket. Close code **1009 message-too-big sets `fallback=true` IMMEDIATELY** (:116); connection-limit errors are retried on a FRESH stream attempt within the same budget (:128-132 + :198-201); aborts clear the failure count but still invalidate (:147-151). Idle pruner runs every min(idleTimeout,60s), unref'd, skipping busy AND fallback entries; `remove(sessionID)` force-invalidates.
**Invariant:** One socket per `(sessionID, "conversation")` — requests for the SAME session while busy silently use HTTP instead of queueing or sharing mid-stream. The `fallback` latch is sticky until `remove()`: after it flips, ALL subsequent requests for that session bypass the pool (test :219 "keeps HTTP fallback active after its idle timeout"). Failure budget is shared across setup failures, mid-stream failures, and connection-limit retries — five total, then permanent fallback.
**Probe:** direct test pins — `packages/opencode/test/plugin/openai-ws.test.ts`: ":150 reuses one healthy websocket for sequential requests", ":174 rotates a socket that exceeds max connection age", ":240 falls back immediately to HTTP when a websocket request is too large", ":670 falls back to HTTP while a websocket lane is busy", ":501 shares the websocket retry budget across stream and connection limit failures"; source pin:
```bash
grep -c 'websocket_connection_limit_reached' packages/opencode/src/plugin/openai/ws-pool.ts
```
expect 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "createWebSocketFetch pool fallback session affinity responses", limit: 8 });
```

## Verdict
Adopt the per-conversation pooling + sticky-fallback degradation model and the first-event error unwrapping; adapt header names/URL gating to host transport; omit the OpenAI-specific Responses protocol constants.
