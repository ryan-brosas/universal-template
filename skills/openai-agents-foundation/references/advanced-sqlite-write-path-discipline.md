<!-- capsule-v2 -->
# AdvancedSQLite write-path discipline — how do side-table writes stay atomic with base-table writes, and how does a racing pop or usage write avoid mis-claiming or mis-attributing rows?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** The base `add_items` writes message rows; the advanced session layers structure metadata, destructive pops, and per-turn usage on top. How do you keep the side-table layer from leaking invisible rows, double-claiming pops across processes, or recording usage against a turn that was popped and recreated (the ABA case)?

## Atomic metadata + claim-on-pop + anchored usage writes
**Path/Symbol:** `src/agents/extensions/memory/advanced_sqlite_session.py:` `add_items` (:346–371, metadata in the SAME transaction), `_add_structure_metadata` (:754–788, failure → orphan cleanup → re-raise), `_insert_structure_metadata` (:790–876), `_cleanup_orphaned_messages_sync` (:894–912), `pop_item` (:460–553, `DELETE ... RETURNING` claim + branch snapshot + turn-usage drop), `store_run_usage` (:618–655), `_capture_current_turn` (:657–686), `_update_turn_usage_internal` (:1883–1971, anchor guard); base class `src/agents/memory/sqlite_session.py:` `_await_mutation` (:20–41), `_write_connection` (:156–170), `_invalidate_connection` (:172–186).
**Signature:** `async def pop_item(self) -> TResponseInputItem | None`; `def _capture_current_turn(self) -> tuple[int, str, int | None]`; `async def _update_turn_usage_internal(self, user_turn_number: int, usage_data: Usage, branch_id: str | None = None, turn_anchor: int | None = None) -> None`.
**Data Shape:** `message_structure` rows carry `sequence_number` (global order), `user_turn_number`/`branch_turn_number` (per-branch turn ids), `message_type`, `tool_name`. `turn_usage` is `UNIQUE(session_id, branch_id, user_turn_number)`. The pop claim is `DELETE FROM message_structure WHERE id = (SELECT id ... ORDER BY sequence_number DESC LIMIT 1) RETURNING message_id, user_turn_number`.

### Decisive source
```python
# pop: atomically claim the newest structure row ACROSS PROCESSES — the DELETE is
# the claim; RETURNING carries what was claimed:
cursor.execute("""
    DELETE FROM message_structure
    WHERE id = (
        SELECT id FROM message_structure
        WHERE session_id = ? AND branch_id = ?
        ORDER BY sequence_number DESC LIMIT 1
    )
    RETURNING message_id, user_turn_number
""", (self.session_id, resolved_branch_id))
claimed_row = cursor.fetchone()
if claimed_row is None:
    conn.commit(); return None
...
self._cleanup_orphaned_messages_sync(conn)  # drop the message only when no
                                            # other branch references it
# when the pop empties a turn, its usage row goes too:
if cursor.fetchone()[0] == 0:
    cursor.execute("DELETE FROM turn_usage WHERE session_id = ? AND branch_id = ? "
                   "AND user_turn_number = ?", (...))
# corrupted JSON or missing message rows: commit the claim, keep looking (continue)
```
and the usage anchor that defeats ABA:
```python
# turn_anchor = MIN(message_structure.id) of the turn — ids are monotonic and
# never reused, so a later pop+recreate that reuses the numeric turn id yields a
# DIFFERENT anchor; an existence-only guard would pass the ABA case.
guard_cursor.execute("""
    SELECT 1 FROM message_structure
    WHERE session_id = ? AND branch_id = ? AND user_turn_number = ? AND id = ?
""", (self.session_id, target_branch, user_turn_number, turn_anchor))
if guard_cursor.fetchone() is None:
    return  # the exact turn incarnation is gone; skip the stale write
```
`add_items` inserts message rows and structure metadata in ONE transaction: a metadata failure rolls the invisible message rows back with it; if the ROLLBACK itself fails, the base class's `_write_connection` invalidates the connection (close + evict, quarantine on close failure). `_await_mutation` swallows repeated caller cancellation while the mutation finishes, then re-raises the FIRST cancellation — a cancelled caller never leaves a half-committed batch whose outcome is unknown.

**Flow:** add_items → `_write_connection` → insert messages → insert structure rows (same txn) → commit; failure → rollback (or connection invalidation) → best-effort orphan cleanup → re-raise. pop_item → snapshot `(branch_id, generation)` at call time → worker: refresh-after-external-clear → claim loop (DELETE RETURNING → orphan cleanup → turn-usage drop → commit → return item, or continue past corrupt rows). store_run_usage → `_capture_current_turn` (one locked read: turn, branch, anchor) → `_update_turn_usage_internal` re-checks the anchor before INSERT OR REPLACE.

**Invariant:** (1) Message rows and structure metadata commit or roll back together — no invisible messages, no structure rows pointing at nothing (orphans are cleaned, never tolerated). (2) A destructive pop is a single DELETE claim: two processes can never receive the same item. (3) A pop targets the branch as of call time; a concurrent switch cannot redirect it. (4) Usage is recorded only against the exact turn incarnation captured — the anchor check kills the ABA stale write while staying scoped so an unrelated `delete_branch` does NOT drop the write. (5) Cancellation never outruns the commit: the mutation completes, then the caller sees the CancelledError.

**Probe:** `tests/extensions/memory/test_advanced_sqlite_session.py` — `test_add_items_rolls_back_messages_when_structure_metadata_fails` (:344), `test_add_items_can_retry_after_structure_metadata_failure` (:374), `test_add_items_failure_preserves_existing_history` (:406), `test_add_items_rolls_back_partial_structure_metadata_write` (:456), `test_add_items_rollback_failure_invalidates_connection` (:486), `test_pop_item_removes_its_structure_row` (:2941), `test_pop_item_removes_turn_usage_only_when_turn_emptied` (:2982), `test_pop_item_deletes_shared_copied_message_only_when_unreferenced` (:3058), `test_pop_item_claim_is_unique_across_processes` (:3188), `test_stale_store_run_usage_skipped_when_turn_removed_by_pop` (:3334), `test_stale_store_run_usage_not_recorded_against_reused_turn_number` (:3366, the ABA case), `test_store_run_usage_survives_unrelated_branch_deletion` (:3405), `test_post_commit_cancellation_propagates_after_known_mutation_outcome` (:603), `test_auxiliary_mutation_cancellation_waits_for_commit` (:675).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "pop item delete returning claim structure metadata transaction usage anchor turn", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the same-transaction rule for any side-table layer over a base store: metadata writes ride the base write's transaction, and a failed rollback invalidates the connection rather than trusting it. Adopt `DELETE ... RETURNING` (or equivalent claim-on-delete) for cross-process destructive reads, and the monotonic-id anchor for any "record against entity N" write that can race with delete+recreate of N. Adopt cancellation-tolerant mutation awaiting. Omit the SQLite-specific JSON corruption retry loop if your store rejects corrupt rows upstream. Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.
