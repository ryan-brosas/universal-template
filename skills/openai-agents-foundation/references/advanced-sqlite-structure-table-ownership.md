<!-- capsule-v2 -->
# AdvancedSQLite structure-table ownership — how can several base-table configurations share one DB-file format without a second pair silently reading the first pair's structure rows?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** The side tables (`message_structure`, `turn_usage`) are not named after the base tables, so one database file can only serve one `(sessions_table, messages_table)` pair — how does the schema prove which pair owns the file, and how does a second session get rejected instead of joining against the wrong messages table?

## Ownership claim + verify ladder
**Path/Symbol:** `src/agents/extensions/memory/advanced_sqlite_session.py:` `_init_db_for_connection` (:96–105), `_claim_structure_tables` (:144–193), `_resolve_base_table_owners` (:195–228), `_resolve_table_identifier` (:230–259), `_identifiers_equal` (:261–269), `_init_structure_tables` (:271–345), `_STRUCTURE_TABLE_OWNERS`/`_OWNER_TARGET_COLUMNS` (:137–143), `_allow_all_sqlite_actions` (:28–36).
**Signature:** `def _claim_structure_tables(self, conn: sqlite3.Connection) -> None`; `def _resolve_base_table_owners(self, conn) -> dict[str, str]`; `def _identifiers_equal(conn, left: str, right: str) -> bool`.
**Data Shape:** Ownership is recorded as ordinary FOREIGN KEYs on the side tables pointing at the base tables (`message_structure.session_id -> sessions_table(session_id)`, `message_structure.id/message_id -> messages_table(id)`). `_STRUCTURE_TABLE_OWNERS = {"message_structure": ("session_id", "message_id"), "turn_usage": ("session_id",)}` maps each side table to the base columns that must own exactly one foreign key each.

### Decisive source
```python
# create_tables=False must PROVE the claim before opening; missing or ambiguous
# ownership is rejected, never accepted:
foreign_keys = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
owner_rows = {column: [row for row in foreign_keys
                       if self._identifiers_equal(conn, row[3], column)]
              for column in columns}
if any(len(owner_rows[column]) != 1 for column in columns):
    raise ValueError(
        f"The `{table}` table in {self.db_path} does not record exactly one owner "
        "foreign key for each required base-table column. Construct an "
        "AdvancedSQLiteSession with create_tables=True to create and claim the "
        "structure tables before opening the database without them.")
# ...then each recorded owner must equal the CONFIGURED pair (resolved through
# SQLite itself, not string-parsed):
if any(not self._identifiers_equal(conn, owner_rows[column][0][2], owned_by[column])
       or not self._identifiers_equal(conn, owner_rows[column][0][4],
                                      self._OWNER_TARGET_COLUMNS[column])
       for column in columns):
    raise ValueError(... "Structure tables are shared per database file, so give "
                        "each sessions_table/messages_table pair its own db_path.")
```
and the identifier-equality rule that refuses to reimplement SQLite's collation:
```python
def _identifiers_equal(conn, left, right) -> bool:
    # SQLite folds identifiers with ASCII rules only; Python casefold() would
    # equate names SQLite keeps distinct (e.g. ßsessions vs sssessions).
    row = conn.execute("SELECT ? = ? COLLATE NOCASE", (left, right)).fetchone()
    return bool(row[0])
```
`_resolve_table_identifier` resolves a configured identifier token by asking SQLite which table object it selects: a temporary authorizer records every `SQLITE_READ` table name seen during `SELECT * FROM {identifier} LIMIT 0`; exactly one distinct name must result, else the identifier is ambiguous. Afterwards the authorizer is removed and a probe `SELECT 1` detects a stuck "not authorized" state (older Pythons cannot unset an authorizer), falling back to a permanent allow-all authorizer instead of leaving the connection locked.

**Flow:** `create_tables=True` → `BEGIN IMMEDIATE` → create base schema + side tables (with owner FKs) → `_claim_structure_tables` validates its own layout → commit. `create_tables=False` → `_claim_structure_tables` first (rejects unclaimed or foreign-owned files), then base schema creation. `_resolve_base_table_owners` resolves the CONFIGURED base-table names through the same authorizer trick and additionally verifies the messages table's own `session_id` FK points at the configured sessions table — so a changed sessions table with shared messages is also rejected.

**Invariant:** (1) One database file serves exactly one `(sessions_table, messages_table)` pair, ever — a second pair is rejected at open and creates NO objects (the rejection happens before any DDL). (2) A `create_tables=False` session can never open a file before any pair has claimed it, and cannot open a file claimed by a different pair. (3) Identifier comparison is delegated to SQLite's own collation, never Python string ops. (4) Authorizer use must leave the connection usable — the fallback ladder ends in allow-all, not a dead connection.

**Probe:** `tests/extensions/memory/test_advanced_sqlite_session.py` — `test_structure_tables_reject_a_second_base_table_pair` (:3893, second pair rejected AND creates no `second_*` objects), `test_structure_tables_reject_changed_sessions_with_shared_messages` (:3930), `test_structure_tables_reject_changed_messages_with_shared_sessions` (:3966), `test_structure_tables_accept_equivalent_identifier_casing` (:4004), `test_structure_tables_accept_quoted_custom_session_table` (:4033), `test_identifier_resolution_leaves_connection_authorized` (:4065), `test_structure_tables_reject_distinct_non_ascii_identifiers` (:4075, ßsessions vs sssessions), `test_no_create_session_rejects_a_database_without_an_owner` (:4108), `test_no_create_session_rejects_owner_metadata_without_base_tables` (:4136), `test_structure_tables_reject_an_ownerless_layout` (:4161), `test_structure_tables_reject_malformed_owner_layouts` (:4201).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "claim structure tables foreign key owner base table pair identifier authorizer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the claim/verify ladder for ANY side-table schema layered over configurable base tables: record ownership as real foreign keys, verify on no-create open, reject ambiguity loudly. Adopt SQLite-delegated identifier comparison whenever table names are caller-configured. Adapt the authorizer-based identifier resolution only if your driver exposes a cleaner name-resolution path; keep the stuck-authorizer fallback. Omit the specific table names. Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.
