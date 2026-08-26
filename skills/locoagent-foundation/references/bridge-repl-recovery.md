<!-- capsule-v2 -->
# REPL bridge env-loss recovery — two-strategy reconnect with reentrancy and poll-race deferral

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When the server reaps your environment mid-session, how do you recover the session — or cleanly fall back to a fresh one — without racing the poll loop?

## Path/Symbol
**Path/Symbol:** `src/bridge/replBridge.ts` — `reconnectEnvironmentWithSession` (:605-615, promise-reentrancy guard), `doReconnect` (:617-836, MAX_ENVIRONMENT_RECREATIONS=3), `tryReconnectInPlace` (:381-419), `handleTransportPermanentClose` (:887-966), `onHeartbeatFatal` (:1038-1069), seq-num carry rules (`lastTransportSequenceNum`, max() capture :897-903/:1174-1181; reset-on-session-swap :805).
**Signature:** `reconnectEnvironmentWithSession(): Promise<boolean>` — concurrent callers share one in-flight promise.
**Data Shape:** mutable `currentSessionId/environmentId/environmentSecret` closure state + `v2Generation` counter invalidating in-flight handshakes.

### Decisive source
```ts
if (currentWorkId) {
  const workIdBeingCleared = currentWorkId
  await api.stopWork(environmentId, workIdBeingCleared, false).catch(() => {})
  // When doReconnect runs concurrently with the poll loop (ws_closed
  // handler case — void-called ...), onWorkReceived can fire during the
  // stopWork await and set a fresh currentWorkId. If it did, the poll loop
  // has already recovered on its own — defer to it rather than proceeding
  // to archiveSession, which would destroy the session its new transport
  // is connected to.
  if (currentWorkId !== workIdBeingCleared) { ...return true }
```

**Flow:** trigger sites: poll 404 (onEnvironmentLost — awaited), ws_closed non-1000 (~98% of ws_closed never recover via poll alone — BQ 2026-03-12), heartbeat fatal. doReconnect: close transport capturing seq via **max()** (an early-dead transport must not reset a high mark) → wakePollLoop → flushGate.drop → stopWork(force=false) with the work-ID-swap race check after EVERY await → re-register with reuseEnvironmentId (cleared before any subsequent await so a stale value can't poison a second run) → Strategy 1: same env returned ⇒ reconnect-in-place (session ID, phone URL, flushed-history set all preserved) → Strategy 2: archive old, create fresh, then reset session-scoped state IMMEDIATELY (seq=0, inbound dedup cleared, title latch reset) BEFORE awaits — carrying a seq across a session swap silently drops every event in the gap. Four abort-check bailouts keep teardown safe; failure-with-fresh-env explicitly tears down (else the loop polls a sessionless env forever).

**Invariant:** (1) After any await inside recovery, re-check: abort signal, currentWorkId identity, transport !== null — the poll loop recovers asynchronously and recovery must defer to it. (2) environmentRecreations resets ONLY on successful POLL, not on onEnvironmentLost success — otherwise oscillating envs never hit the limit-3 guard. (3) SSE seq numbers are session-scoped: carry across transport swaps within a session, zero across sessions. (4) Promise-based reentrancy: two simultaneous close events share one recovery.

**Probe:** coverage caveat — no upstream unit tests for this path. Deterministic pins: `grep -n "defer to it" src/bridge/replBridge.ts` (:666); `grep -n "defeats it entirely" src/bridge/replBridge.ts` (:797); `grep -n "not lifetime total" src/bridge/replBridge.ts` (:831); graph resolves `locoagent.src.bridge.replBridge.startWorkPollLoop` :1851-2398 and initBridgeCore :260-1839 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "reconnectEnvironmentWithSession tryReconnectInPlace handleTransportPermanentClose v2Generation", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the two-strategy ladder + post-await re-check discipline wholesale for any client of a TTL-managed remote resource. Adapt strategy 1 to your reattach API; omit nothing else — every check here is pinned to an observed production failure.
