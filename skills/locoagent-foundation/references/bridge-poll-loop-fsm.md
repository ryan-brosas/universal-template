<!-- capsule-v2 -->
# Standalone poll-loop FSM — ack ordering, stale-work dedup, heartbeat composition, shutdown ladder

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does a multi-session work-poll loop acknowledge, spawn, throttle, and shut down without losing work or tight-looping?

## Path/Symbol
**Path/Symbol:** `src/bridge/bridgeMain.ts` — `runBridgeLoop` (:141-1580), heartbeat aggregation `heartbeatActiveWorkItems` (:202-270), empty-work branch (:637-746), `atCapacityBeforeSwitch` + completedWorkIds skip (:753-784), secret-decode failure (:788-830), `ackWork` deferral comment (:832-850), case 'session' existing-handle token refresh (:869-896) + at-capacity break (:891-896) + v2 register retry (:914-958) + worktree isolation (:969-1015), post-switch capacity sleep (:1220-1235), dual-track backoff with sleep detection (:1270-1399, threshold = 2×connCap :107-109), graceful shutdown (:1417-1579: SIGTERM→30s grace→SIGKILL :1445-1463, snapshot-before-kill maps :1426-1443, pendingCleanups drain :1511-1513, resumable-shutdown early return :1525-1538, pointer clear :1576-1577); helpers `stopWorkWithRetry` (1s/2s/4s ×3 :1627-1676), `onSessionTimeout` (:1678-1697).
**Signature:** `runBridgeLoop(config, environmentId, environmentSecret, api, spawner, logger, signal, backoffConfig?, initialSessionId?, getAccessToken?)`.
**Data Shape:** per-session Maps (`activeSessions/sessionStartTimes/sessionWorkIds/sessionIngressTokens/sessionCompatIds/sessionTimers/sessionWorktrees`) — compat IDs and ingress JWTs cached SEPARATELY from raw session IDs and refresh-overwritten handle tokens.

### Decisive source
```ts
// Explicitly acknowledge after committing to handle the work — NOT
// before. The at-capacity guard inside case 'session' can break
// without spawning; acking there would permanently lose the work.
// Ack failures are non-fatal: server re-delivers, and existingHandle
// / completedWorkIds paths handle the dedup.
...
if (completedWorkIds.has(work.id)) {
  // ... persistent stale redeliveries would tight-loop at poll-request
  // speed (the !work branch above is the only sleep, and work != null skips it)
```

**Flow:** poll → null? capacity branch composes heartbeat-with-poll via deadline (heartbeat loops WITHOUT polling; breaks out on poll-due/auth-fail/capacity-wake/config-disable; each exit reason telemetry-tagged) → work? skip if in completedWorkIds (server re-delivers before processing stop; the sleep here is mandatory or stale redeliveries tight-loop) → decode secret (failure ⇒ OAuth stopWork poison-pill + capacity-respecting sleep) → **ack AFTER commit decision** → existing session? deliver fresh JWT to child via updateAccessToken + re-schedule refresh → new? v2 registers epoch (1 retry) else v1 ws URL → optional worktree per spawnMode ('worktree' isolates; pre-created initial session exempted) → spawn with timeout watchdog + token-refresh schedule → done-callback: timeout-killed interrupts are RECLASSIFIED 'failed' so stopWork/archive still run; multi-session archives (idempotent 409) and keeps looping, single-session aborts loop for teardown. Shutdown ladder: kill all → race 30s grace → forceKill stragglers → clear timers → snapshot-clear worktrees → parallel stopWork(force=true) → await pendingCleanups → resume-path leaves env+session alive (backend GCs via 4h TTL; deregister would make the printed --session-id hint a lie) → archive-all → deregister → clear pointer.

**Invariant:** (1) Ack only after the spawn-commit point; acking then failing to spawn permanently loses the item. (2) Every continue path that skips the !work sleep must sleep itself — three separate sites enforce this. (3) Sleep/wake detection resets error budgets when gap >2× backoff cap, else laptop-lid sleeps burn the give-up budget invisibly. (4) Heartbeat before EVERY backoff sleep when enabled — a poll_due exit leaves a healthy lease exposed to the backoff path. (5) Snapshot every Map before awaits that trigger done-callbacks which mutate them.

**Probe:** coverage caveat — no upstream unit tests (tests/=shell scripts). Deterministic pins: `grep -nF 'would permanently lose the work' src/bridge/bridgeMain.ts` (:834); `grep -n "Detected system sleep" src/bridge/bridgeMain.ts` (:1281,:1347); `grep -n "printed resume command a lie" src/bridge/bridgeMain.ts` (:1519); graph resolves `locoagent.src.bridge.bridgeMain.runBridgeLoop` :141-1580 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "runBridgeLoop heartbeatActiveWorkItems stopWorkWithRetry completedWorkIds onSessionTimeout", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the FSM skeleton wholesale for any supervisor spawning children from polled jobs. Adapt spawn modes/backoff numbers; omit the worktree plane by pinning one mode. Porting trap: acking before the capacity guard, or letting a stale redelivery skip the throttle sleep.
