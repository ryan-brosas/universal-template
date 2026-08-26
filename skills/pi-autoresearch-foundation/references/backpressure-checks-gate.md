<!-- capsule-v2 -->
# Backpressure checks gate — how do correctness checks veto a keep without polluting the metric?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** When do `autoresearch.checks.sh` runs happen, and how is "benchmark passed but tests failed" kept distinct from a crash?

## run action checks plane — post-benchmark exec, hard keep-gate in log, fourth status
**Path/Symbol:** `harness/server.ts:run` :1069–1104 (checks execution), `log` gate :1246–1252 (keep refusal), status vocabulary `ExperimentResult['status'] = 'keep'|'discard'|'crash'|'checks_failed'`.
**Signature:** benchmark passed (`exitCode===0 && !timedOut`) AND `autoresearch.checks.sh` exists → `execFileSync(bash, [checks], { timeout: checks_timeout_seconds*1000 (default 300) })`.
**Data Shape:** `session.lastRunChecks: { pass: boolean; output: string; duration: number } | null`; ETIMEDOUT flagged separately as `checksTimedOut`.

### Decisive source
```ts
// log action: the veto is SERVER-SIDE, not prompt-side
if (status === 'keep' && session.lastRunChecks && !session.lastRunChecks.pass) {
  return {
    text: `❌ Cannot keep — autoresearch.checks.sh failed.\n\n${session.lastRunChecks.output.slice(-500)}\n\nLog as 'checks_failed' instead.`,
    details: {},
  };
}
```

**Flow:** run → benchmark exits 0 & not timed out & checks file exists → checks execute with their OWN timeout; checks time never enters `lastRunDuration`/the primary metric. Outcomes: checks fail ⇒ response text instructs "Log as 'checks_failed'" + appends last 80 lines of output; log with keep while `lastRunChecks.pass === false` ⇒ HARD REJECTION (no JSONL write); agent must re-log as `checks_failed`, which then behaves like a crash in the revert branch (protected files preserved, tree cleaned). Checks skipped entirely when the benchmark itself failed or no file exists (`checksPass === null` = "no checks ran", distinct from false).
**Invariant:** three-way outcome space is load-bearing: `null` = not run (keep allowed), `true` = passed, `false` = ran-and-failed (keep impossible). Checks duration is excluded from the measured metric by construction (timed separately around execFileSync). `checks_failed` rows render distinctly in every UI surface (widget `⚠`, table color 'error', scatter symbol '⚠') so correctness regressions are visually separable from benchmark crashes.
**Probe:** anchors: `grep -n 'experimentCompletedWaitingForLog = true' harness/server.ts` → exactly :1107; `grep -n checks_failed harness/server.ts | cut -d: -f1` → :39 (type def), :1151 (response text), :1215 (type ref), :1249 (keep-veto), :1414 (revert branch) — five lines total (`grep -c` counts LINES = 5); direct test `__tests__/unit/state.test.ts` describe('After failed run_experiment') pins the widget's failed-state text. CLI validates status vocabulary before dispatch: `harness/cli.ts:400 validStatuses`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "checksPass autoresearch.checks.sh Cannot keep checks_failed", limit: 10 });
```

## Verdict
Adopt the server-side keep-veto and the null/true/false tri-state verbatim (prompt-only enforcement would let the model keep broken code); adapt the check command/timeout to host conventions; omit the pi-specific widget glyphs. Coverage caveat: the veto path has no dedicated vitest (state.test covers widget states only) — source-pinned.
