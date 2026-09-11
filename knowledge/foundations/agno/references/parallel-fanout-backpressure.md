<!-- capsule-v2 -->
# Parallel fan-out backpressure — how do you run N member tasks concurrently without corrupting shared state or swallowing cancellation?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** What isolation does each parallel branch need, and which exception must pierce `return_exceptions=True`?

## execute_tasks_parallel
**Path/Symbol:** `libs/agno/agno/team/_task_tools.py:762` (sync, ThreadPoolExecutor) / `:966` (`aexecute_tasks_parallel`, asyncio.gather).
**Signature:** `execute_tasks_parallel(task_ids: List[str]) -> Iterator[...|str]` — a task-mode tool the leader model calls with plan-task ids.
**Data Shape:** all-or-nothing validation BEFORE launch (missing id / wrong status / no assignee / unknown member ⇒ yield error string and return); per-branch tuple `(task_id, member_run_response, session_state_copy, member_agent_task, error)`.

### Decisive source
```python
# async variant
async def _run_single_task_async(task_obj, member_agent):
    ...
    member_session_state_copy = deepcopy(run_context.session_state)  # full deepcopy per branch
    thread_images = list(_images) ...                                # media lists copied per thread
    try:
        member_run_id = str(uuid4())
        if run_response.run_id is not None:
            await aregister_member_run(run_response.run_id, member_run_id)
        return (task_obj.id, await member_agent.arun(...), member_session_state_copy, ..., None)
    except RunCancelledException:
        raise                                                        # pierce gather's swallow
    except Exception as e:
        return (task_obj.id, None, member_session_state_copy, ..., e)

gather_results = await asyncio.gather(*[...], return_exceptions=True)
for gather_result in gather_results:
    if isinstance(gather_result, RunCancelledException):
        raise gather_result                                          # re-arm team cancel handler
# then per-result: paused → task back to pending + _propagate_member_pause;
#                  error → failed; content → completed; merge_parallel_session_states at END
```
Sync twin: `ThreadPoolExecutor(max_workers=len(tasks_to_run))` — one worker PER task, unbounded by any pool cap; completion events are buffered in a list and yielded only after ALL futures settle (:957-959).

**Flow:** validate all → mark all in_progress + persist plan → fan out (threads or tasks) → each branch deep-copies state + registers its member run for cancel-cascade → collect → re-raise cancellation → classify each outcome into task status → bulk-merge session states → save plan → yield buffered events.
**Invariant:** (1) `RunCancelledException` must be re-raised inside branches and AGAIN from gathered results — `return_exceptions=True` would otherwise convert cancel into a per-task "failed" row. (2) Session-state isolation is deepcopy-per-branch with ONE end-of-run merge — naive shared-dict mutation races across threads. (3) HITL pause returns the task to `pending` (not failed) so a later continue can retry it. (4) No worker bound: concurrency = number of requested tasks.
**Probe:** graph-resolved via `_get_task_management_tools` (search_graph :92-1182 Module span); closure-regression suite `tests/unit/team/test_delegate_closure_bug.py` covers the same fan-out capture pattern; executed GREEN 94 passed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "_get_task_management_tools", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt deepcopy-per-branch + single merge, cancel-piercing through gather, and pending-on-pause; adapt the executor choice to your runtime; omit agno's specific tool-docstring prompts. Caveat: sync twin uses one-thread-per-task — porters needing bounded concurrency must add a semaphore themselves.
