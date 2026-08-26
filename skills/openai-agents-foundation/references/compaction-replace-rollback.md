<!-- capsule-v2 -->
# Cancel-tolerant history replacement — how do you swap a session's whole history without risking an empty store?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory project `openai-agents-python`. **Question:** clear-then-add is not atomic: what does the replacement transaction do when the add fails, the clear fails, or the task is cancelled mid-flight (possibly twice)?

## The replacement transaction
**Path/Symbol:** `src/agents/memory/openai_responses_compaction_session.py`: `_replace_underlying_session_items` (:271–299), `_recover_from_failed_replacement` (:301–314), `_await_restore_despite_cancellation` (:316–336), failed-clear inspection `_restore_underlying_session_items_after_failed_clear` (:338–358), mutation lock (`self._mutation_lock = asyncio.Lock()`, :144) serializing snapshot/replace vs `add_items`/`pop_item`/`clear_session`.
**Signature:** `async def _replace_underlying_session_items(*, output_items, previous_items) -> None`.
**Data Shape:** restore is always constructed as an awaitable and drained to settlement before re-raising.

### Decisive source
```python
# _await_restore_despite_cancellation docstring (:317-323):
#   ``asyncio.shield`` alone is not enough: a second ``task.cancel()`` makes
#   ``await asyncio.shield(restore)`` raise immediately while restore is still
#   running. Keep re-awaiting the shielded task until it settles, then re-raise
#   ``CancelledError`` so callers still observe cancellation.
```
Failed-clear path first RE-READS current items and only restores if they differ from `previous_items` (:353–355) — a clear that never mutated needs no rewrite.

**Flow:** snapshot under lock → `clear_session()` → on success `add_items(output_items)` → ANY failure (Exception or CancelledError) routes to recovery: pick restore variant by whether `cleared` flipped, wrap in ensure_future + shield, re-await in a loop until done even under repeated cancellation, retrieve the outcome, THEN re-raise the original error. Newer writes can't interleave because everything holds `_mutation_lock`; a cancelled compaction cannot rewind past a newer write (lock re-acquisition ordering pinned by test).
**Invariant:** The session must never be observed empty after a failed replacement, and cancellation semantics stay honest: callers still see CancelledError, but only AFTER durable state is restored.
**Probe:** `grep -c "await asyncio.shield(restore_task)" src/agents/memory/openai_responses_compaction_session.py` → 2 (initial await :326 + re-await loop :330). Direct tests: `tests/memory/test_openai_responses_compaction_session.py::test_run_compaction_restores_history_when_cancelled_again_during_restore` (:721), `..._cancel_restore_waits_for_mutation_lock_before_newer_writes` (:795), `..._restores_history_when_replacement_add_fails` (:545), `..._restores_full_history_when_session_limit_applies` (:969).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "replace_underlying_session_items recover restore cancellation shield", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lock-guarded replace-with-rollback for any whole-store rewrite; adapt the store API calls; omit OpenAI compact specifics. Companion capsule: `sqlite-session-cancel-tolerant-writes` covers the single-write case; this one covers bulk replacement.
