<!-- capsule-v2 -->
# Sandbox schema-version migration ladder — how do in-document schema upgrades run, and what is guaranteed on downgrade?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How does a document at schema version N become version SCHEMA_VERSION via doc-actions, and what happens when the doc is NEWER than the code?

## Registry + replay ladder
**Path/Symbol:** `sandbox/grist/migrations.py:create_migrations` (:47-104), `migration` decorator (:112-127), `noop_migration` (:40-44), `get_last_migration_version` (:106-110); philosophy header (:16-36); target constant `sandbox/grist/schema.py:SCHEMA_VERSION` (:16, = 46).
**Signature:** `create_migrations(all_tables, metadata_only=False) -> [DocAction...]`; `@migration(schema_version, need_all_tables=False)`.
**Data Shape:** input = TableData dict keyed by table name (at minimum the `_grist_*` metadata tables); output = ordered doc-actions ending with `UpdateRecord('_grist_DocInfo', 1, {'schemaVersion': SCHEMA_VERSION})`.

### Decisive source
```python
# migrations.py :93-103
  migration_actions = []
  for version in range(doc_version + 1, schema.SCHEMA_VERSION + 1):
    migration_func = all_migrations.get(version, noop_migration)
    if migration_func.need_all_tables and metadata_only:
      raise Exception("need all tables for migration to %s" % version)
    migration_actions.extend(all_migrations.get(version, noop_migration)(tdset))

  # Note that if we are downgrading versions (i.e. doc_version is higher), then the following is
  # the only action we include into the migration.
  migration_actions.append(actions.UpdateRecord('_grist_DocInfo', 1, {
    'schemaVersion': schema.SCHEMA_VERSION
  }))
```

**Flow:** read `doc_version` from `_grist_DocInfo.schemaVersion[0]` (0 on any failure, :56-59) → rebuild a fresh `TableDataSet`: user schema from `schema.build_schema(...)` AddTable actions, every remaining table from an AddTable built off CURRENT schema defaults with INCOMPLETE `{'id': col_id}` columns for unknown/deprecated cols (:76-87), original data replayed as BulkAddRecord (:90) → apply each registered migration for `range(doc_version+1, SCHEMA_VERSION+1)`, defaulting to noop → ALWAYS stamp schemaVersion; on downgrade that stamp is the ONLY action. Philosophy: add-only metadata — never remove/rename/retype; meaning changes require a NEW column; legacy migrations may set `need_all_tables=True` (forces retry with full data) but new ones must not (:117-121). Shorthands: `add_column`, `maybe_add_column` (idempotent), `next_id`, `safe_parse`.
**Invariant:** Migrations must be expressible as plain doc-actions against possibly-degraded schemas (missing/deprecated columns tolerated); a doc newer than the code must survive opening — downgraded to a no-op stamp, never corrupted.
**Probe:** `sandbox/grist/test_migrations.py:test_migrations` (:8-67): replays the frozen historical `schema_version0()` fixture (:89-191) through the ladder and asserts the resulting schema EQUALS current `schema_create_actions()`; on mismatch the test FAILS WITH GENERATED SOURCE CODE for the missing migration function.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", mode: "ids", query: "migrations create_migrations migration decorator", limit: 10 });
```

## Verdict
Adopt the registry-of-pure-functions ladder over replayed TableData, the incomplete-column tolerance rule, and the newer-doc no-op stamp. Adapt the metadata-only/need_all_tables split if you have no on-demand tables. Omit the JS-side twins already mined (`SQLiteDB._migrate`, `ActiveDoc._migrate`) — this capsule is the sandbox half of that seam.
