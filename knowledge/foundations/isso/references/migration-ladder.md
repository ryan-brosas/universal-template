<!-- capsule-v2 -->
# user_version migration ladder — how do sequential schema upgrades stay idempotent?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** How does a fresh DB skip migrations while an old DB climbs rungs 0→1→2→3→4→5 safely?

## PRAGMA ladder
**Path/Symbol:** `isso/db/__init__.py:SQLite3.migrate` (+ `migrate_to_version_4`, lines 66–207).
**Signature:** `migrate(to: int) -> None`; each rung guarded by `if self.version == N`.
**Data Shape:** `PRAGMA user_version` is the sole schema-version store; `MAX_VERSION = 5`.

### Decisive source
```python
if self.version >= to:
    return
...
# re-initialize voters blob due a bug in the bloomfilter signature
if self.version == 0:
    ...con.execute("UPDATE comments SET voters=?", (bf,))
    con.execute("PRAGMA user_version = 1")
    con.execute("COMMIT")

def migrate_to_version_4(self, con):
    rv = con.execute("PRAGMA table_info(comments)").fetchall()
    if any([row[1] == "notification" for row in rv]):
        logger.info("... 'notification' field already exists ...")
        con.execute("PRAGMA user_version = 4")
        return
```

**Flow:** constructor checks whether core tables exist — brand-new DBs get `user_version = MAX_VERSION` directly (no migration); existing DBs walk only the exact missing rungs. Each rung: BEGIN TRANSACTION → data fix → bump version → COMMIT, with ROLLBACK + RuntimeError on sqlite3.Error.
**Invariant:** Version bumps are INSIDE the same transaction as the data change (crash = old version + old data); v3→v4 is idempotent against pre-existing columns by inspecting `table_info` instead of trusting the version number alone (the "with_existing_column" test pins this).
**Probe:** `grep -c 'PRAGMA user_version' isso/db/__init__.py` (`8`) and `grep -c 'PRAGMA table_info(comments)' isso/db/__init__.py` (`1`).
**Test:** `isso/tests/test_db.py:test_comment_add_notification_column_migration_with_existing_column`, `test_comment_text_not_null_migration_with_rollback_after_error`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "migrate user_version transaction rollback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: version-in-transaction + capability-probe idempotence for third-party schemas. Adapt rung bodies to your schema history. Omit nothing from the error path — ROLLBACK-before-raise is what makes a failed migration retryable.
