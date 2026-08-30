<!-- capsule-v2 -->
# Caffeinate automatic detector — when does "automatic" keep-awake actually hold the machine awake?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do I decide whether a recognized foreground program should keep the machine awake without ever polling on a timer?

## Event-driven two-source detection (hook name short-circuit → ps walk)
**Path/Symbol:** `packages/server/src/caffeinate-automatic-detector.ts:CaffeinateAutomaticDetector.pollAuto` (203–291) + `.poke` (119–127) + `.noteOutputActivity` (133–161).
**Signature:** `poll(): Promise<void>` (test entry for the private `pollAuto`); `poke(): void`; `noteOutputActivity(): void`.
**Data Shape:** Injected getters only — `listSessionPids()`, `snapshotProcesses()`, trigger set = fixed defaults ∪ user commands (lowercased), plus optional `hasRecentOutput(pids, withinMs)` / `hasPeerClient()` / `foregroundNames(): Map<shellPid, programName>`. Derived state: `autoActive`/`autoTrigger`/`autoPeerActive`.

### Decisive source
```ts
// pollAuto :203-235 — hook-name short-circuit BEFORE any ps snapshot
programTrigger = this.hookTriggerFor(pids, triggers);
if (programTrigger === null) {
  const snapshot = await this.snapshotProcesses();
  programTrigger = anySessionRunsTrigger(pids, snapshot, triggers);
}
if (programTrigger) {
  if (!this.getActivityGate()) { programActive = true; }
  else if (this.checkRecentOutput) {
    programActive = this.checkRecentOutput(pids, CAFFEINATE_ACTIVITY_GATE_DEBOUNCE_MS);
  }
}
```

**Flow:** event (foreground change / session connect-disconnect / mode-command change) → debounced `poke` (150ms one-shot, coalesces a burst into ONE snapshot; fires once, does not repeat) → `pollAuto`: hook-name match against triggers (walk-free engage — test proves `snapshotProcesses` NOT called) else BFS `ps` walk under session shells → activity gate: gated programs additionally require recent output within `CAFFEINATE_ACTIVITY_GATE_DEBOUNCE_MS` (5_000) → peer keep-awake (`getPeerKeepAwake() && hasPeerClient()`) holds INDEPENDENTLY of program detection and bypasses the output gate → silence-release timer arms ONLY while a gated program is the SOLE reason active (`programActive && !peerActive`); cleared when a peer joins.
**Invariant:** never poll on a timer — every re-check is event-driven; the trailing-edge timer exists only to release after silence, and it must NOT arm while a peer holds (a stale trailing edge would convert the design back into timer polling). Broadcast `change` on ANY movement of `autoActive|autoTrigger|autoPeerActive` — trigger identity can flip while caffeinate stays continuously active and a UI highlighting rows would go stale otherwise.
**Probe:** `packages/server/tests/caffeinate-manager.test.ts::"engages from the shell-hook foreground name without a ps snapshot"` (:120 — asserts `snapshotProcesses` not called), `"falls back to the ps walk when the hook name is not a trigger"` (:138), `"does not arm the activity-gate silence timer while a peer holds"` (:344), `"broadcasts when the trigger identity changes while caffeinate stays active"` (:364).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "pollAuto", limit: 5, fields: ["signature", "name", "file"] });
// → CaffeinateAutomaticDetector.pollAuto @ caffeinate-automatic-detector.ts:203-291
await mcp.codebase_memory.search_graph({ project: "localterm", query: "noteOutputActivity", limit: 5 });
```

## Verdict
Adopt the poke→poll serialization ladder (`polling` + `pollQueued` so exactly one queued re-check runs with latest-state-wins) and the sole-reason timer-arming rule; adapt the OSC 7777 fg;<token> hook plumbing to whatever foreground-report channel the host has (the detector consumes a plain `Map<pid,name>`); omit macOS/Linux-specific trigger defaults if porting outside a coding-agent terminal. Direct tests pin all four branches at this commit; no coverage caveat beyond index.ts parse_partial (irrelevant here).
