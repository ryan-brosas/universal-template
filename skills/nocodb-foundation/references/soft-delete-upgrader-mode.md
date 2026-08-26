<!-- capsule-v2 -->
# Soft-delete upgrader mode — how does a background job run schema DDL without tripping cache staleness or partial writes?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What machinery must wrap a bulk column-add migration so every row-level query during the window still works and all DDL lands in ONE flush?

## Upgrader instance + per-model queued queries
**Path/Symbol:** `packages/nocodb/src/modules/jobs/migration-jobs/nc_job_010_soft_delete_column.ts:SoftDeleteColumnMigration.job` (:85-237), `.processModel` (:239-638); same pattern in `nc_job_005_order_column.ts:processModel` (:306-413).
**Signature:** `const ncMeta = new Upgrader(); ncMeta.enableUpgraderMode()` → per model `new Source({...originalSource, upgraderMode: true, upgraderQueries: []})` → collect `source.upgraderQueries.push(dbDriver.raw(...).toQuery())` → `Upgrader.flushSourceQueries(source, realDbDriver)` → `ncMeta.runUpgraderQueries()`.
**Data Shape:** `upgraderQueries: string[]` of raw SQL text on a throwaway Source clone; the Upgrader meta handle is separate from `Noco.ncMeta` — progress rows go to `Noco.ncMeta`, DDL queues on the Upgrader.

### Decisive source
```ts
const ncMeta = new Upgrader();
try {
  ncMeta.enableUpgraderMode();
  // ... per model:
  const source = new Source({ ...originalSource, upgraderMode: true, upgraderQueries: [] });
  source.upgraderMode = true;
  const dbDriver: CustomKnex = await NcConnectionMgrv2.get(source);
  // sqlMgr ops + raw pushes land in source.upgraderQueries, not executed yet
  await sqlMgr.sqlOpPlus(source, 'tableUpdate', { ...model, tn, originalColumns, columns });
  source.upgraderQueries.push(
    dbDriver.raw(`CREATE INDEX ?? ON ?? (??)`, [idxName, tnPath, col]).toQuery());
  // real connection has upgraderMode OFF so reads work while we stage:
  const realDbDriver = await NcConnectionMgrv2.get(new Source({ ...originalSource, upgraderMode: false } as any));
  await Upgrader.flushSourceQueries(source, realDbDriver);   // physical DDL, single transaction
  await ncMeta.runUpgraderQueries();                          // staged meta writes
} catch {
  await ncMeta.disableUpgraderMode();
}
```

**Flow:** enable upgrader mode once per job → for each model build a cloned Source whose flag makes the SQL client *stage* instead of execute → emit the whole table rewrite through `sqlMgr.sqlOpPlus('tableUpdate')` plus any raw index/data statements onto `upgraderQueries` → fetch a second driver from an unflagged Source clone (so it is a normal connection) → `flushSourceQueries` runs the physical batch, then `runUpgraderQueries` runs the meta batch → disable upgrader mode in BOTH success and catch paths.
**Invariant:** a porter's default — executing each DDL statement as generated — breaks twice: (1) mid-migration rows lack the new column, so any live query touching the table fails; staging keeps the window to one atomic flush; (2) `NcConnectionMgrv2.get` caches by Source identity, so flushing through the SAME flagged driver deadlocks the queue — you must request a fresh driver from an `upgraderMode: false` clone. Progress bookkeeping (`updateModelStatus`) always uses `Noco.ncMeta`, never the Upgrader, so resume state survives even when the DDL batch throws.
**Probe:** no unit test upstream (migration jobs are deployment-time). Source-grounded probe: `enableUpgraderMode` before the count query, `disableUpgraderMode` in both try-success and catch at `nc_job_010_soft_delete_column.ts:115/:226/:234`; paired clone drivers at :464-468; `_011` repeats identically at :107-110/:183-185.
**Coverage caveat:** no in-repo unit tests cover these jobs; contract pinned from whole-file source reads.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "SoftDeleteColumnMigration processModel enableUpgraderMode flushSourceQueries", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-handle split (staging Source clone vs real-driver clone) and the queue-then-flush ordering verbatim whenever porting "add a column to every table" style backfills; adapt the Upgrader class to your own meta layer; omit the SQLite serial-concurrency special case if you have no SQLite fleet.
