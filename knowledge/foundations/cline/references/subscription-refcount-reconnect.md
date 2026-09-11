<!-- capsule-v2 -->
# Subscription refcounts + reconnect ladder — level-triggered counts, edge-triggered wire frames

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How does a client keep N independent listeners per session over one socket, survive drops with backoff, and restore subscriptions after reconnect?

## refcount map drives subscribe/unsubscribe edges; backoff+jitter; re-register all keys on open
**Path/Symbol:** `sdk/packages/core/src/hub/client/index.ts:356-480` (`connect`), `641-661` (`scheduleReconnect`), `663-693` (`reconnectSubscribedTransport`), `770-790` (`adjustSubscriptionCount`); recovery guard `restartLocalHubIfIdleAfterStartupTimeout` (1192-1224).
**Signature:** `adjustSubscriptionCount(sessionId | undefined, delta: 1 | -1)`; `scheduleReconnect()`; `reconnectSubscribedTransport()`; `connect() → Promise<void>`.
**Data Shape:** `subscriptionCounts: Map<subscriptionKey, count>`; delays `HUB_RECONNECT_INITIAL_DELAY_MS * 2 ** attempt` capped at max, jittered in `(1-ratio, 1]` band; auth via WS subprotocol `${HUB_AUTH_PROTOCOL_PREFIX}${authToken}`.

### Decisive source
```ts
// LEVEL: counts are bookkeeping; WIRE: frames fire only on 0<->1 edges
const next = (this.subscriptionCounts.get(key) ?? 0) + delta;
if (next <= 0) {
    this.subscriptionCounts.delete(key);
    if (!this.hasActiveSubscriptions()) this.clearReconnectTimer();   // nothing to keep alive
    if (delta < 0 && this.socket?.readyState === 1) this.sendSubscriptionFrame("stream.unsubscribe", sessionId);
    return;
}
this.subscriptionCounts.set(key, next);
if (delta > 0 && next === 1 && this.socket?.readyState === 1) this.sendSubscriptionFrame("stream.subscribe", sessionId);

// BACKOFF: exponential with jitter band; single timer; gated on live subscriptions
const delayMs = Math.min(HUB_RECONNECT_INITIAL_DELAY_MS * 2 ** this.reconnectAttempt, HUB_RECONNECT_MAX_DELAY_MS);
const jitteredDelayMs = Math.round(delayMs * (1 - HUB_RECONNECT_JITTER_RATIO) + Math.random() * delayMs * HUB_RECONNECT_JITTER_RATIO);

// RECONNECT: recoverable local URL gets full rediscovery (ensureCompatibleLocalHubUrl), else plain retry
} catch {
    if (!isRecoverableLocalHubUrl(this.currentUrl)) { this.reconnectAttempt += 1; this.scheduleReconnect(); return; }
    const recoveredUrl = await ensureCompatibleLocalHubUrl({...}).catch(() => undefined);
    ...
}

// POST-CLOSE identity guard + pending-reply flush (inside connect's close listener):
socket.addEventListener("close", (event) => {
    if (this.socket !== socket) return;              // stale close from a retired socket is ignored
    ...
    for (const pending of this.pendingReplies.values()) pending.reject(this.lastCloseError);
    this.pendingReplies.clear();
    if (!this.closedByClient && this.hasActiveSubscriptions()) this.scheduleReconnect();
});
// AFTER OPEN: handshake then re-subscribe EVERY key (no wildcard sentinel):
await this.command("client.register", {... satisfies HubClientRegistration}); this.registered = true;
for (const key of this.subscriptionCounts.keys()) this.sendSubscriptionFrame("stream.subscribe", this.subscriptionSessionIdFromKey(key));
this.reconnectAttempt = 0;
```

**Flow:** listeners inc/dec a per-session refcount map; wire frames fire only at 0→1 (subscribe) and →0 (unsubscribe) crossings while the socket is OPEN; counts reaching zero stops the reconnect timer (no ghost keepalive). Close path: stale sockets ignored by identity check, all pending replies rejected+cleared, reconnect scheduled only when the client didn't close AND subscriptions remain. Backoff doubles per failed attempt up to cap within a jitter window, resets to 0 on any successful connect. Recoverable local URLs get full rediscovery through the daemon ensure ladder before falling back to plain retries; explicit endpoints never auto-rediscover. A hub that never came up can be recovered by `restartLocalHubIfIdleAfterStartupTimeout`: only for recoverable URLs, discovery must match the normalized URL, hub must have NO active sessions, graceful stop ⇒ wait retire ⇒ clear discovery ⇒ re-ensure — every unmet guard returns undefined.
**Invariant:** Counts and wire state stay decoupled (level vs edge); a reconnecting client neither loses listener registrations nor spams per-listener frames; stale socket events cannot corrupt current-socket state; reconnect machinery exists only while something is subscribed.
**Probe:** `grep -cF 'const next = (this.subscriptionCounts.get(key) ?? 0) + delta;' sdk/packages/core/src/hub/client/index.ts` → 1; `grep -cF 'HUB_RECONNECT_INITIAL_DELAY_MS * 2 ** this.reconnectAttempt,' ...` → 1; `grep -cF 'for (const key of this.subscriptionCounts.keys()) {' ...` → 1; `grep -cF 'if (this.socket !== socket) {' ...` → 1. Direct tests: `client/index.test.ts` ("re-subscribes global listeners without sending the wildcard sentinel", "ignores stale close events from retired sockets", "does not rediscover explicit local hub endpoints", "does not restart explicit local endpoints after startup timeout").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "adjustSubscriptionCount scheduleReconnect hasActiveSubscriptions stream.subscribe", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt level-counts/edge-frames refcounting, identity-guarded close handling, jittered exponential backoff gated on live subscriptions, and post-open re-registration of every key. Adapt frame names, registration payload, backoff constants. Omit Cline's hub URL policy specifics. Runner-BLOCKED here; probes green.
