<!-- capsule-v2 -->
# Pending-run handoff — how does a scheduled launch become exactly one claimed session, with secrets attached after an async await?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do I hand a scheduled run to whichever tab claims it first — single-use, secret-env-complete, expiring unclaimed — across the async gap between launch and browser load?

## create → setEnv/setRedactionValues → claim-once → sweepExpired
**Path/Symbol:** `packages/server/src/automation-run-tracker.ts:AutomationRunTracker` (5–61): `create` (8–18), `claim` (20–25), `setEnv` (30–34), `setRedactionValues` (41–45), `sweepExpired` (47–56).
**Signature:** `create(automation: Automation, now?: number): PendingAutomationRun`; `claim(runId: string): PendingAutomationRun | null`; `sweepExpired(now?: number): PendingAutomationRun[]`.
**Data Shape:** pending run = `{runId, automationId, cwd, runner, createdAt}` + late-bound `env?` / `redactionValues?`. In-memory only — daemon restart loses it by design.

### Decisive source
```ts
// :27-34 — attach AFTER async resolution; no-op once consumed
// Attach resolved secret env to a pending run after the async backend
// resolution settles. No-op if the run was already claimed (single-use) or
// expired — the env is only consumed by `claim()` at WS spawn time.
setEnv(runId: string, env: Record<string, string>): void {
  const run = this.pendingRuns.get(runId);
  if (!run) return;
  run.env = env;
}
```

**Flow:** scheduler emits `due` → composition root `tryLaunch` (index.ts:2708) records a "launched" history row, then `tracker.create(automation)` snapshots cwd+runner NOW (the automation may be edited/deleted before any tab loads) → opens the run tab with `?run=<runId>` → async secret resolution lands via `setEnv`, and `Object.values(env)` as redaction values only when the automation opted into redactOutput → when the run tab's WS upgrades, index.ts:3173 calls `tracker.claim(requestedRunId)`: first claim wins and is DELETED (a reload of the ?run= URL gets a plain shell in the same cwd instead of re-running the command); spawn threads `claimedRun.env` into the PTY and `{automationId, runId, redactValues}` onto the session context → every scheduler tick sweeps runs older than AUTOMATION_PENDING_RUN_EXPIRY_MS (constants.ts:704 = 5min) and flips their still-"launched" history rows to "missed" (index.ts:3466-3476).
**Invariant:** claims are single-use; setEnv/setRedactionValues are silent no-ops once claimed/expired so late-resolving secrets can never leak into a different session; the launch stays synchronous through history-append + tracker-create so the overlap guard (`isRunInFlight`) holds across the secret-resolution await. Secrets live Keychain → daemon memory → PTY env only, never the HTTP surface.
**Probe:** `packages/server/tests/automation-run-tracker.test.ts` — `"claims a run exactly once"` (:34), `"does not attach env to a run that was already claimed"` (:54), `"sweeps only expired runs"` (:63 — boundary at exactly EXPIRY_MS expires).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "AutomationRunTracker claim sweepExpired", limit: 6, detail: "compact" });
// → claim @ automation-run-tracker.ts:20-25, sweepExpired @ :47-56 (+ create/setEnv/setRedactionValues)
```

## Verdict
Adopt the claim-once map with late-binding env attachment verbatim for any "open a UI that eventually executes X" flow; adapt the expiry window to host UX; omit redaction-values threading if output capture doesn't exist in your port. 6 direct tests pin the lifecycle at this commit.
