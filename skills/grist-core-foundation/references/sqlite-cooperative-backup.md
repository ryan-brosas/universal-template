<!-- capsule-v2 -->
# Cooperative chunked backup — how do you snapshot a live SQLite file without long locks, and give up gracefully if the writer never yields?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you copy a database that is being written continuously, so clients stay responsive AND the backup still completes under sustained write pressure?

## Page-bounded step loop with pause-escalation and restart detection
**Path/Symbol:** `app/server/lib/backupSqliteDatabase.ts:backupSqliteDatabase` (:32–175); escalation knobs `PAGES_TO_BACKUP_PER_STEP` = 1024 (4MB chunks) (:16), `PAUSE_BETWEEN_BACKUP_STEPS_IN_MS` = 10 (:21); companions `retryOnClose` (:200–213), `backupUsingBestConnection` (:221–237).
**Signature:** `async backupSqliteDatabase(mainDb: SQLiteDB | undefined, src: string, dest: string, testProgress?: (e: BackupEvent) => void, label?: string, logMeta?: object): Promise<string>`.
**Data Shape:** `BackupEvent { action: "step"|"close"|"open"|"restart"|"error", phase?: "before"|"after", error?: string }` — the observable event stream used by tests to time every phase.

### Decisive source
```ts
for (;;) {
  numSteps++;
  const stepStart = Date.now();
  // A RESTART is visible as remaining pages INCREASING between steps
  // (writer committed mid-backup; sqlite restarted the copy). Log ≥1/s.
  if (remaining >= 0 && backup.remaining > remaining && stepStart - restartMsgTime > 1000) {
    _log.info(null, `copy of ${src} (${label}) restarted`);
  }
  remaining = backup.remaining;
  let isCompleted = false;
  if (mainDb?.isClosed()) { throw new Error("source closed"); }
  try {
    // Bound each step to ~4MB of pages so writers get gaps between steps.
    isCompleted = Boolean(await fromCallback(cb => backup!.step(PAGES_TO_BACKUP_PER_STEP, cb)));
  } catch (err) {
    if (String(err).match(/SQLITE_BUSY/)) {
      busyCount++;
      if (busyCount === 10 && mainDb) {
        mainDb?.pause();   // escalate: freeze OUR OWN writes at the 10th busy
      }
    }
    if (!backup.failed) continue-with-log; else throw;
  } finally { /* track maxStepTimeMs vs maxNonFinalStepTimeMs */ }
  if (isCompleted) break;
  await delay(PAUSE_BETWEEN_BACKUP_STEPS_IN_MS);
}
```

**Flow:** remove any stale dest → prefer the live source connection (`mainDb`) so backups can terminate under constant changes; else open fresh dest-side handle with `PRAGMA synchronous=OFF; journal_mode=OFF` (crash may corrupt a backup nobody will use — acceptable) → loop {detect restart via increasing `remaining`; step ≤1024 pages; on SQLITE_BUSY count up and at the 10th PAUSE the app's own writes; sleep 10ms} → finally ALWAYS {unpause, `backup.finish()`, close handles, DELETE dest unless success}.
**Invariant:** Never hold the DB locked longer than one bounded step — progress requires yielding between steps; contention escalates by pausing the application's own writes only after repeated BUSY (a deliberate starvation trade: correctness of backup < liveness of clients until proven otherwise); a closed source connection aborts immediately (checked before EVERY step) rather than retrying blind — `retryOnClose` retries the WHOLE backup exactly once only when the connection closed DURING this attempt; failed backups leave NO partial file behind (dest removed in finally). Restart detection reads `backup.remaining`, not error codes.
**Probe:** `test/server/lib/HostedStorageManager.ts` `describe("backupSqliteDatabase")` — `"backups will make time for themselves if competing with writes"` (:1183; asserts completion iff pauses allowed, busy>10) and `"backups are robust to locking"` ×{without-doc, with-doc, with-closing-doc} (:1225+; closes the source mid-backup).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "backupSqliteDatabase SQLITE_BUSY pause backup.remaining", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for snapshotting any embedded DB under load: page-bounded steps + inter-step delay + own-write pausing as LAST resort + atomic cleanup-on-failure. Adapt chunk size/pause to your storage latency budget and what your driver exposes (the `remaining`-increase restart signal needs node-sqlite3's backup API or equivalent). Omit the fresh-connection synchronous=OFF branch if your backups must survive OS crashes.
