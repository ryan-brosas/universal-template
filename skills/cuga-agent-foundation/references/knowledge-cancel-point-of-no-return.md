<!-- capsule-v2 -->
# Ingest cancel lifecycle — how do you cancel a long-running ingest without ever letting a row lie or opening a duplicate-content race?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f` (#685/#687/#692/#693); Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A user cancels a multi-minute document parse — where are the safe checkpoints, what must stay uncancellable, and how does the status row stay truthful against a racing worker?

## Cancel checkpoints + point of no return + serialized terminal writes
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:64-69` (`_TERMINAL_FILE_STATUSES`, `_DELETE_INGEST_WAIT_S = 30`), `:801-834` (`IngestStillFinishingError`, `IngestCancelledError`), `:1854-1866` (`_uncancellable_tasks`, `_task_write_lock`), `:2360-2379` (`_blocks_reupload`), worker checkpoints `:2525-2560` (`_check_cancelled` + persisted-status pre-check BEFORE `status="running"`), point of no return `:2746-2756`, locked terminal writes :2829/:2897/:2916/:2933, `cancel_task`/`_cancel_task_locked` `:3921-3982`.
**Signature:** `async cancel_task(task_id) -> dict | None`; `def _check_cancelled() -> None` (sync, closure over the cancel Event).

### Decisive source
```python
# engine.py:2740-2759 — the atomic handoff with NO await between check and add
                _ensure_vector_store_cached(collection)
                # POINT OF NO RETURN. Past this line the chunks land, so
                # cancel_task must stop writing a terminal status for this task
                # (see _uncancellable_tasks) — otherwise it would release the
                # dedup guard and let a re-upload race this insert.
                _check_cancelled()
                self._uncancellable_tasks.add(task_id)
                result = await self._insert_documents_async(...)
```
```python
# engine.py:2525-2549 — trust the PERSISTED row, not just the in-process event
        def _check_cancelled() -> None:
            if cancel_event.is_set():
                raise IngestCancelledError(task_id, filename)
        try:
            _check_cancelled()
            persisted = await self._metadata.get_task(task_id)
            if persisted and persisted.get("status") in ("completed", "failed", "cancelled"):
                return   # row already carries its real outcome; don't resurrect it
            await self._metadata.update_task(task_id, status="running")
```

**Flow:** checkpoints sit only where abandoning costs nothing: before the running-flip, after parse (`asyncio.to_thread` is NOT interruptible — Docling burns CPU until it returns, but the worker abandons before any store touch), after chunking, and immediately before insert. The event alone is insufficient: routes.py creates the task ROW then schedules the coroutine, so a cancel landing in that window leaves no `_active_tasks` entry — hence the persisted-status re-read. All terminal writes (completed/cancelled/superseded/failed) hold `_task_write_lock`, and `cancel_task` sets the event FIRST then reads-decides-writes under the same lock: whichever side goes second re-reads and stands down. `update_task` is last-write-wins with no CAS, which is exactly why the lock exists.

**Invariant:** (1) A missing file-task `status` means IN FLIGHT, never terminal — progress emits replace the whole entry with `{filename, stage, progress}` on purpose, and reading unknown as terminal would let a second ingest race a live insert. (2) Once `_uncancellable_tasks` holds the task id, `cancel_task` returns the live row WITHOUT writing "cancelled": persisting a lie would both misreport and RELEASE the dedup guard (`_insert_documents_async` does delete_by_source+add under replace_duplicates — the LOSER of that race wins the content, and "cancel then re-upload corrected file" hits this head-on). The in-memory set is cleared in the worker's `finally`. (3) SQL CHECK admits no new parent status for supersede — the audit lives in `file_tasks[filename].status="superseded"` with reason. (4) `_blocks_reupload` blocks only while the PARENT status is pending/running AND the specific file-task is non-terminal.

**Probe:** direct tests `tests/unit/test_knowledge_cancel_task.py::test_cancel_during_insert_is_refused_and_task_completes` (:206), `::test_cancel_during_insert_does_not_open_the_duplicate_window` (:233), `::test_cancel_before_running_flip_does_not_resurrect_running` (:272), `::test_blocks_reupload_treats_unknown_status_as_live` (:360), `::test_row_and_document_never_disagree_when_cancel_races_completion` (:414), `::test_cancel_while_running_persists_cancelled_status` (:95), `::test_cancel_is_idempotent_on_terminal_task` (:318).

## Get live surrounding code
**Retrieve:**
```ts
mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "cancel_task _uncancellable_tasks _task_write_lock IngestCancelledError", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** ADOPT whenever an operation has a commit horizon: mark the last cheap checkpoint, make everything past it uncancellable-by-row-truth, serialize every read-decide-write of shared outcome state behind one lock, and treat absent status fields as live rather than done.
