<!-- capsule-v2 -->
# Migration jobs — versioned one-time migrations run through the job queue

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3`; Codebase Memory `nocodb`. **Question:** How do you run a sequence of one-time data migrations exactly once across multiple instances, using the job queue as the driver and a store-backed lock as the guard?

## Versioned migration runner
**Path/Symbol:** `packages/nocodb/src/modules/jobs/migration-jobs/init-migration-jobs.ts:InitMigrationJobs` (30–243); state helpers `helpers/migrationJobs.ts` (getMigrationJobsState / updateMigrationJobsState / setMigrationJobsStallInterval).
**Signature:** `async job(job: Job)` — registered as `JobTypes.InitMigrationJobs` (`_jobVersion: 2`).
**Data Shape:** `migrationJobsList` = `[{version, job: MigrationJobTypes, service}]` (16 entries, versions '1'..'16'). State stored in `MetaTable.STORE` under key `NC_MIGRATION_JOBS` = `{ version: string, stall_check: number, locked: boolean, instance?: string }`, init `{version:'0', stall_check: Date.now(), locked:false}`. EE/CE split swaps order-column vs no-op services via `isEE`.

### Decisive source
```ts
async job(job) {
  const runUuid = uuidv4();
  const state = await getMigrationJobsState();
  if (state.locked) {                                   // stall recovery
    if (Date.now() - state.stall_check > 10*60*1000) { state.locked=false; state.stall_check=Date.now();
      await updateMigrationJobsState(state); return this.job(job); }   // retry
    if (state.instance === runUuid) return;             // this instance holds it
    setTimeout(() => this.jobsService.add(JobTypes.InitMigrationJobs, {}), 10*60*1000).unref(); return;
  }
  const migrations = this.migrationJobsList.filter(m => +m.version > +state.version);
  if (!migrations.length) return;
  state.locked = true; state.stall_check = Date.now(); state.instance = runUuid;
  await updateMigrationJobsState(state, state);
  await new Promise(r => setTimeout(r, 5000));          // wait 5s to confirm lock
  const confirm = await getMigrationJobsState();
  if (confirm.locked && confirm.instance === runUuid) { // we own it
    const migration = migrations[0];                    // ONE migration per run
    const stallInterval = setMigrationJobsStallInterval();  // heartbeat every 5 min
    let migrated = false;
    try { migrated = await migration.service.job(); }
    catch (e) { this.log('Error running migration: ', e); }
    finally { clearInterval(stallInterval);
      state.locked = false; state.stall_check = Date.now();
      if (migrated) state.version = migration.version;
      await updateMigrationJobsState(state);
      if (migrated) this.jobsService.add(JobTypes.InitMigrationJobs, {});  // cascade next
    }
  }
}
```

**Flow:** On each invocation, read the store state; if locked and not stalled, schedule a re-check in 10 min and return. If unlocked, take the lock (write state), wait 5s, and confirm this instance still owns it. Run the *first* pending migration, heartbeat every 5 min (stall watchdog), then release the lock and — if the migration reported success — advance `version` and re-enqueue to run the next. A stalled run (>10 min without heartbeat) is force-released and retried.

**Invariant:** Only one migration runs per job invocation, and only one instance holds the lock at a time (5s confirm prevents a thundering-herd double-run). The lock is released in a `finally` even on migration error. A migration that returns falsy does NOT advance the version (it will retry next run). The 10-min stall check + 5-min heartbeat bound how long a crashed runner can hold the lock.

**Probe:** No in-repo unit test exists. Source-grounded probe: the `migrationJobsList` version ordering ('1'..'16') with the EE/CE `isEE` service swap at versions 5/6/7 is the contract a porter must preserve.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "InitMigrationJobs migrationJobsState stall_check locked", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the versioned-list + single-instance lock + 5s confirm + stall watchdog + one-per-run cascade; adapt the store key, versions, heartbeat cadence, and the EE/CE service split. Omit the individual migration service bodies (attachment, thumbnail, recover-links, etc.) — they are per-product data migrations. Caveat: no direct test — source-grounded only.
