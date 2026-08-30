<!-- capsule-v2 -->
# Functional-API call reuse — How does a resumed @entrypoint avoid re-executing finished @task calls?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** When an @entrypoint is interrupted and later resumed, the parent re-executes from the top — how do its earlier `@task` calls return their old results instead of running again?

## Reuse is pending-write reuse, not a stored result field
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_algo.py:Call` (:120-152), `prepare_push_task_functional` (:800-935), `_scratchpad` (:1280-1345); `libs/langgraph/langgraph/pregel/_runner.py:_call` (:700-786) and `_acall` (:789-945); `libs/langgraph/langgraph/pregel/_loop.py:PregelLoop.accept_push` (:550-587).
**Signature:** `Call(func, input: tuple[tuple, dict], *, retry_policy, cache_policy, callbacks, timeout)` — note: NO result slot; results live in checkpoint pending writes. `schedule_task(task, write_idx: int, call: Call | None) -> PregelExecutableTask | None`.
**Data Shape:** A child task path is `(PUSH, parent_task_path, idx, parent_task_id, Call)` where `idx = scratchpad.call_counter()` — the Nth `call()` inside the parent. Task id = `task_id_func(checkpoint_id_bytes, f"{parent_ns}{NS_SEP}{name}", str(step), name, PUSH, task_path_str(parent_path), str(idx))`. The in-progress path appends `True` (a Call IS present → interrupts from this child are suppressed at this level; responsibility lies with the parent).

### Decisive source
```python
# _runner.py:_call (sync twin _acall is line-for-line parallel)
    if next_task := schedule_task(
        task(),
        scratchpad.call_counter(),
        Call(func, input, retry_policy=retry_policy, cache_policy=cache_policy,
             callbacks=callbacks, timeout=timeout),
    ):
        if fut := next((f for f, t in list(futures().items())
                        if t is not None and t == next_task.id), None):
            # if the parent task was retried,
            # the next task might already be running
            pass
        elif next_task.writes:
            # if it already ran, return the result
            fut = concurrent.futures.Future()
            ret = next((v for c, v in next_task.writes if c == RETURN), MISSING)
            if ret is not MISSING:
                fut.set_result(ret)
            elif exc := next((v for c, v in next_task.writes if c == ERROR), None):
                fut.set_exception(exc if isinstance(exc, BaseException) else Exception(exc))
            else:
                fut.set_result(None)
        else:
            # schedule the next task
            fut = submit()(run_with_retry, next_task, retry_policy, ...)
```

**Flow:** Parent executes → each `@task(...)` call goes through `_call_with_options` (`pregel/_call.py:276-298`) which reads `CONFIG_KEY_CALL` from context and calls the runner's `_call`. That schedules a PUSH task whose id is deterministic in (checkpoint id, ns, step, name, PUSH, parent path, call index). On resume, the parent re-runs; its Nth call re-derives the identical id; `accept_push` (`_loop.py:550-587`) prepares the task and — unless `is_replaying` — runs `_reapply_writes_to_succeeded_nodes`, copying the checkpoint's pending writes (including the child's RETURN write) onto the fresh task object. Back in `_call`, branch 2 fires: the future resolves from stored writes and the child body never executes. Branch 1 covers parent retry (child already in flight this run); branch 3 submits new children with `__next_tick__=True` (their updates commit/stream after the current tick) and adds the future to SKIP_RERAISE_SET so child exceptions raise into the parent rather than at tick end.
**Invariant:** A functional-API call is idempotent across resume/retry purely by identity: same (checkpoint, step, parent path, call index) ⇒ same task id ⇒ prior RETURN/ERROR writes are found and replayed without execution. The call index comes from a per-task atomic counter (`LazyAtomicCounter`, `_algo.py:1338`), so call ORDER in the parent body is part of the identity — reordering calls changes ids and defeats reuse.
**Probe:** `python -m pytest "tests/test_pregel.py::test_task_before_interrupt_resume" "tests/test_pregel.py::test_multiple_tasks_before_interrupt_resume" "tests/test_pregel.py::test_no_redundant_put_writes_for_cached_task" -q -k memory` — all three pass on the memory checkpointer param (tasks before an interrupt resume without re-execution; the cached setup task produces no redundant put_writes on resume). Byte-exact: `grep -c "# if it already ran, return the result" libs/langgraph/langgraph/pregel/_runner.py` → 2 (sync + async twins); `grep -c 'parent_ns: checkpoint\["id"\]' libs/langgraph/langgraph/pregel/_algo.py` → 4 (every task-prep path threads the checkpoint map). Postgres/sqlite_aes params are environmental blocks (no postgres server / pycryptodome missing), recorded in verification.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "prepare_push_task_functional", limit: 8 });
```

## Verdict
Adopt the pattern: give every dynamically-spawned child a deterministic id derived from (parent identity, spawn ordinal), persist child results as writes keyed by that id, and on re-entry resolve already-written children from storage before executing. Adapt the future-resolution ladder (in-flight / already-wrote / submit-new) to your host's concurrency primitive. Omit the interrupt-suppression flag (`path[-1] is True`) unless you also port nested-interrupt routing — it only matters when children can interrupt.
