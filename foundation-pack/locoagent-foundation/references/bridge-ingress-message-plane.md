<!-- capsule-v2 -->
# Ingress message plane — echo dedup, control-request liveness, and the BoundedUUIDSet ring

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does an ingress stream route echoes vs re-deliveries vs server control requests without duplicating prompts or hanging the connection?

## Path/Symbol
**Path/Symbol:** `src/bridge/bridgeMessaging.ts` — type guards (:36-70), `isEligibleBridgeMessage` (:77-88), `extractTitleText` (:103-122), `handleIngressMessage` (:132-208), `handleServerControlRequest` (:243-391, outbound-only error :231-232), `makeResultMessage` (:399-416), `BoundedUUIDSet` (:429-461).
**Signature:** `handleIngressMessage(data, recentPostedUUIDs, recentInboundUUIDs, onInboundMessage, onPermissionResponse?, onControlRequest?)`; `BoundedUUIDSet(capacity)` with O(capacity) FIFO eviction.
**Data Shape:** TWO dedup sets: `recentPostedUUIDs` (echoes of what we sent) and `recentInboundUUIDs` (re-delivered inbound we already forwarded) — conflating them breaks one direction of dedup.

### Decisive source
```ts
// control_request from the server (initialize, set_model, can_use_tool).
// Must respond promptly or the server kills the WS (~10-14s timeout).
...
default:
  // Unknown subtype — respond with error so the server doesn't
  // hang waiting for a reply that never comes.
  response = { type: 'control_response', response: {
    subtype: 'error', request_id: request.request_id,
    error: `REPL bridge does not handle control_request subtype: ...` } }
```

**Flow:** parse → normalizeControlMessageKeys → control_response FIRST (not an SDKMessage — checked before the guard) → control_request next → SDKMessage guard → UUID checks: posted-set hit ⇒ ignore echo; inbound-set hit ⇒ ignore re-delivery (defensive backstop for seq-num negotiation failures) → only `type==='user'` forwards (everything else is internal REPL chatter; virtual REPL-inner messages excluded at eligibility). Control ladder: initialize replies minimal capabilities (server kills the WS otherwise); set_permission_mode converts an ABSENT callback into an explicit ERROR response rather than silent false-success ("success would lie to the client"); outbound-only mode errors every mutable subtype but STILL answers initialize. Result message: fabricated zero-cost `SDKResultSuccess` written before archive so the server triggers archival.

**Invariant:** (1) Every request subtype — including unknown ones — must get a response within ~10-14s or the server drops the connection; the default branch is load-bearing. (2) Echo dedup and re-delivery dedup are separate sets seeded differently (echo set pre-seeded with initial-flush UUIDs). (3) Unhandled callback ≠ success: any context that cannot honor a request must return subtype:'error'. (4) Ring-buffer dedup is a SAFETY NET behind primary ordering (hook index / seq numbers) — sized 2000 to cover realistic echo windows, evicting oldest-first.

**Probe:** coverage caveat — no upstream unit tests for this file. Deterministic pins: `grep -n "10-14s timeout" src/bridge/bridgeMessaging.ts` (:152 and :238); `grep -n "success would lie" src/bridge/bridgeMessaging.ts` (:334); `grep -n "FIFO-bounded set backed by a circular buffer" src/bridge/bridgeMessaging.ts` (:420-421); graph resolves all five `BoundedUUIDSet.*` members :435-460 line-exact.

## Response-side worker-status pushes (v2 only; reconciled from a parallel lane's unwired capsule)
**Path/Symbol:** `src/bridge/remoteBridgeCore.ts` — writeMessages push (:807-809), drainFlushGate push (:615-617), flushHistory pre-cap check (:645-653), sendControlRequest/Response/CancelRequest drops + pushes (:824-872), sendResult idle push (:873-881).
```ts
// v2 does not derive worker_status from events server-side (unlike v1
// session-ingress session_status_updater.go). Push it from here so the
// CCR web session list shows Running instead of stuck on Idle.
if (filtered.some(m => m.type === 'user')) transport.reportState('running')
...
if (authRecoveryInFlight) return   // control writes DROP during 401 recovery
```
**Invariant:** (1) v2's claude.ai session list ONLY moves when the client pushes `reportState`: `requires_action` when a can_use_tool control_request goes out, `running` on permission resolution/cancel/user-message batches (CCRClient dedupes consecutive same-state), `idle` on result. (2) flushHistory checks the trailing message type against ELIGIBLE (pre-cap), not capped — the cap may truncate to a user message even when the actual trailing message is assistant. (3) All four control-plane sends drop while `authRecoveryInFlight` rather than half-writing into a dying uploader. Pins: `grep -n "does not derive worker_status" src/bridge/remoteBridgeCore.ts` (:802-803); `grep -n "requires_action" src/bridge/remoteBridgeCore.ts` (:833); `grep -n "Check eligible (pre-" src/bridge/remoteBridgeCore.ts` (:650).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "handleIngressMessage handleServerControlRequest isEligibleBridgeMessage BoundedUUIDSet makeResultMessage", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt whole for any bidirectional session stream: dual-set dedup + always-answer control semantics + bounded rings are directly portable. Adapt the capability payload of initialize; omit extractTitleText if titles are server-side.
