<!-- capsule-v2 -->
# Run FSM with durable counters — what guards keep a single-writer run lifecycle consistent across memory and SQLite?

**Source:** Ultireaaach `main@60bf4a3e478022df11ed2f04077d129f4f72cc60`; Codebase Memory `ultireaaach`. **Question:** how do you model collect/enrichment runs so only one is active, bounds are enforced, and every state change lands in a resumable runs table?

## Connected graph-selected seam
**Path/Symbol:** `packages/app/src/run-coordinator.ts:RunCoordinator` (22-66); HTTP coupling in `packages/app/src/server.ts` /api/run/* (464-488) and `packages/app/src/lead-store.ts:updateRun` (172-183).
**Signature:** `start(opts: RunOptions, runId?: number): StartResult` with `RunState = ready|running|paused|stopped|completed|failed|interrupted`, `RunCounts = {seen,added,merged,skipped,failed}`.
**Data Shape:** in-memory FSM + counts accumulator (copied on read); durable mirror row created by `store.createRun` BEFORE start, updated on every transition.

### Decisive source
```ts
start(opts: RunOptions, runId?: number): StartResult {
  if (this.active) return { ok: false, reason: "a run is already active" };
  if (!Number.isInteger(opts.target) || opts.target < 1 || opts.target > MAX_TARGET)
    return { ok: false, reason: `target must be an integer 1..${MAX_TARGET}` };
  this.current = opts; this.state = "running";
  this.counts = { seen: 0, added: 0, merged: 0, skipped: 0, failed: 0 };
  this.runId = runId ?? null;
  return { ok: true, runId: runId ?? undefined };
}
pause() { if (this.state === "running") this.state = "paused"; }
resume(){ if (this.state === "paused") this.state = "running"; }
stop()  { if (this.state === "running" || this.state === "paused") this.state = "stopped"; }
// updateRun: additive deltas + terminal timestamp
UPDATE runs SET state = ?, added = added + COALESCE(?, 0), /* ... */
  finished_at = CASE WHEN ? IN ('completed','stopped','failed','interrupted')
                THEN datetime('now') ELSE finished_at END, reason = ? WHERE id = ?
```
**Flow:** POST /api/run/start -> store.createRun(row) -> coordinator.start -> on rejection store.updateRun(failed, reason). pause/resume/stop each re-persist coordinator.status. Lead inserts mid-run call recordAdded/recordMerged then flush currentCounts into the run row. SIGINT -> interrupt() marks interrupted.
**Invariant:** at most one active run (`active = running||paused`); target is an integer in 1..MAX_TARGET(=100, DEFAULT 25); transitions are guard-refused not thrown (pause from paused is a no-op); counters move ADDITIVELY in SQL so partial flushes never double-subtract; finished_at set exactly once via terminal-state CASE.
**Restart-recovery boundary (spec law, not a gap):** the in-memory FSM has NO constructor rehydration — after process restart it forgets state/current/counts entirely, and that is REQUIRED behavior: mvp.md §12 (447-469) mandates "Application or browser termination marks unfinished work as interrupted", "Restart never resumes browser automation automatically", "The user may start a new bounded run from the retained collection or selected leads", and no duplicate leads on reprocessing. Durability lives entirely in the runs/leads SQLite rows (index.ts shutdown ladder calls coordinator.interrupt() at line 21 so SIGINT/SIGTERM mark rows terminal), and lead dedup by linkedin_url is what makes re-running safe. Do NOT "fix" the amnesia with session restore when porting.
**Probe:** `packages/app/test/smoke.test.ts` — five cases pin bounds rejection (0, MAX_TARGET+1), single-active-run, pause->resume->stop chain, interrupt-on-active, count accumulation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ultireaaach", query: "RunCoordinator", limit: 5 });
// observed: total 19, top hits RunCoordinator.status/active/start/pause/resume (28-47) in run-coordinator.ts
```

## Verdict
Adopt guard-refused transitions + pre-created run rows + additive counter deltas for any long-running local job lifecycle. Adapt MAX_TARGET/terminal-state vocabulary to your domain. Omit nothing on the single-active invariant — the HTTP layer trusts it when mapping rejections to run failures.
