<!-- capsule-v2 -->
# Transport-exit supervision — how do you distinguish "child died at boot, retry" from "transport died mid-run, fail", and how does the error text become the retry classifier?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** after a transport reports dead, what exact sequence of grace windows, log summaries, retry gates, and error-string protocols turns the death into a settled outcome?

## Sustained-dead window → laundered error string → zero-progress retry gate
**Path/Symbol:** `src/agents/manager.ts`: `TRANSPORT_EXIT_GRACE_MS = 1_000` (:76), `TRANSPORT_EXITED_WITHOUT_RESULT_PREFIX` (:154) + matcher (:156-157), monitor liveness arm (:1109-1131), `#waitForTransportExit` (:982-989), `#retryStartup` (:991-1025), deadline expiry (:1046). Direct tests: `tests/agent-manager.test.ts:280` (boot-failure retry), :298 (no retry on deterministic failure), :316/:335 (transport-death retry then give-up), `tests/worker-e2e.test.ts:295-326` (abort ≠ exited-without-result; crash mid-stream = terminal failure).
**Signature:** `#retryStartup(managed, record, deadline): Promise<boolean>`; `transportExitedWithoutResult(error): boolean`.

### Decisive source
```ts
// Monitor: a single dead poll means nothing — the dead state must PERSIST
const alive = await managed.transport.isAlive();
if (!alive) {
  firstObservedDeadAt ??= livenessCheckedAt;
  if (livenessCheckedAt - firstObservedDeadAt >= TRANSPORT_EXIT_GRACE_MS) {   // 1s
    const logSummary = summarizeRunLog(managed.runDirectory, 8);              // last 8 lines
    const failed = failedRecord(managed, "failed",
      logSummary ? `Agent transport exited without a result; last run log: ${logSummary}`
                 : "Agent transport exited without a result");
    if (await this.#retryStartup(managed, failed, deadline)) {
      managed.lastRetriedTransportFailure = failed;
      continue;                                                               // relaunch
    }
    writeRecord(managed.statusFile, failed);
    this.#settle(managed, failed);
    return;
  }
} else { firstObservedDeadAt = undefined; }        // any alive poll RESETS the window
// Retry gate: ONLY pre-first-turn failures with literally ZERO progress
record.status !== "failed" || !(
  (managed.runner === "pi" && retryablePiStartupError(record.error)) ||
  transportExitedWithoutResult(record.error)
) || record.turns !== 0 || record.toolCalls !== 0 ||
  record.usage.input !== 0 /* …every counter must be 0… */ → no retry
```

**Flow:** poll cadence per transport (`livenessPollIntervalMs ?? 250ms`) → sustained-dead ≥1s → synthesize the failed record with an ERROR STRING that embeds the run-log tail (`summarizeRunLog(…, 8)`) for operator diagnosis → classify: boot-window failures matching `retryablePiStartupError` (pi runner) OR carrying the `"Agent transport exited without a result"` prefix WITH all-zero progress counters are retried up to 3 attempts at exponential backoff (base 500ms × 2^(attempt−1)), relaunching via the SAME stored `launch` descriptor after wiping status/lifecycle files → otherwise settle terminal. `#waitForTransportExit` gives the dying transport 7×grace to flush its own records before the manager overwrites them. Deadline expiry stops the transport FIRST, then prefers a real terminal record over synthesizing `timed_out`.
**Invariant:** the error string is a PROTOCOL, not prose — `#retryStartup` re-parses it via `startsWith("Agent transport exited without a result")`, so any refactor that renames the message silently breaks retry classification (worker.ts:207 comment documents the same coupling); retry eligibility requires zero progress in EVERY counter (turns/toolCalls/usage×4) because anything that touched tokens is deterministic and final; one dead poll never kills a run (transient CLI blips reset `firstObservedDeadAt`).
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/pi-ecosystem/pi-fabric && grep -c "TRANSPORT_EXITED_WITHOUT_RESULT_PREFIX" src/agents/manager.ts'` → 2 (:154 definition + :157 matcher — emitters use the LITERAL string); `grep -c "Agent transport exited without a result" src/agents/manager.ts` → 3 (:1124 bare literal, :1123 prefixed log-summary variant, plus the :154 constant definition line carrying the same text); `grep -n "TRANSPORT_EXIT_GRACE_MS \* 7" src/agents/manager.ts | wc -l` → 1 (:983); `grep -n "firstObservedDeadAt >= TRANSPORT_EXIT_GRACE_MS" src/agents/manager.ts | wc -l` → 1 (:1117); tests pin both outcomes: `tests/worker-e2e.test.ts:295` "aborts a hanging run as stopped, not exited-without-a-result" vs :314 "reports a terminal failure (not exited-without-a-result) when the worker crashes mid-stream".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory-mcp.search_graph({ project: "pi-fabric", query: "retryStartup waitForTransportExit transport exited without result", limit: 5, fields: ["signature", "name", "file"] });
```
(Retrieval note: this seam lives inside private `AgentManager` methods; the public graph resolves `#resolveTransport` :1341-1354 and the constants file — cite manager.ts line ranges from source when tracing.)

## Verdict
Adopt sustained-dead windows, progress-gated retries, and machine-parsed error strings for supervisor loops over killable transports; adapt windows/cadences to your transports' poll costs; omit the pi-specific startup-error regex for other runners. Rich direct-test coverage across agent-manager and worker-e2e suites — no coverage caveat.
