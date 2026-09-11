<!-- capsule-v2 -->
# Bench run store — how to mirror filesystem-truth benchmark runs into SQLite and survive dead owners

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** When benchmark artifacts live on disk as the source of truth and the launching process may die at any moment, how does a queryable run store stay correct — status inference, orphan handling, phantom rows, WAL startup?

## Disk-truth store: upsert-from-disk, never trust the row's age
**Path/Symbol:** `packages/metaharness/src/store.ts`:`RunStore` (`syncRun` 354-441, `discover` 325-351, `enableWal` 167-181).
**Signature:** `class RunStore { constructor(jobsDir: string, dbPath?: string); discover(): number; syncRun(jobName: string): RunRow | null; syncActive(): RunRow[]; syncAll(): void; markExit(jobName: string, exitCode: number | null, cancelled?: boolean): void; }`
**Data Shape:** SQLite tables `runs` (job_name PK + rollup counters + `pid`, `config_json`, `metrics_json`), `trials` (PK `(job_name,name)`), `experiments` (id PK + goal). Job dirs named `_bench`/`_manager` are excluded from discovery (`NON_JOB_DIRS`). DB lives at `<jobsDir>/_manager/metaharness.sqlite`.

### Decisive source
```ts
// syncRun: prune trials whose dirs vanished (a resume deletes interrupted trial
// dirs and re-runs under a fresh suffix) — otherwise phantom `running` rows
// haunt the dashboard forever.
if (snapshot.traces.length > 0) {
    const names = snapshot.traces.map(t => t.name);
    this.#db.query(`DELETE FROM trials WHERE job_name = ? AND name NOT IN (...)`)...
}
// Runs with no owning process (historical dirs, or a runner that died with a
// previous manager). Infer terminal state from result metadata or directory
// freshness — an orphaned harbor child may still be running and writing
// trials, so a fresh dir stays "running".
if (row.pid === null && row.finishedAt === null && row.status !== "cancelled") {
    if (result?.finishedAt != null) { status = "complete"; finishedAt = result.finishedAt; }
    else if (jobDirFresh(dir))      { status = "running"; }
    else { status = snapshot.done > 0 && snapshot.done >= snapshot.total ? "complete" : "failed"; }
}
```

**Flow:** constructor enables `busy_timeout=5000` + WAL (retrying the pragma ~10×100ms because `SQLITE_BUSY_RECOVERY` never invokes the busy handler) then runs idempotent `ALTER TABLE` migrations (incl. `RENAME COLUMN slide TO prewalk`) → `discover()` backfills unknown job dirs as historical rows (status `running`, then immediately `syncRun`ed) → `syncRun(jobName)` re-reads native artifacts via the benchmark adapter, upserts trials inside ONE transaction, prunes vanished trial names, refreshes rollups, and infers terminal state only for ownerless rows (`pid === null && finishedAt === null && !cancelled`) → `syncActive()` clears dead pids (`kill(pid,0)` probe) before syncing so disk inference decides; `markExit` is called only by the live owning process.
**Invariant:** the filesystem is the source of truth — the DB is a rebuildable mirror plus manager-owned metadata (pid/role/note/config). Status inference for orphaned runs prefers explicit terminal markers (`result.finishedAt`), falls back to directory freshness (<30min mtime ⇒ still running, an orphan may be writing), and only then decides complete/failed from counts. Never mark an ownerless-but-fresh dir failed.
**Probe:** `packages/metaharness/test/manager.test.ts:88-203` — `discovers historical job dirs and mirrors trial state` (fresh dir + running trial stays `running`), `marks discovered runs complete when harbor recorded a terminal state`, and `releases a dead runner's pid without failing a possibly-live orphan` (dead pid ⇒ `pid:null` but status still `running`; later terminal marker completes it).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "RunStore syncRun discover enableWal markExit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mirror pattern: idempotent-schema SQLite beside the artifacts, transactional trial upsert + vanished-name pruning, freshness-based orphan inference, and WAL-pragma retry (busy handler gap on recovery locks is universal SQLite behavior). Adapt the 30-minute staleness threshold, table shape, and `Bun.sleepSync` retry loop to your runtime; omit the harbor-specific artifact parsing (that is the adapter capsule's contract). Tests are bun:test but assert pure file-system behavior — portable evidence.
