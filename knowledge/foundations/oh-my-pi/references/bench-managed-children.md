<!-- capsule-v2 -->
# Managed runner children — spawning, cancelling, and deleting benchmark runs without orphaning or resurrecting them

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How does a manager server launch long-running benchmark children so that restarts don't kill them, cancels don't orphan grandchildren, deletes can't be undone by re-discovery, and dev reloads don't corrupt the store?

## Detached spawn + SIGTERM-first cancel + delete-both-layers + liveness-over-status
**Path/Symbol:** `packages/metaharness/src/server.ts`:`ManagerServer` — `#spawnRunner` (481-514), `cancel` (599-627), `#runLive` (517-519), `resume` (442-478), `deleteRun`/`#destroyRun` (573-588), `assertSafeJobName` (94-98), hot-reload retire block (755-784).
**Signature:** `#spawnRunner(argv: string[], cwd: string, record: Omit<LaunchRecord, "pid">): number`; `cancel(jobName: string): { jobName; cancelled }`; `#runLive(run: RunRow): boolean`.
**Data Shape:** in-memory `Map<jobName, {proc, jobName, cancelled}>` of managed children layered over the persistent RunStore rows. Manager logs per run at `_manager/logs/<jobName>.log`.

### Decisive source
```ts
const proc = Bun.spawn(argv, {
    cwd, stdout: logFile, stderr: logFile, env: { ...process.env },
    // Own process group: a manager restart (Ctrl+C / --hot dev cycle) must
    // not deliver terminal signals to runners — that killed live runs.
    detached: true,
});
proc.exited.then(exitCode => {
    if (this.#stopped) return;   // retired (--hot) instance must not touch the closed store
    this.#store.markExit(jobName, exitCode, child.cancelled);
    // Final sync AFTER the terminal state: the ticker only revisits
    // running rows, so the last-2s trial results would otherwise be lost.
    this.#store.syncRun(jobName);
    ...
});
// Cancel: SIGTERM first so the runner forwards the signal to its harbor
// child (SIGKILL is untrappable — it used to orphan the harbor process,
// which kept running trials into the job dir); escalates after 5s.
child.proc.kill("SIGTERM");
const escalate = setTimeout(() => { try { child.proc.kill(9); } catch {} }, 5000);
child.proc.exited.then(() => clearTimeout(escalate));
// Liveness check that survives manager restarts
#runLive(run) { return this.#children.has(run.jobName) || (run.status === "running" && pidAlive(run.pid)); }
```

**Flow:** launch ⇒ validate job name is one path segment (`.`/`..`/separators rejected — anything else could escape the jobs dir), refuse duplicate live names, open the per-run log, spawn DETACHED (own process group), register the row with the real pid, tick → exit ⇒ markExit(cancelled flag honored) then ONE final syncRun (the periodic ticker only revisits `running` rows, so the last-2s trials would be lost otherwise) → cancel ⇒ SIGTERM first, SIGKILL escalation armed for +5s and disarmed by exit; for foreign (non-child) pids same ladder via `process.kill`, then markExit(null, cancelled=true) → resume/delete ⇒ trust liveness probes over the recorded status ("a runner killed while a previous server instance owned it leaves a stale running row"); delete removes DB rows AND the job dir AND the manager log — disk removal is not optional because `discover()` would resurrect a surviving dir on next start; refuses while live → shutdown ⇒ process-wide hooks registered once on globalThis; each `--hot` re-eval retires the previous instance BEFORE creating a new one, and `unhandledRejection` swallows only Bun's dev stream-teardown code (`ERR_STREAM_RELEASE_LOCK`) while rethrowing everything else.
**Invariant:** never signal with SIGKILL first (untrappable ⇒ orphaned grandchildren keep writing); never trust a stale `status` column when a pid probe is available; never delete DB rows without deleting the artifacts that discovery keys on; a retired server instance must never write to a closed store.
**Probe:** `packages/metaharness/test/manager.test.ts:325-371` — resume guard rejects unknown/non-harbor/live/config-less runs (liveness via live pid, not status); `:373-465` — experiment CRUD pins live-arm deletion refusal, row+dir+log removal, and post-delete 404.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "ManagerServer spawnRunner cancel destroyRun assertSafeJobName unhandledRejection ERR_STREAM_RELEASE_LOCK", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the child-management contract wholesale: detached spawn for signal isolation, TERM→KILL grace ladder, pid-probe liveness over recorded status, dual-layer (DB+disk+log) delete with discovery-resurrection awareness, and the hot-reload retire-before-replace pattern with selective unhandled-rejection swallowing. Adapt Bun's spawn/serve APIs to your runtime and the 5s grace window to your workload; omit the Bun-dev-specific error codes. Direct REST-level tests pin every guard.
