<!-- capsule-v2 -->
# Online-eval background dispatch — how does fire-and-forget evaluation survive sync callers with no event loop, and how do tests drain it deterministically?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter making evaluation non-blocking must decide where the evaluator coroutine runs when the decorated function is sync (possibly with no running loop), and how a test suite can await all of that background work without sleeps.

## Loop-vs-thread dispatch ladder + single-lock drain
**Path/Symbol:** `pydantic_evals/pydantic_evals/_online.py:EVALUATION_DISABLED/_background_*/dispatch_async/dispatch_in_background_thread/wait_for_evaluations` (:126-186, :489-512); `pydantic_evals/pydantic_evals/online.py:_wrap_sync` tail (:786-805); `tests/evals/conftest.py:_cleanup_background_evaluations` (whole file, 19 lines).
**Signature:** `dispatch_async(coro) -> None`; `dispatch_in_background_thread(coro) -> None`; `wait_for_evaluations(*, timeout: float = 30.0) -> None` (async).
**Data Shape:** Three module-level registries under ONE `threading.Lock`: `_background_tasks` (asyncio.Task set, done-callback removes), `_background_events` (anyio.Event set, trio only), `_background_threads` (non-daemon Thread set).

### Decisive source
```python
# _wrap_sync tail — the ladder decision:
try:
    asyncio.get_running_loop(); has_running_loop = True
except RuntimeError:
    has_running_loop = False
coro = _online_internal.dispatch_evaluators(sampled, context, span_reference, target, config)
if has_running_loop:
    _online_internal.dispatch_async(coro)                 # caller's loop → ContextVars preserved
else:
    _online_internal.dispatch_in_background_thread(coro)  # own thread + own loop

def dispatch_in_background_thread(coro):
    ctx = contextvars.copy_context()          # captured BEFORE the thread starts
    async def _run(): await coro
    def _thread_target():
        try: ctx.run(anyio.run, _run)
        finally:
            with _background_lock: _background_threads.discard(thread)
    thread = threading.Thread(target=_thread_target, daemon=False)
    ...

async def wait_for_evaluations(*, timeout=30.0):
    with _background_lock:
        tasks_snapshot, events_snapshot, threads_snapshot = list(...), list(...), list(...)
    for task in tasks_snapshot:
        try: await task
        except BaseException: pass            # evaluation failures never fail the waiter
    for event in events_snapshot: await event.wait()
    if threads_snapshot:
        def _join_threads():
            for thread in threads_snapshot:
                thread.join(timeout=timeout)
                if thread.is_alive(): warnings.warn(...)
        await run_sync(_join_threads())       # join off-loop
```

**Flow:** async wrapper always dispatches on the CALLER's running loop (`loop.create_task`, tracked + done-callback removed; trio branch spawns a system task with an Event marker). Sync wrapper probes for a running loop: present → same task path (a sync function called from async context keeps ContextVars); absent → `copy_context()` then a non-daemon thread running `anyio.run` inside that context. Drain = snapshot all three registries under the lock ONCE, await tasks (exceptions swallowed), wait events, join threads off-loop with per-thread timeout warning. The evals conftest installs an autouse fixture calling `wait_for_evaluations()` after EVERY test so leaked background work cannot bleed across tests.
**Invariant:** Background work must be observable and drainable: every dispatched unit registers in exactly one registry before it can finish, and removal happens in a done-callback/finally, not at start. Draining must never propagate evaluation exceptions to the waiter. A porter who fires `threading.Thread` without `copy_context()` loses every ContextVar (config, disabled flag, task-run accumulator) inside the evaluation.
**Probe:** `tests/evals/test_online.py::test_sync_function_no_event_loop` (:1349-1371) calls the sync wrapper via `run_sync` (no loop) and still gets exactly one sink call after drain; `test_sync_function_from_async_context` (:1241-1262) pins the loop-present branch; `tests/evals/conftest.py` autouse fixture (:10-19) is the standing drain contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "dispatch_in_background_thread wait_for_evaluations _background_tasks", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session; anchors confirmed by direct read of _online.py :126-186/:489-512, online.py :786-805, and conftest.py whole at pin `a5b5fb7a`.

## Verdict
Adopt the probe-for-running-loop ladder and the copy-context-before-thread rule — they are the entire correctness story for sync callers. Adopt the three-registry-under-one-lock design with snapshot-then-drain, and the autouse per-test drain fixture as the test-side contract. Adapt the trio branch away if your host is asyncio-only. Omit the non-daemon choice's flip side (process exit waits on stragglers) unless your host needs daemon semantics — the source deliberately chose non-daemon so results are not lost at shutdown. Coverage caveat: none — files read whole this pass.
