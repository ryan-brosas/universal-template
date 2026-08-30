<!-- capsule-v2 -->
# shielded continuation teardown — how does a server-side job get cancelled from inside an already-cancelling scope?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When workflow/task cancellation is what aborts a run holding a suspended background job, how do you guarantee the job's cancel HTTP call actually completes instead of leaking?

## cancel_suspended_job
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/_continuation.py:cancel_suspended_job` (:216-234); called from `_get_event_iterator` error path :461-468 and `close_stream` :555-565.
**Signature:** `async def cancel_suspended_job(model: Model, response: ModelResponse) -> None` (best-effort; swallows all non-cancel errors).
**Data Shape:** Wraps the model's `cancel_suspended_response(response)` (a no-op by default; only models with cancellable server-side jobs override) in an `asyncio.ensure_future` task.

### Decisive source
```python
# _continuation.py:225-234 — shield so the teardown finishes before cancellation propagates
job = asyncio.ensure_future(model.cancel_suspended_response(response))
try:
    await asyncio.shield(job)
except asyncio.CancelledError:
    # Our scope was cancelled mid-teardown; let the shielded cancel finish before propagating.
    with suppress(Exception):
        await job          # drain to completion — Temporal's workflow loop respects asyncio.shield
    raise                  # …then re-raise the original cancellation
except Exception:
    pass                   # a failing teardown must not REPLACE the error that aborted the run
```

**Flow:** schedule the model's cancel as a task → await it under `asyncio.shield`. Three outcomes: (a) completes normally → return; (b) an exception from the cancel itself is swallowed (best-effort: teardown failure must not mask the aborting error or cancellation); (c) the surrounding scope is cancelled mid-teardown → the shield keeps the job alive, the handler drains it to completion (`await job`, suppressing secondary errors), then re-raises the ORIGINAL `CancelledError`.

**Invariant:** The server-side job never leaks on cancellation, AND the caller's original exception/cancellation is always what propagates — teardown errors are never allowed to replace it. Without the shield, awaiting an activity-wrapped cancel inside an already-cancelled Temporal/asyncio scope raises `CancelledError` before the cancel runs.

**Probe:** `tests/models/test_continuation_stream.py::test_cancel_teardown_survives_scope_cancellation` (:996 — cancellation injected while parked in the teardown still runs the job cancel to completion); companion `::test_nonstream_continuation_cancel_failure_preserves_original_error` (:599).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "cancel_suspended_job cancel_suspended_response shield", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ensure_future + shield + drain-and-reraise ladder verbatim for any best-effort remote teardown racing scope cancellation; adapt only the wrapped call. Nothing to omit. Coverage clean at the pinned commit.
