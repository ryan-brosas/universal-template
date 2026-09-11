<!-- capsule-v2 -->
# Bridge REPL poll loop — heartbeat/poll composition, suspension detection, env-loss ladder

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does a single-session poll loop stay alive across laptop sleep, JWT expiry, and server-side environment reaping without dead windows?

## Path/Symbol
**Path/Symbol:** `src/bridge/replBridge.ts` — `startWorkPollLoop` (:1851-2398): at-capacity heartbeat composition (:1971-2134), merged backoff sleep with overrun detector (:2096-2131, >60s overrun ⇒ suspension), read-and-clear `suspensionDetected` fast-cycle (:1930-1936,:1976-1978), poll-404 env-loss handling (:2188-2270, stale-credential check :2206-2217), fatal classification (:2272-2304), heartbeat-before-backoff (:2371-2390); constants POLL_ERROR_* (:244-246: 2s initial, 60s cap, 15min give-up).
**Signature:** `startWorkPollLoop(pollOpts): Promise<void>` — opts include `isAtCapacity` (REPL: `transport !== null`, even mid-auto-reconnect), `getHeartbeatInfo`, `onHeartbeatFatal`, `onEnvironmentLost`.
**Data Shape:** `environmentRecreations` resets ONLY on successful poll; `reclaim_older_than_ms` threaded into every poll for stale-work pickup.

### Decisive source
```ts
// Process-suspension detector. A setTimeout overshooting its
// deadline by 60s means the process was suspended (laptop lid,
// SIGSTOP, VM pause) — even a pathological GC pause is seconds,
// not minutes. Early aborts (wakePollLoop → cap.signal) produce
// overrun < 0 and fall through.
const overrun = Date.now() - sleepStart - sleepMs
if (overrun > 60_000) { ...; suspensionDetected = true }
...
// Read-and-clear: after a detected suspension, skip the at-capacity
// branch exactly once. The pollForWork above already refreshed the
// server's BRIDGE_LAST_POLL_TTL; this fast cycle gives any
// re-dispatched work item a chance to land before we go back under.
```

**Flow:** work-null + transport-present ⇒ at-capacity: if heartbeat enabled, inner loop heartbeats on its interval while a poll deadline composes (break out to poll at atCapMs — heartbeat and poll COMPOSE rather than suppress); heartbeat BridgeFatalError ⇒ onHeartbeatFatal clears work state so isAtCapacity flips false and the next outer iteration fast-polls (without the hook: backoff, else tight loop). The merged sleep measures overrun; >60s ⇒ process was suspended ⇒ one forced fast-poll cycle before going back under (the WS ping detector covers shorter suspensions; this is the backstop when it isn't running). Error path: 404 = env gone (poll endpoint's only path param — no-work is 200/null) → stale-credential guard skips recovery if a concurrent reconnect already swapped creds → re-register ≤3 → give-up. Backoff sleeps heartbeat first so /poll outages don't kill the 300s lease.

**Invariant:** (1) isAtCapacity must be conservative (transport !== null, not isConnectedStatus) or the loop sleeps 10min against a dead socket. (2) Heartbeat-fatal MUST clear work state synchronously in the callback — leaving it set causes the ~25-min dead window documented in the docstring. (3) Suspension detection belongs on the SHARED sleep path (legacy + heartbeat-backoff both reach it). (4) Only a successful poll resets environmentRecreations — recovery success proves intent, not health.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "process was suspended" src/bridge/replBridge.ts` (:2115-2116); `grep -n "~25-min dead window" src/bridge/replBridge.ts` (:1035); `grep -n "unambiguously means env-gone" src/bridge/replBridge.ts` (:2196-2200); graph resolves `locoagent.src.bridge.replBridge.startWorkPollLoop` :1851-2398 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "startWorkPollLoop onHeartbeatFatal suspensionDetected environmentRecreations reclaim_older_than_ms", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the composition rules (heartbeat+poll deadline, suspension overrun, heartbeat-before-backoff) wholesale for any long-lived polling client. Adapt intervals to your TTLs; omit the multisession variants covered in bridge-poll-loop-fsm.
