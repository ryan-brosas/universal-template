<!-- capsule-v2 -->
# Resource-subscription fan-out — how do you track per-URI subscribers across sessions and drive `notifications/resources/updated` on an interval?

**Source:** modelcontextprotocol/servers MIT `main@76d64c822f5125032f89eb71dbdb94e42b434821` (src/everything); Codebase Memory `servers`. **Question:** What is the subscribe/unsubscribe data structure, the stdio sessionId edge case, and the dead-subscriber reaping trick inside the notification loop?

## URI→Set(sessionId) map + per-session interval, undefined = stdio
**Path/Symbol:** `src/everything/resources/subscriptions.ts` (whole file, 171L: state maps :7–15; handlers :36–97; update loop :111–129; interval lifecycle :139–171). Low-level SDK surface: `server.server.setRequestHandler(SubscribeRequestSchema | UnsubscribeRequestSchema)` — bypasses McpServer sugar for raw protocol methods.

**Signature:** two module maps: `subscriptions: Map<string /*uri*/, Set<string|undefined> /*sessionIds*/>` and `subsUpdateIntervals: Map<string|undefined, NodeJS.Timeout|undefined>`. Handlers `(request, extra) => {}` read `extra.sessionId` — **undefined for stdio**, which is a legitimate key everywhere (:44–45, :75–76 comments).

**Data Shape:** subscribe ⇒ `{}` (empty result ack); notification ⇒ `{ method: "notifications/resources/updated", params: { uri } }`.

### Decisive source
```ts
// src/everything/resources/subscriptions.ts:111-153 (condensed)
const sendSimulatedResourceUpdates = async (server, sessionId) => {
  for (const uri of subscriptions.keys()) {
    const subscribers = subscriptions.get(uri);
    if (subscribers.has(sessionId)) {
      await server.server.notification({          // push to THIS session's transport
        method: "notifications/resources/updated",
        params: { uri },
      });
    } else {
      subscribers.delete(sessionId);              // ← reap: subscriber has disconnected
    }
  }
};

export const beginSimulatedResourceUpdates = (server, sessionId) => {
  if (!subsUpdateIntervals.has(sessionId)) {      // idempotent: never double-interval
    sendSimulatedResourceUpdates(server, sessionId);   // fire once immediately
    subsUpdateIntervals.set(sessionId,
      setInterval(() => sendSimulatedResourceUpdates(server, sessionId), 5000));
  }
};
```

**Flow:** client calls `resources/subscribe {uri}` → handler logs via `sendLoggingMessage(..., sessionId)` (session-routed logging), adds sessionId to the URI's Set → a tool later calls `beginSimulatedResourceUpdates(server, sessionId)` → immediate first fan-out, then every 5s each subscribed URI notifies that session → unsubscribe removes just that session from the Set; `stopSimulatedResourceUpdates(sessionId)` clears the interval. The iteration itself REAPS: when the loop probes a URI the session is NOT subscribed to, it deletes the sessionId from that Set as "subscriber has disconnected" (:126).

**Invariant:** one interval PER SESSION (guarded by map presence — double-begin is a no-op), while subscription membership is per-URI-per-session Sets; `undefined` is a valid session key (stdio has no id) so porters must not filter falsy keys. Notification delivery is best-effort per transport — the reference tolerates disconnected subscribers by lazily deleting them during sends rather than tracking connection liveness separately.

**Probe:** `src/everything/__tests__/resources.test.ts:284–327` — `setSubscriptionHandlers` pins exactly TWO `setRequestHandler` registrations (:286–299); lifecycle test starts updates for BOTH a string sessionId AND `undefined`, stops them plus a never-started id without throwing (:301–326).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "setSubscriptionHandlers SubscribeRequestSchema notifications resources updated", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt URI→Set(sessionId) subscription tracking with per-session notification intervals, undefined-as-stdio-key handling, lazy dead-subscriber reaping inside the send loop, and empty-result acks; adapt the 5s cadence to your change rate; omit connection-liveness bookkeeping (the loop reaps instead). Note: this mines the LEGACY per-resource subscribe API — the modern era replaces it with `subscriptions/listen` (spec-side `subscriptions.md` capsule).
