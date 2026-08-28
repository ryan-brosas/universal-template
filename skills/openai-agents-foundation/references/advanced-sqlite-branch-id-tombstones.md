<!-- capsule-v2 -->
# AdvancedSQLite branch-ID tombstones — how do branch IDs stay unique forever across delete, clear, and processes?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** A branch can be deleted or wiped by `clear_session`, but a stale session instance (or another process) may still hold code paths that will write into a branch reusing that ID — how do you make every branch ID ever used permanently unreservable without a migration?

## Reservation table + lazy backfill
**Path/Symbol:** `src/agents/extensions/memory/advanced_sqlite_session.py:` `_ensure_branch_reservations_table` (:1267–1298), `_reserve_branch_id` (:1358–1390), `_copy_messages_to_new_branch` (:1392–1512, `BEGIN IMMEDIATE` at the top of `_copy_sync`), `delete_branch` (:1128–1216, backfill before delete), `clear_session` (:555–616, backfill before clear), `pop_item` (:460–553, backfill inside the pop loop).
**Signature:** `def _reserve_branch_id(self, cursor: sqlite3.Cursor, new_branch_id: str | None, from_turn_number: int) -> str`; `def _ensure_branch_reservations_table(self, conn: sqlite3.Connection) -> None`.
**Data Shape:** `branch_reservations(session_id, branch_id)` with `PRIMARY KEY (session_id, branch_id)` — a pure tombstone table with no foreign keys. Auto-generated IDs are `branch_from_turn_{n}_{int(time.time())}` with a `_2`, `_3`… suffix ladder on collision.

### Decisive source
```python
# Reservation is INSERT OR IGNORE + rowcount check — the DB's primary key is the
# arbiter, not a read-then-write race:
cursor.execute("INSERT OR IGNORE INTO branch_reservations (session_id, branch_id) VALUES (?, ?)",
               (self.session_id, new_branch_id))
if cursor.rowcount == 0:
    raise ValueError(f"Branch ID '{new_branch_id}' has already been used. Choose a new branch ID.")
return new_branch_id
# Auto-generated IDs collide-suffix instead of failing:
base_branch_id = f"branch_from_turn_{from_turn_number}_{int(time.time())}"
branch_id = base_branch_id
suffix = 1
while True:
    cursor.execute("INSERT OR IGNORE INTO branch_reservations (session_id, branch_id) VALUES (?, ?)",
                   (self.session_id, branch_id))
    if cursor.rowcount == 1:
        return branch_id
    suffix += 1
    branch_id = f"{base_branch_id}_{suffix}"
```
Legacy databases created before the reservations table existed are migrated lazily: `_ensure_branch_reservations_table` runs `CREATE TABLE IF NOT EXISTS` and then backfills any `branch_id` currently present in `message_structure` that has no reservation row — and it is called at the top of EVERY destructive operation (clear, delete, pop) so a legacy branch's last durable identity evidence is preserved before that operation can remove it. The copy path acquires SQLite's write reservation first (`BEGIN IMMEDIATE`) so two processes cannot pass the same reservation check concurrently.

**Flow:** create_branch_from_turn → `_copy_messages_to_new_branch` → `_copy_sync` opens `BEGIN IMMEDIATE` → ensure+backfill reservations → validate the source turn → reserve the new ID (explicit name rejected if tombstoned; generated name suffix-laddered) → copy structure rows → commit → `_commit_branch_pointer` under the generation guard. delete_branch/clear_session/pop_item each backfill first, so deleting the last evidence of a legacy branch still leaves its tombstone.

**Invariant:** (1) A branch ID, once used, can never be reserved again in that session — not after delete, not after clear, not from another process. (2) The reservation check and the write are one primary-key operation; there is no TOCTOU window. (3) Lazy migration must not retain a writer transaction after a no-op or error (the backfill runs inside the caller's transaction boundary). (4) `main` is implicitly reserved by backfill.

**Probe:** `tests/extensions/memory/test_advanced_sqlite_session.py` — `test_branch_ids_remain_reserved_after_delete_and_clear` (:1279), `test_branch_reservations_migrate_existing_populated_branches` (:1304, dropped table backfilled on next open), `test_legacy_branch_ids_are_backfilled_before_destructive_operations` (:1344, parametrized clear/delete/pop), `test_legacy_destructive_noops_leave_database_unlocked` (:1385), `test_branch_allocation_is_serialized_across_processes` (:1428, multiprocessing), `test_failed_branch_reservation_rolls_back_and_allows_retry` (:1232), `test_generated_branch_ids_do_not_merge_within_the_same_second` (:1208), `test_clear_before_branch_transaction_prevents_stale_reservation` (:3299).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "branch reservations tombstone insert or ignore backfill legacy destructive", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tombstone-table pattern for any caller-named durable identifier (branch IDs, run IDs, workspace names): `INSERT OR IGNORE` + rowcount as the arbiter, lazy backfill before every destructive op, `BEGIN IMMEDIATE` for cross-process serialization. Adopt the suffix ladder for generated names instead of failing. Omit the specific ID format. Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.
