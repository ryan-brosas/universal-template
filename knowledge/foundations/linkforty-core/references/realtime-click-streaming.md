<!-- capsule-v2 -->
# Real-time click streaming — process-local EventEmitter broadcast with filter-at-subscription WebSocket fan-out

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** How do live dashboards receive clicks without a message broker, and what are the scale limits of that choice?

## clickEventEmitter + subscribeToClickEvents + /api/debug/live WS
**Path/Symbol:** `src/lib/event-emitter.ts:clickEventEmitter` (:7), `emitClickEvent` (:53-55), `subscribeToClickEvents` (:61-70); consumer `src/routes/debug.ts` websocket handler (:306-362).
**Signature:** `function subscribeToClickEvents(callback: (eventData: ClickEventData) => void): () => void` — returns unsubscribe closure over `.off`.
**Data Shape:** ClickEventData carries eventId/timestamp/link/geo/device/redirect decision (`redirectUrl`, `redirectReason`, `targetingMatched`) + UTM/referer/language; emitted from BOTH redirect.ts and sdk.ts async writers.

### Decisive source
```ts
// debug.ts:327-349 — per-client filtering at delivery, not at emission:
const unsubscribe = subscribeToClickEvents((eventData) => {
  if (userId && eventData.userId !== userId) return;
  if (linkId && eventData.linkId !== linkId) return;
  try {
    connection.socket.send(JSON.stringify({ type: 'click_event', data: eventData }));
  } catch (error) { console.error('Failed to send WebSocket message:', error); }
});
connection.socket.on('close', () => unsubscribe());
connection.socket.on('error', (error) => { console.error(...); unsubscribe(); });
```

**Flow:** ingestion writers call emitClickEvent inside their setImmediate blocks (tracking failures already isolated) → every connected WS client's callback runs synchronously on the emitter → filters drop non-matching events per client → send errors caught per-message so one bad socket can't break others; close/error both unsubscribe, preventing emitter leaks.
**Invariant:** The emitter is process-LOCAL state (module singleton): multi-instance deployments need external pub/sub (Redis etc.) for cross-node streaming — this primitive is single-node only; unhandled listener growth is bounded only by clients unsubscribing on disconnect.
**Probe:** per-file line counts: `bash -c "grep -cF 'subscribeToClickEvents' src/lib/event-emitter.ts"` → 1 (:61 definition — the export * barrel is not a literal match); `bash -c "grep -cF 'subscribeToClickEvents' src/routes/debug.ts"` → 2 (:5 import + :327 subscription); direct tests `src/lib/event-emitter.test.ts`: describe('emitClickEvent') multi-listener/exact-data cases + describe('subscribeToClickEvents') "stops receiving events after unsubscribing".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "clickEventEmitter subscribe websocket live", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt in-process emitter + unsubscribe-on-disconnect discipline for dev/live inspection surfaces; adapt transport; swap in Redis pub/sub BEFORE scaling past one instance — do not port this pattern as-is into a multi-node fleet expecting cross-node delivery.
