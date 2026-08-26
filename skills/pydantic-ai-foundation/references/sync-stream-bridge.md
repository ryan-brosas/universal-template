<!-- capsule-v2 -->
# SyncStreamBridge: async streaming CM on the caller's event loop

## Source / Question
`pydantic_ai_slim/pydantic_ai/_sync_stream.py` — How does pydantic-ai expose an async streaming context manager to synchronous code without breaking event-loop affinity or cancel-scope/task affinity? A porter must know why naive `loop.run_until_complete(anext(...))` pumping is wrong.

## Path / Symbol
`pydantic_ai_slim/pydantic_ai/_sync_stream.py` — `SyncStreamBridge` (196–~400), `_hold_context_manager` (57–85), `_run_task_to_completion` (108–135), `_shutdown_loop` (137–157), `_request_exit` (159–181), `_finalize_loop` (183–210), `_receive_one` (212–222).

## Signature
```python
class SyncStreamBridge(Generic[StreamT]):
    def __init__(self, cm: AbstractAsyncContextManager[StreamT], *, async_alternative: str)
    stream: StreamT
    def shutdown(self, ...) -> None   # from the sync wrapper's __exit__
```

## Data Shape
Owner task holds the async CM open; pump tasks run each `async for` pass; `entered: asyncio.Future[(StreamT, Context)]`, `exit_requested: asyncio.Future[_ExitInfo]`, `pump_tasks: set[asyncio.Task]`. `weakref.finalize` fallback for dropped-without-close wrappers.

## Decisive source
Module docstring (1–15) + `_hold_context_manager` (57–85): naive per-step `loop.run_until_complete(anext(...))` runs each step in a DIFFERENT asyncio task, so any cancel scope the async code enters/exits per step (the agent graph's per-node scopes, `group_by_temporal`'s debouncer) straddles tasks and raises `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in`; it also leaves OTel spans dangling (the run span never closes in the task that opened it). The bridge instead keeps a **long-lived owner task** holding the CM open, and each streaming pass runs its entire `async for` in another long-lived task — all on the caller's event loop, preserving loop affinity of async clients/resources.

## Flow / Invariant
1. **Owner task** enters the CM once and parks on `exit_requested`; it returns `(stream, copy_context())` so child call/pump tasks inherit the context variables set by `__aenter__`.
2. **Pump tasks** run each full `async for` pass on the caller's loop; cancel scopes entered/exited inside never straddle tasks.
3. **Shutdown** (`_shutdown_loop`): cancel pump tasks, drive them to completion, then set `exit_requested` and drive the owner task to completion.
4. **Stale run_until_complete callbacks**: `_run_task_to_completion` retries `RuntimeError` while the waiter is still pending and this thread can still drive the loop; interrupts/base exceptions do best-effort cleanup then re-raise.
5. **Finalizer**: `_finalize_loop` handles callers that drop the wrapper without closing — if on the owner thread with no running loop, drives shutdown synchronously; otherwise `call_soon_threadsafe(request_exit)`.
6. **EndOfStream**: `_receive_one` converts `anyio.EndOfStream` to `_utils.UNSET` so it doesn't leak through a task traceback.

## Probe (direct test)
`tests/test_sync_stream_loop_affinity.py` (215L): `test_sync_entry_points_keep_async_client_on_one_event_loop` (:137) — a real keep-alive connection (VCR doesn't retain asyncio transport state) asserts the same client port is reused across sync-then-stream and stream-then-sync entry points, for both agent and direct surfaces and both provider/user client ownership. `test_async_run_and_stream_share_one_event_loop` (:193).

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'SyncStreamBridge'` → `_sync_stream.SyncStreamBridge.__init__` (197–243), `.shutdown` (264–273), `._run` (275–289).

## Verdict
**Adopt** the long-lived-owner-task pattern — it is the correct way to bridge async streaming CMs to sync code while preserving loop/task/cancel-scope affinity. A porter using per-step `run_until_complete(anext())` will hit cancel-scope straddling and dangling spans.
