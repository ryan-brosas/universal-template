<!-- capsule-v2 -->
# Drop-notification dedupe & error-without-close recovery — why does one socket drop fire onClose exactly once, and what heals Node's error-only 5xx hang?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** Phoenix fires socket AND channel close/error hooks for the SAME drop — how do you notify subscribers once per episode, and how do you recover when Node's WebSocket emits `error` with no `close` (leaving Phoenix with no reconnect scheduled)?

## Episode-latched onClose + 100ms grace timer + code-1000 override
**Path/Symbol:** `packages/channels-intelligence/src/realtime-gateway.ts` drop block (:1042-1130): latch `closeFired` (:1052), `notifyClose` (:1054-1066), grace timer (:1073-1092), socket onClose/onError (:1100-1116), channel onClose/onError (:1123-1130), invitation pre-join buffer (:794-820).
**Signature:** `onClose(cb: () => void): void`; constants `ERROR_WITHOUT_CLOSE_GRACE_MS = 100`, `maxPendingInvitations = 1_000`.
**Data Shape:** callbacks fire-and-forget — a throwing callback must not skip later ones nor propagate into Phoenix dispatch.

### Decisive source
```typescript
let closeFired = false;
const notifyClose = (): void => {
  if (closingIntentionally || closeFired) return;   // one shot per drop episode
  closeFired = true;
  for (const cb of closeCallbacks) { try { cb(); } catch {} }
};
socket.onOpen(() => {
  clearErrorWithoutCloseTimer();
  closeFired = false;                               // reset per episode on reopen
});
// Phoenix schedules reconnects ONLY from transport `close`. Node 22's built-in
// WebSocket can emit only `error` on a later HTTP 5xx upgrade, leaving Phoenix
// with no reconnect scheduled. Give paired events a brief window, then cycle:
const armErrorWithoutCloseTimer = (): void => {
  if (closingIntentionally || errorWithoutCloseTimer !== undefined) return;
  errorWithoutCloseTimer = setTimeout(() => {
    errorWithoutCloseTimer = undefined;
    if (closingIntentionally) return;
    socket.disconnect(() => { if (!closingIntentionally) socket.connect(); });
  }, ERROR_WITHOUT_CLOSE_GRACE_MS);
  // ...
};
socket.onClose((event) => {
  clearErrorWithoutCloseTimer();
  notifyClose();
  enterReconnecting();
  // Phoenix treats 1000 as terminal and schedules nothing. For a live managed
  // session only OUR disconnect is terminal:
  if (!closingIntentionally && event?.code === 1000) {
    socket.disconnect(() => { if (!closingIntentionally) socket.connect(); });
  }
});
```

**Flow:** any drop co-fires socket+channel hooks → first hook wins the latch, later duplicates are absorbed → reopen resets the latch so a SECOND distinct drop notifies again → `error` without a paired `close` within 100ms ⇒ cycle the existing socket exactly once (`disconnect` resets Phoenix's pending reconnect timer before `connect`) → clean close with code 1000 is force-cycled too → delivery invitations arriving before control setup completes buffer up to 1,000 and replay to the first handler; overflow before settle fails the connect loudly.
**Invariant:** The latch is per-EPISODE, not global: resetting it in `socket.onOpen` is load-bearing (otherwise a later drop after a heal never notifies). Own-teardown silence (`closingIntentionally` checked first) keeps `disconnect()` from masquerading as an outage.
**Probe:** `packages/channels-intelligence/src/realtime-gateway.test.ts` :306 "fires a registered onClose callback exactly once"; :333 "fires onClose again for a second drop after the socket reopens"; :377 "does not fire onClose when the drop is our own disconnect()"; :568 "recovers when a reconnect attempt emits error without close"; :275 "delivers an invitation sent before the control join reply". Deterministic anchor `grep -n "closeFired" packages/channels-intelligence/src/realtime-gateway.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "notifyClose closeFired armErrorWithoutCloseTimer pendingInvitations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt episode-latched notifications and the grace-window socket cycle for any auto-reconnecting socket wrapper. Adapt the grace constant to your transport's event pairing. Omit the invitation buffer at your peril — gateways wake faster than control setup completes.
