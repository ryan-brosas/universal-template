<!-- capsule-v2 -->
# Sync evaluation loop repair — how does evaluate_sync survive a closed/missing event loop and a Ctrl-C mid-run without leaking tasks?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How should a sync wrapper drive an async batch job on the caller's (possibly broken) loop, and how do you keep ordered results from anyio task groups?

## Loop self-repair + own-task cancel-on-interrupt
**Path/Symbol:** `pydantic_evals/pydantic_evals/_utils.py:get_event_loop` (:82-91), `run_until_complete` (:94-112), `task_group_gather` (:115-134); consumed by `dataset.py:evaluate_sync` (:460-473) and both fan-outs.
**Signature:** `run_until_complete(coro: Awaitable[T]) -> T`; `task_group_gather(tasks: Sequence[Callable[[], Awaitable[T]]]) -> list[T]`.
**Data Shape:** Results list pre-sized `[None] * len(tasks)`; slot-written by index inside the task group.

### Decisive source
```python
def run_until_complete(coro):
    loop = get_event_loop()
    task = asyncio.ensure_future(coro, loop=loop)
    try:
        return loop.run_until_complete(task)
    except BaseException:
        if not task.done():
            task.cancel()
            with suppress(BaseException):
                loop.run_until_complete(task)   # drive OUR cleanup to completion
        raise                                    # never touches other tasks on the caller's loop

results: list[T] = [None] * len(tasks)
async def _run_task(tsk, index): results[index] = await tsk()
async with anyio.create_task_group() as tg:
    for i, task in enumerate(tasks):
        tg.start_soon(_run_task, task, i)
```

**Flow:** `get_event_loop` replaces a CLOSED thread-current loop or creates one when absent → coroutine wrapped as a task → run; on ANY base exception (KeyboardInterrupt included) cancel our OWN task and pump it to completion so `async with`/finally blocks execute, then re-raise. Fan-out call sites pass no-arg lambdas with DEFAULT-ARG capture (`lambda case=case, rn=...: ...`) defeating late binding; gather returns results in INPUT order via slot writes, not completion order.
**Invariant:** Interrupting the sync bridge must not leak a pending task with un-run finally blocks, and must not cancel foreign tasks sharing the loop. Ordered gather is achieved by index assignment because anyio has no as_completed primitive.
**Probe:** `tests/evals/test_dataset.py::test_evaluate_sync_replaces_closed_event_loop` (:102-118) asserts the replacement loop is fresh, reused on second call, and carries no leftover tasks; `::test_evaluate_sync_creates_missing_event_loop` (:121-130) pins creation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "run_until_complete task_group_gather", limit: 6 });
```
Live check this pass: search_graph located `_utils.py` helpers; whole file read; tests executed GREEN at pin (74 passed incl. both loop-repair tests).

## Verdict
Adopt all three kernels verbatim (loop repair, own-task interrupt drain, indexed ordered gather). Adapt none of the semantics; only naming. Omit the logfire_span warning-suppression wrapper (adjacent seam).
