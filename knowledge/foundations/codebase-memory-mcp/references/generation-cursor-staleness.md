<!-- capsule-v2 -->
# Generation-keyed cursors — how do pagination tokens detect that the graph changed underneath them?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you mint a cheap cursor staleness token so pages can never silently mix two index generations?

## db_uid + mutation_gen composite
**Path/Symbol:** `src/store/store.c:cbm_store_generation` (1648–1669) and the `upsert_project` seeding block (1620–1642).
**Signature:** `int cbm_store_generation(cbm_store_t *s, char *buf, size_t bufsz);` — writes `"u<db_uid>g<mutation_gen>"`, or `"legacy"` for pre-migration DBs.
**Data Shape:** `db_uid` = random 8-byte hex minted ONCE per DB file (`INSERT OR IGNORE`); `mutation_gen` = integer bumped on EVERY `upsert_project` (the choke point all full/incremental/watcher runs pass through).

### Decisive source
```sql
CREATE TABLE IF NOT EXISTS store_meta (k TEXT PRIMARY KEY, v TEXT);
INSERT OR IGNORE INTO store_meta VALUES('db_uid', lower(hex(randomblob(8))));
INSERT OR IGNORE INTO store_meta VALUES('mutation_gen','0');
UPDATE store_meta SET v = CAST(CAST(v AS INTEGER)+1 AS TEXT) WHERE k='mutation_gen';
```

**Flow:** first upsert on a fresh DB seeds uid+gen → every later index run's upsert bumps gen → tool responses embed `cbm_store_generation()` in cursors → next page request re-reads the generation; mismatch ⇒ loud `stale_cursor` error instead of duplicated/skipped rows. A full reindex publishes a NEW file whose uid differs, so old-file cursors can never validate against rebuilt node ids either.
**Invariant:** Reads are generation-stable; any write path must funnel through the bump; two distinct DB files can never share a token (random uid).
**Probe:** `tests/test_store_pragmas.c:store_generation_tracks_mutations` (stable across reads, changes after upsert, distinct across DBs) and `tests/test_mcp.c:tool_check_index_coverage_rejects_stale_generation` (`"generation_matches":false`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_generation", limit: 5 });
```

## Verdict
Adopt the two-component token (file identity + mutation counter) and the loud stale-cursor error; adapt the storage to your meta-table conventions; omit the `"legacy"` pre-migration spelling if your schema ships with the table from day one.
