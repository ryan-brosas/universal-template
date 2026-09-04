<!-- capsule-v2 -->
# Audit id migration — how do you copy a huge legacy table to a new UUIDv7-keyed one, day-by-day, without blocking or duplicating?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What makes the batch loop O(log N) per batch, and what preserves chronological order after re-keying?

## Keyset-by-PK pagination + timestamp-derived UUIDv7 ids
**Path/Symbol:** `packages/nocodb/src/modules/jobs/migration-jobs/nc_job_009_audit_migration.ts` — resume-from-highest-old_id (:33-44), keyset rationale comment (:70-79), per-row uuidv7 from created_at (:102-111), in-transaction dedup recheck (:142-167), completion gate + cleanup (:197-248).
**Signature:** cursor = `SELECT max(old_id)` on the new table; batch = `WHERE id > :cursor ORDER BY id ASC LIMIT batchSize` (100 for SQLite / 1000 otherwise); done when a full pass leaves `COUNT(legacy LEFT JOIN new WHERE new.old_id IS NULL) == 0` → drop the `old_id` column.
**Data Shape:** `{AUDIT}_old` rows keyed by integer `id`; new rows keyed by `uuidv7({msecs: created_at})`; carry column `old_id` marks provenance.

### Decisive source
```ts
// Keyset-paginate by the primary key `id`: `WHERE id > ? ORDER BY id`
// is a range-seek on the existing PK index on every supported database
// … each batch is O(log N) instead of the full table scan + sort the
// previous created_at-based, unindexed cursor did. That full scan per
// batch is the cause of the days-long migration in issue #12379.
// Processing in id order is irrelevant: each row's UUIDv7 is derived
// from its own created_at below, not from the order in which rows are copied.
const batch = await ncMeta.knexConnection.select('*').from(`${AUDIT}_old`)
  .where('id', '>', lastProcessedId).orderBy('id', 'asc').limit(batchSize);
…
const id = uuidv7({ msecs: timestamp });   // fallbackTimestamp 2020-01-01 for unparseable dates
```

**Flow:** detect completion by presence of the `old_id` provenance column → seed the cursor from the highest already-copied legacy id → loop: page by PK keyset, skip COMMENT rows entirely, mint each row's new id from ITS OWN created_at (invalid dates → fixed 2020 epoch), insert under a transaction that RE-CHECKS `old_id IN (...)` for parallel-runner races → advance cursor → return false ("more remain") so the versioned runner re-enqueues tomorrow — multi-day migrations are the designed shape, not a failure → only when a full pass finds zero unmigrated rows, drop the bridge column.
**Invariant:** order-independence of id assignment is what lets you paginate by PK instead of date; a porter who "fixes" the ordering back to created_at reintroduces the unindexed full-scan-per-batch that made this run for days. The transaction-scoped dedup recheck exists because TWO instances can run concurrently between runs. SQLite gets batchSize 100 due to the compound-SELECT term limit. Completion is detected structurally (column dropped), never by a flag row.
**Probe:** no unit test upstream. Source-grounded probe: issue number cited in-comment :76; fallback constant :21; `batch.length < batchSize` terminator :188-190; cleanup drops only the column, `_old` table drop explicitly deferred :231-233.
**Coverage caveat:** no in-repo tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "AuditMigration old_id uuidv7 lastProcessedId cleanupMigration", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt PK-keyset + derived-time-ordered ids for any large-table rekey; adapt the id scheme; omit the comment-type filter if your audit has no excluded op types.
