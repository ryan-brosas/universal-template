<!-- capsule-v2 -->
# AdvancedSQLite clear-generation guard — how does a stale async pointer commit avoid resurrecting state a concurrent clear destroyed?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** `switch_to_branch` and `create_branch_from_turn` are multi-step async operations: validate on the worker thread, then commit an in-memory pointer. If `clear_session` (another instance, another process) commits between those steps, how does the stale pointer commit avoid pointing at a branch that no longer exists?

## Durable generation + guarded pointer commit
**Path/Symbol:** `src/agents/extensions/memory/advanced_sqlite_session.py:` `_commit_branch_pointer` (:107–142), `_ensure_session_clear_generations_table` (:1300–1314), `_refresh_branch_after_external_clear` (:1316–1345), `_resolve_read_branch` (:1347–1356), `clear_session` (:555–616, generation bump + locked reset), `switch_to_branch` (:1077–1126), `create_branch_from_turn` (:997–1050), `__init__` (:56–94, `_generation`/`_current_branch_id` sync contract).
**Signature:** `def _commit_branch_pointer(self, branch_id: str, generation: int) -> bool`; `def _refresh_branch_after_external_clear(self, conn, *, initialize: bool = True) -> None`.
**Data Shape:** `session_clear_generations(session_id TEXT PRIMARY KEY, generation INTEGER NOT NULL DEFAULT 0)` — one durable monotonic counter per session. In-memory mirrors: `self._generation` and `self._current_branch_id`, "synchronized with the durable row whenever a branch pointer is established or a write begins."

### Decisive source
```python
def _commit_branch_pointer(self, branch_id: str, generation: int) -> bool:
    # Acquires the connection lock so the generation check and the assignment
    # are atomic with clear_session's reset.
    with self._locked_connection() as conn:
        row = conn.execute("SELECT generation FROM session_clear_generations WHERE session_id = ?",
                           (self.session_id,)).fetchone()
        durable_generation = row[0] if row is not None else 0
        if durable_generation != generation:
            # A clear committed after `generation` was captured: its reset wins.
            self._generation = durable_generation
            self._current_branch_id = "main"
            return False
        self._generation = durable_generation
        self._current_branch_id = branch_id
        return True
```
and the read-side refresh that never creates the table:
```python
def _refresh_branch_after_external_clear(self, conn, *, initialize=True):
    if not initialize:
        table_exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' "
                                    "AND name = 'session_clear_generations'").fetchone()
        if table_exists is None:
            return  # pure reads never initialize coordination tables
    ...
    if generation != self._generation:
        self._generation = generation
        self._current_branch_id = "main"
```
`clear_session` bumps the generation and resets the pointer INSIDE its transaction and while still holding the lock, so "no other locked operation observes the session as cleared while the pointer still references a deleted branch." `pop_item` snapshots `(branch_id, generation)` at call time and re-resolves the branch after `_refresh_branch_after_external_clear` only when the generation moved — a concurrent `switch_to_branch` cannot redirect the pop.

**Flow:** switch/create: validate branch exists + capture durable generation (worker thread) → `_commit_branch_pointer(branch, generation)` under the lock → if the durable generation moved, the commit is a no-op that ALSO resynchronizes the in-memory mirror to the durable value. Reads: `_resolve_read_branch` refreshes against the durable generation (without initializing) before resolving an implicit branch.

**Invariant:** (1) A pointer commit whose captured generation is stale never repoints — the clear's reset to `main` wins. (2) The generation check and pointer assignment are atomic with the clear's own reset (same lock). (3) Pure reads never create coordination tables (initialize=False), so a read-only open of a legacy file stays read-only. (4) A stale commit resynchronizes the in-memory mirror rather than leaving it wrong.

**Probe:** `tests/extensions/memory/test_advanced_sqlite_session.py` — `test_stale_switch_after_clear_does_not_repoint_to_deleted_branch` (:3233, barrier-gated interleaving), `test_stale_create_branch_after_clear_does_not_repoint` (:3269), `test_clear_before_branch_transaction_prevents_stale_reservation` (:3299, no tombstone leak either), `test_pop_item_uses_branch_snapshot_when_branch_switches_concurrently` (:3148), `test_clear_session_resets_current_branch_to_main` (:3445), `test_external_clear_resets_stale_branch_before_next_write` (:3474), `test_external_clear_resets_stale_branch_before_pop` (:3510), `test_external_clear_resets_stale_branch_before_default_reads` (:3550), `test_default_read_does_not_initialize_clear_generation_table` (:3625), `test_switch_validation_cancellation_waits_for_generation_commit` (:3653), `test_post_clear_switch_synchronizes_generation_before_next_write` (:3730).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "clear generation branch pointer stale switch guard session_clear_generations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the durable-generation guard for ANY multi-step async mutation over shared mutable state with concurrent resetters: capture a durable epoch during validation, re-check it under the lock at commit, treat mismatch as "the resetter won" and resynchronize. Adopt the read-side non-initializing refresh so read paths stay read-only. Adapt the epoch storage to your store (here a one-row table; elsewhere a version column). Omit the SQLite specifics. Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.
