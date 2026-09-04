<!-- capsule-v2 -->
# WebSocket reconnect ladder — parallel sockets retrying without lockstep herds, stale sockets clobbering fresh ones, or hung handshakes blocking the host

**Source:** OpenHands / All-Hands-AI MIT `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How should a reconnecting WebSocket hook behave when two sockets share one origin and connections hang, flap, or get replaced?

## Connected graph-selected seam
**Path/Symbol:** `src/hooks/use-websocket.ts:useWebSocket` (22–250); `src/utils/websocket-handshake.ts:startHandshakeWatchdog` (17–26); `src/utils/websocket-auth.ts:sendWebSocketAuth` (9–18).
**Signature:** `function useWebSocket(url: string, options?: WebSocketHookOptions): { isConnected, error, socket, sendMessage, isReconnecting, attemptCount, disconnect, reconnect }`.
**Data Shape:** Options carry `queryParams`, `sessionApiKey`, four callbacks, and `reconnect:{enabled,maxAttempts}`. Callbacks are stored in a ref updated per render — identity changes never reconnect.

### Decisive source
```ts
// Reconnect backoff bounds: 1s, 2s, 4s, … capped at 30s.
const RECONNECT_BASE_DELAY_MS = 1_000;
const RECONNECT_MAX_DELAY_MS = 30_000;
// …inside onclose:
// Exponential backoff with up to 30% random jitter so parallel
// sockets (main + planning) don't retry in lockstep and hammer an
// already-struggling server every few seconds forever.
const baseDelay = Math.min(
  RECONNECT_BASE_DELAY_MS * 2 ** (attemptCountRef.current - 1),
  RECONNECT_MAX_DELAY_MS,
);
const delay = baseDelay + Math.random() * baseDelay * 0.3;

// Notify the consumer unless this socket was deliberately replaced by a
// newer one — a replaced socket's close event arrives late and must not
// clobber the replacement's OPEN state in the consumer. Final closes
// (disconnect/unmount, nothing replacing the socket) still notify.
const wasReplaced = wsRef.current !== null && wsRef.current !== ws;
if (!wasReplaced) optionsRef.current?.onClose?.(event);
```
Watchdog: `startHandshakeWatchdog(ws)` closes a socket still `CONNECTING` after 10s — browsers never time out CONNECTING, and Chrome serializes handshakes per host, so one hung handshake blocks every other socket to that origin until settled; cancel it in open/close handlers.

**Flow:** connect → append query params → mark instance allowed-to-reconnect in a WeakSet → start watchdog → onopen cancels watchdog, sends `{"type":"auth","session_api_key":…}` as the first frame, resets attempt count → onclose (non-1000) records error and only then schedules backoff if this exact instance is still allowed and unmount has not set `shouldReconnectRef=false` → `reconnect()` detaches the old instance from the WeakSet before closing and connects fresh → cleanup removes from WeakSet BEFORE `close()` so the close handler cannot schedule another attempt.

**Invariant:** Only the current socket instance may reconnect or notify consumers; teardown flags flip before close, never after; attempt count resets only on successful open; jitter is proportional to base delay so independent sockets decorrelate.

**Probe:** `__tests__/hooks/use-websocket.test.ts` pins open/close/error/reconnect behavior. Companion coverage caveat: `websocket-handshake.ts` has no dedicated unit test (verified absent) — its invariant rests on source comments plus integration usage. RUNNER BLOCK: vitest not executable here; decisive ranges read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "websocket reconnect exponential backoff jitter handshake watchdog", limit: 8 });
// executed this pass -> startHandshakeWatchdog src/utils/websocket-handshake.ts 17-26,
// useWebSocket src/hooks/use-websocket.ts 22-250 (has_more: true)
```

## Verdict
Adopt the per-instance WeakSet gating, options-in-ref stability, pre-close flag flips, ≤30% proportional jitter, and the 10s CONNECTING watchdog. Adapt delays/auth frame shape to your server. Omit the specific planning/main dual-socket pairing (see `conversation-stream-kernel`). Coverage: use-websocket.ts and websocket-auth.ts `no_recorded_issue`; handshake watchdog test gap recorded above.
