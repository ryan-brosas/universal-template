<!-- capsule-v2 -->
# Reconnect ladder + permanence classification — when does a dead session stop retrying, and how do sleep/wake and refreshed tokens bend the rules?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What separates "retry forever within budget" from "close immediately", and which permanent failures are actually conditional?

## One ladder shape, two wire codings, three escape hatches
**Path/Symbol:** `src/cli/transports/WebSocketTransport.ts`: `handleConnectionError` (:397-554), PERMANENT_CLOSE_CODES :42-46, SLEEP_DETECTION_THRESHOLD_MS :36, tick-gap detector :706-735; `src/cli/transports/SSETransport.ts`: `handleConnectionError`/:470-535, PERMANENT_HTTP_CODES :27, liveness :542-559.
**Signature:** both: exp backoff base 1s cap 30s, delay `base ±25%` multiplicative jitter, wall-clock budget `RECONNECT_GIVE_UP_MS = 600_000` → state=closed + onCloseCallback(code).
**Data Shape:** Permanent sets: HTTP {401,403,404}; WS {1002 protocol error/reaped, 4001 expired, 4003 unauthorized}. Escape hatches: (1) 4003 retriable IFF refreshHeaders() returns CHANGED Authorization; (2) `autoReconnect:false` option → straight to closed (caller-owned recovery, e.g. REPL bridge poll loop); (3) sleep/wake detection resets attempts+budget.

### Decisive source
```ts
if (closeCode === 4003 && this.refreshHeaders) {
  const freshHeaders = this.refreshHeaders()
  if (freshHeaders.Authorization !== this.headers.Authorization) { Object.assign(this.headers, freshHeaders); headersRefreshed = true }
}
if (closeCode != null && PERMANENT_CLOSE_CODES.has(closeCode) && !headersRefreshed) {
  this.state = 'closed'; this.onCloseCallback?.(closeCode); return
}
// sleep/wake: gap between reconnect ATTEMPTS >60s ⇒ machine slept ⇒ reset budget
if (now - this.lastReconnectAttemptTime > SLEEP_DETECTION_THRESHOLD_MS) { this.reconnectStartTime = now; this.reconnectAttempts = 0 }
```
```ts
// ping-interval suspension detector: setInterval COALESES missed ticks,
// so a >60s gap between ticks proves process suspension. Don't wait for a
// ping roundtrip to confirm — ws.ping() on a dead socket returns immediately
// with no error (bytes go into the kernel send buffer). Assume dead NOW.
if (gap > SLEEP_DETECTION_THRESHOLD_MS) { this.handleConnectionError(); return }
```

**Flow:** error/close → telemetry (bridge-only, incl. msSinceLastActivity EXCLUDING control frames — proxies don't count ping/pong, so ~300s peaks diagnose Cloudflare RSTs) → doDisconnect (listeners off BEFORE ws.close) → permanent? closed : autoReconnect? ladder-with-jitter-and-budget : closed. Liveness planes stay separate: SSE counts ANY frame incl. keepalive comments (45s window vs server 15s keepalives); WS uses ping/pong (10s) PLUS 5-min keep_alive DATA frames for proxy idle timers (skipped under CLAUDE_CODE_REMOTE where CCR heartbeats own it).
**Invariant:** Budget is WALL-CLOCK (elapsed since first failure), not attempt-count — otherwise slow jitter loops retry forever. A "permanent" code is only truly permanent when token refresh cannot change the verdict. Suspension gaps invalidate backoff state (the deadline didn't elapse; the machine did).
**Probe:** `grep -n "PERMANENT_CLOSE_CODES = new Set" src/cli/transports/WebSocketTransport.ts` (`:42`), `grep -n "closeCode === 4003 && this.refreshHeaders" src/cli/transports/WebSocketTransport.ts` (`:428`), `grep -n "600_000" src/cli/transports/SSETransport.ts src/cli/transports/WebSocketTransport.ts` (`:19`,`:26`), `grep -n "gap > SLEEP_DETECTION_THRESHOLD_MS" src/cli/transports/WebSocketTransport.ts` (`:724`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "handleConnectionError PERMANENT_CLOSE_CODES reconnect give up", limit: 5 });
```

## Verdict
Adopt wall-clock budgets, conditional permanence, and dual sleep detectors. Adapt code sets and liveness windows to your server/proxy stack. Omit tick-gap detection only in environments that cannot suspend mid-session.
