<!-- capsule-v2 -->
# Delegate run lifecycle — what states does an async run move through, and which transitions are terminal-without-result?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** What are the legal status values of a background run, and why do cancelled runs deliberately persist no result while spawn errors fabricate one?

## running → completed | failed | cancelled over the shared module-level runs Map
**Path/Symbol:** `src/delegate-tool.ts`: `RunStatus` (:152), `DelegateRun` (:154-180), `runs` Map (:181), `runningRunsSnapshot` (:208-214), cancel tool (:615-646), cancelled branch of finalize (:792-802 inside `finalize` :782-853), spawn-error finalizer (:857-879).
**Signature:** `RunStatus = "running" | "completed" | "failed" | "cancelled"`; `DelegateRun` carries `child?`, `result? {code,file,body}`, `consumed?`, `injected?`, `timedOut?`, `waiter?`.
**Data Shape:** one process-global Map keyed by `del_<ts36>_<rand4>`; `runningRunsSnapshot()` projects it for the TUI widget (runId/agent/task/startedAt of status==="running" only).

### Decisive source
```ts
// src/delegate-tool.ts:792-802 — cancelled runs never persist a result
// N2: cancelled runs never persist a result — wake a parked waiter (if any)
// and stop. status stays "cancelled" (set by cancel), so wait cannot
// mistake it for a finished-with-result run.
if (run.status === "cancelled") {
  await Promise.all([rm(replyFile, { force: true }), rm(activityFile, { force: true })]);
  run.finishedAt = Date.now();
  ...
  return;   // no result, stream files deleted
}
// :870-878 — spawn error DOES fabricate a synthetic result so wait has data
if (run.status === "running" || run.status === "cancelled") {
  run.status = run.status === "cancelled" ? "cancelled" : "failed";
  run.result = { code: null, file: "", body: `spawn error: ${String(err)}` };
```

**Flow:** spawn registers `{status:"running", child}` → cancel sets `status="cancelled"` + `consumed=true` BEFORE SIGTERM (so the waiter gets a consistent cancelled message and injection is suppressed) → finalize on close: cancelled = delete stream files, persist nothing, wake waiter; otherwise flip result+status ATOMICALLY to completed/failed (effectiveCode: EOF-watchdog kills with delivered output count as 0) → spawn `error` event settles the run itself (Node guarantees no follow-up close after error) with a synthetic result and wakes any waiter. The `settled` latch makes double finalize impossible across the close/error/watchdog trio. Cancel of an already-finished run is a loud no-op ("already completed").
**Invariant:** (1) exactly one settle path wins via the `settled` latch — close, error, and watchdog can all fire but only the first acts; (2) `cancelled` is the ONLY terminal state with no result — wait renders it from status alone and formatPayload's misleading "could not be persisted" line is explicitly bypassed for it; (3) every other terminal transition pairs status with result in the same synchronous step.
**Probe:** deterministic greps pin the cancelled-no-result branch (:795), the atomic result+status pairing (:817-818, effectiveCode :813), consumed-suppression at cancel time (:633-634), and the synthetic spawn-error result (:870-878) (no dedicated upstream lifecycle suite — the behavior is exercised through delegate-tool.test.ts delivery tests); adversarial naive port (persisting a result on cancelled runs) would break tests/delegate-tool.test.ts:154-182's dedup expectations (injectedWaitMessage suite, verified at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "makeDelegateCancelTool DelegateRun runs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-state machine with cancelled-as-terminal-no-result and the settled-latch single-settle rule for any long-lived background work registry. Adapt the runId format and snapshot projection to your UI surface. Omit per-run stdout capture in async mode (the applier streams to files instead).
