<!-- capsule-v2 -->
# FTS5 trigram migration — versioned drop-and-recreate under BEGIN IMMEDIATE with busy-lock attempt cap

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** How do you switch an existing external-content FTS5 table to a different tokenizer in place — when `CREATE VIRTUAL TABLE IF NOT EXISTS` cannot alter a tokenizer and other Pi processes may hold the write lock or race you mid-migration?

## DatabaseManager.migrateFtsTokenizer
**Path/Symbol:** `src/store/db.ts:migrateFtsTokenizer` (:1060–1128); constants `FTS5_TOKENIZER_VERSION = 'trigram-v1'`, key `fts5_tokenizer_version`, `FTS5_MIGRATION_MAX_LOCK_ATTEMPTS = 3` (:75), table DDL map `FTS5_TRIGRAM_TABLES` (:78–91); call site in schema init :388 (`ensureMemoryIndexes(db)` then `this.migrateFtsTokenizer(db)`).
**Signature:** `private migrateFtsTokenizer(db: DatabaseLike): void`.
**Data Shape:** two external-content trigram tables (`message_fts` over `messages.rowid`, `memory_fts` over `memories.id`); version marker row in `extension_metadata`; completion predicate = marker matches AND both tables' `sqlite_master.sql` contains `tokenize='trigram'` (case-insensitive regex).

### Decisive source
```ts
let lockAttempts = 0;
while (!migrationComplete()) {
  try { db.exec('BEGIN IMMEDIATE'); }
  catch (error) {
    // Each attempt waits up to busy_timeout. Cap the total attempts so a
    // permanently held writer cannot hang extension startup forever.
    if (isBusy(error) && ++lockAttempts < FTS5_MIGRATION_MAX_LOCK_ATTEMPTS) continue;
    if (isBusy(error)) throw new Error(
      `Timed out waiting for the FTS tokenizer migration lock after ${lockAttempts} attempts. `
      + "Close the other Pi process and retry.", { cause: error });
    throw error;
  }
  try {
    // Another Pi process may have completed the migration while this
    // connection waited for the write lock.
    if (migrationComplete()) { db.exec('COMMIT'); return; }
    db.exec(`
      DROP TABLE IF EXISTS message_fts; DROP TABLE IF EXISTS memory_fts;
      ${FTS5_TRIGRAM_TABLES.message}; ${FTS5_TRIGRAM_TABLES.memory};
      INSERT INTO message_fts(message_fts) VALUES ('rebuild');
      INSERT INTO memory_fts(memory_fts) VALUES ('rebuild');`);
    db.prepare(`INSERT INTO extension_metadata (key, value) VALUES (?, ?)
      ON CONFLICT(key) DO UPDATE SET value = excluded.value`)
      .run(FTS5_TOKENIZER_VERSION_KEY, FTS5_TOKENIZER_VERSION);
    db.exec('COMMIT'); return;
  } catch (error) {
    try { db.exec('ROLLBACK'); } catch { /* preserve migration error */ }
    throw error;
  }
}
```

**Flow:** check version marker + both table SQLs → already migrated: no-op → else loop `BEGIN IMMEDIATE` (each failure waits out `busy_timeout`, max 3 attempts, then an actionable "Close the other Pi process" error) → RE-CHECK completion inside the lock (a sibling process may have finished while we waited) → drop + recreate both tables as trigram → `'rebuild'` repopulation from source tables → upsert version marker → COMMIT; any body error ROLLBACKs (rollback failure is swallowed so the migration error propagates).
**Invariant:** the migration is versioned and idempotent — the marker alone is not trusted (both physical table SQLs must say trigram), the double-check inside the transaction makes concurrent migrators converge on one rebuild, and the whole rebuild is atomic so readers never see a half-populated index. Why trigram at all: unicode61 cannot match CJK substrings (`设备清单`) — trigram can; the short-CJK residual gap is handled at query time by `fts-trigram-cjk-search.md`. Note also :383-387: `DROP TABLE` during legacy migrations drops attached indexes, so `ensureMemoryIndexes` runs BEFORE this migration every startup.
**Probe:** `npx tsx --test tests/store/db.test.ts` — "rebuilds existing unicode61 FTS tables and preserves indexed data" (:185, real DB roundtrip: drops to unicode61, deletes marker, reopens manager, asserts both tables carry `tokenize='trigram'`, marker = `trigram-v1`, and CJK MATCH hits on BOTH tables), "waits for a concurrent tokenizer migration and rechecks its result under the write lock" (:254, fake DB: first `BEGIN IMMEDIATE` throws SQLITE_BUSY, second succeeds, marker appears on 2nd read ⇒ exactly 2 begin attempts, 1 commit, rebuild NEVER attempted), "fails startup with an actionable error when the tokenizer migration lock remains held" (:295, `/Timed out waiting for the FTS tokenizer migration lock/i`, beginAttempts === 3). GREEN under `npx tsx --test` (bun cannot load better-sqlite3).
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "migrateFtsTokenizer FTS5_TRIGRAM_TABLES fts5_tokenizer_version", limit: 5 })`

## Verdict
Adopt the versioned-marker + in-lock-double-check + attempt-capped migration shape for ANY virtual-table redefinition. Adapt table names, marker key, and attempt cap. Omit nothing — the fake-DB tests make the concurrency contract directly portable.
