<!-- capsule-v2 -->
# Anyio-cancel-safe activity execution — shielded handle + exactly-one graceful cancel

## Source / Question
`pydantic_ai_slim/pydantic_ai/durable_exec/temporal/_activity_execution.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Awaiting a durable-engine activity handle directly from a task inside an anyio cancel scope can livelock the whole workflow — how do you keep cancellation delivery on YOUR task while still cancelling the remote unit exactly once? A porter will `await execute_activity(...)` bare and inherit the spin: scope re-cancels every loop turn, the engine's resolution can never arrive, deadlock detector kills the workflow, which retries identically forever.

## Path / Symbol
`_activity_execution.py` — `execute_activity` (:38–53), module docstring documenting the failure mechanism (:1–23).

## Signature
```python
async def execute_activity(activity: Any, *, args: Sequence[Any], **config: Unpack[ActivityConfig]) -> Any:
    handle = workflow.start_activity(activity, args=args, **config)   # start, don't await
    try:
        return await asyncio.shield(handle)
    except asyncio.CancelledError:
        if not handle.done():
            handle.cancel()                                # exactly one graceful cancel
            with anyio.CancelScope(shield=True):
                await asyncio.wait([handle])               # wait for configured resolution
        raise                                              # original CancelledError propagates
```

## Data Shape
`handle` is the engine's `ActivityHandle` (started activity). The shield flips WHO receives cancellation: without it `task.cancel()` delegates into the handle task, whose loop swallows `CancelledError`, emits `request_cancel_activity`, and re-parks on a shielded future — leaving the scoped task uncancelled with an undone waiter, so anyio (level-triggered: re-arms via `call_soon` while the scope lives) cancels it again next iteration.

### Decisive source — the whole body (:40–53, verbatim above)
The already-done arm (`handle.done()` check) covers the real race of cancel landing in the same tick the activity resolves — untestable deterministically through the workflow API (`# pragma: no branch`).

**Flow:** start → shielded await → if cancelled: forward ONE cancel to Temporal → wait inside a SHIELDED anyio scope for the configured `ActivityCancellationType` resolution (re-delivery stops; activation completes) → re-raise. Re-raising the original keeps asyncio semantics at callers: `asyncio.wait_for` yields `TimeoutError`, not a leaked `ActivityError`; cancelling the Temporal workflow still ends it as *Cancelled*.

**Invariant:** Cancellation must be delivered by OUR task (shield) and delegated to the engine EXACTLY once; the resolution wait must be anyio-shielded or level-triggered redelivery resumes the spin; never swallow or replace the caller's `CancelledError`.

**Probe:** `tests/test_temporal.py::test_anyio_scope_cancel_of_activity_await_does_not_wedge` (:528 — in-flight agent run under `asyncio.wait_for` must not wedge), `test_temporal_cancellation_backstop_survives_absorbed_activity_cancel` (:657 — `_cancellation_activity_cancel_absorbed` fixture model at :449–476).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'execute_activity shield CancelledError CancelScope'
```

## Verdict
**Adopt** the pattern wholesale for ANY durable engine whose client SDK parks cancellations on an internal task (Temporal today; same shape applies wherever an SDK "swallows and forwards" cancel). **Adapt** the handle API names. **Omit** nothing — this is 53 lines that prevent an infinite retry loop.
