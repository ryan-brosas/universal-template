<!-- capsule-v2 -->
# Status computation ladder — how do four presence states derive from one timestamp?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What is the exact active/idle/away/stuck decision function and its auto-status twin?

## Threshold cascade with work-preservation override
**Path/Symbol:** `lib/status.ts:computeStatus` (:9-35), `STATUS_INDICATORS` (:46-51), `generateAutoStatus` (:53-81); consumers `handlers/coordination/list.ts:formatAgentLine` (:36-82), `whois.ts:formatWhoisOutput` (:65-132).
**Signature:** `computeStatus(lastActivityAt, hasTask, hasReservation, thresholdMs): { status, idleFor? }`.
**Data Shape:** ACTIVE_MS=30s, IDLE_MS=5min, stuck threshold = config.stuckThreshold seconds (default 900) ×1000.

### Decisive source
```ts
if (!hasTask && !hasReservation) {
  return { status: 'away', idleFor: formatDuration(elapsed) };
}
if (elapsed >= thresholdMs) {
  return { status: 'stuck', idleFor: formatDuration(elapsed) };
}
return { status: 'idle', ... };   // long-idle BUT holding a task/reservation stays yellow, not red
```
Auto-status precedence (generateAutoStatus):
```ts
if (sessionAge < 30_000) return 'just arrived';
if (ctx.recentCommit) return 'just shipped';
if (ctx.recentTestRuns >= 3) return 'debugging...';
if (ctx.recentEdits >= 8) return 'on fire 🔥';
```

**Flow:** elapsed <0 or NaN clamps to active (clock skew safety); 30s/5min bands; then the WORK-HOLDING branch: an agent holding a task or reservation can never be 'away' — it becomes 'stuck' only past the stuck threshold, else stays 'idle'. Auto-status is a separate precedence ladder fed by the activity tracker's 60s windows (recentCommit bool, test-run and edit counters) and is suppressed entirely by custom statuses.
**Invariant:** The hasTask/hasReservation inputs change semantics after 5 minutes — porters who compute status from timestamps alone will show workers as away mid-task. `customStatus` latching (set_status flips it true; only rename/new session resets context) means auto-status must check the flag, not overwrite.
**Probe:** direct tests pinned via `grep -n "computeStatus\|generateAutoStatus" tests/*.test.ts tests/swarm/*.test.ts` (pure functions exercised through list/whois suites e.g. `tests/swarm/channels.test.ts`, litmus-statusbar); `grep -c "elapsed < 0" lib/status.ts` (=1); `grep -c "recentTestRuns >= 3" lib/status.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "computeStatus generateAutoStatus STATUS_INDICATORS agentHasTask", limit: 5 });
```

## Verdict
Adopt the four-state cascade including the work-holding override and the auto-status precedence ladder; adapt thresholds/wording; omit emoji indicators in non-TUI ports.
