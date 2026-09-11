<!-- capsule-v2 -->
# progress-cancel-latch — how does a worker observe cancellation mid-parse?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ext-ragflow`. **Question:** Where must a ported task loop check cancellation so it cannot wedge or lose work?

## Progress write as cancellation checkpoint
**Path/Symbol:** `set_progress` `rag/svr/task_executor.py:186-217`; flag source `has_canceled` `api/db/services/task_service.py:606-613`; cleanup `do_handle_task` finally `rag/svr/task_executor.py:1723-1742`.
**Signature:** `set_progress(task_id, from_page=0, to_page=-1, prog=None, msg="Processing...")`; `has_canceled(task_id) -> bool`.
**Data Shape:** cancel flag is Redis key `f"{task_id}-cancel"` set by `cancel_doc_chunking` (`:601 REDIS_CONN.set(f"{t.id}-cancel","x")`).

### Decisive source
```python
cancel = has_canceled(task_id)
if cancel:
    msg += " [Canceled]"
    prog = -1
...
TaskService.update_progress(task_id, d)
close_connection()
if cancel:
    raise TaskCanceledException(msg)
```

**Flow:** every progress callback re-reads the Redis flag FIRST → canceled tasks still get their final "[ERROR]... [Canceled]" progress row persisted BEFORE the raise → TaskCanceledException propagates through `except TaskCanceledException:` re-raise arms (5 sites in task_executor.py) up to handle_task's dedicated handler (DONE_TASKS += 1, NOT failed) → finally block at :1723 deletes the doc's partial chunks from the doc store when canceled (`index_exist` check → `delete({"doc_id"})`). collect() also acks unknown/canceled messages instead of processing (`:265-270 redis_msg.ack()`).
**Invariant:** the DB/Redis progress write happens BEFORE the exception — dropping the raise would hang workers forever, dropping the write loses the user-visible cancel state. Cancellation is cooperative: nothing preempts a running coroutine except these checkpoints (plus the pre-build check at :1443).
**Probe:** `sed -n '190,210p' rag/svr/task_executor.py | grep -c 'TaskCanceledException(msg)'` → 1; `grep -n '{task_id}-cancel' api/db/services/task_service.py` → 1 hit :608; `grep -c 'except TaskCanceledException' rag/svr/task_executor.py` → 5; `grep -n 'redis_msg.ack()' rag/svr/task_executor.py` → 3 hits (:246 empty-msg ack, :269 canceled ack, :1810 final ack). Executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ragflow", query: "set_progress has_canceled TaskCanceledException", limit: 5, fields: ["name", "file"] });
```

## Verdict
Adopt checkpoint-on-progress-write + persist-then-raise + terminal ack; adapt the flag store (any shared KV); omit the recording-context calls (`get_recording_context`) which exist for dry-run comparison mode.
