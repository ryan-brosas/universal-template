<!-- capsule-v2 -->
# IngestResult resume handles — how does a caller recover an async bulk import from another process?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** What state must persist to reconstruct, poll, and judge a submission later — and how are per-item identities kept zip-aligned?

## IngestResult
**Path/Symbol:** `ingestion/src/zep_ingest/result.py:17-27` (terminal sets), `:89` (`IngestResult`), `:130` (`from_batch_ids`), `:137` (`from_task_ids`), `:141` (`mark_batch_failed`), `:150` (`refresh`), `:175` (`_param_identity_prefix`), `:205` (`status`), `:236` (`wait`), `:305` (`raise_for_status`).
**Signature:** classmethods `from_batch_ids(client, batch_ids)` / `from_task_ids(client, task_ids)` rebuild a usable result; `_param_identity_prefix(*, kind) -> list[str | None]`.
**Data Shape:** Resume handles = `batch_ids`, `task_ids`, `episode_uuids`; identity lists `node_uuids`/`edge_uuids` are parallel-to-input with `None` gap slots; private `_batch_summaries`/`_task_statuses`/`_task_params` caches excluded from compare.

### Decisive source
```python
# _UNSUCCESSFUL_STATUSES derived FROM the terminal sets so a status added
# there cannot slip past raise_for_status(); "untracked" deliberately
# excluded — unknown ≠ bad (wait() raises IngestUntrackedError instead).
_UNSUCCESSFUL_STATUSES = (_TERMINAL_BATCH_STATUSES | _TERMINAL_TASK_STATUSES) - {"succeeded"}

# _param_identity_prefix — stop at the first still-in-flight task so a later
# finish cannot surface its UUID ahead of an earlier submission; a terminal
# task with no identity leaves a None gap so later successes stay zip-aligned.
for task_id in self.task_ids:
    nodes, edges = _identity_from_task_params(self._task_params.get(task_id))
    values = nodes if kind == "node" else edges
    if values:
        collected.extend(values); continue
    if self._task_statuses.get(task_id) not in _TERMINAL_TASK_STATUSES:
        break
    collected.append(None)
```

**Flow:** refresh() polls only non-terminal summaries/tasks (never overwrites a pinned terminal summary), caches task.params by id → identities rebuilt in task_ids order after each poll → status aggregates by worst-first priority [failed, partial, canceled, untracked, processing, queued, succeeded] → wait() polls to terminal (raises timeout/untracked) → failed_items() paginates server-side failures under a limit.
**Invariant:** Identity alignment is the porting trap: node_uuids[i] MUST correspond to input i even when batch k failed — fill None gaps, never shift later successes forward ("so ``zip`` cannot pin a later success to an earlier failure"). Submit-time node UUIDs are never overwritten by task-param recovery. "untracked" is unknown-not-failed.
**Probe:** `grep -c 'def test' ingestion/tests/test_result.py` → 35 incl. `test_edge_uuids_keep_later_success_after_earlier_terminal_failure`, `test_refresh_keeps_submit_time_node_uuids_when_task_params_arrive`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "IngestResult from_task_ids identity prefix terminal", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt persisted-handle reconstruction + gap-slotted parallel identity lists + derived unsuccessful-status set; adapt the status vocabulary to your backend's states; omit BatchSummary-specific pinning.
