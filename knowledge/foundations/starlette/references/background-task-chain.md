<!-- capsule-v2 -->
# BackgroundTask/BackgroundTasks — post-response execution contract

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** When exactly do background tasks run, what happens if one raises, and how do sync tasks execute?

## BackgroundTask + BackgroundTasks
**Path/Symbol:** `starlette/background.py:BackgroundTask` (:12-23), `BackgroundTasks` (:26-36).
**Signature:** `BackgroundTask(func, *args, **kwargs)`; is_async frozen at CONSTRUCTION via `is_async_callable`.
### Decisive source
```python
async def __call__(self) -> None:
    if self.is_async: await self.func(*self.args, **self.kwargs)
    else:             await run_in_threadpool(self.func, *self.args, **self.kwargs)

class BackgroundTasks(BackgroundTask):
    async def __call__(self) -> None:
        for task in self.tasks:      # SEQUENTIAL, first exception stops the chain
            await task()
```
**Flow:** invoked at the tail of Response.__call__ (:169-170 responses.py), StreamingResponse.__call__ after stream completion (:282), _StreamingResponse after body drain (:243-244 base.py) — i.e., AFTER the final ASGI message but INSIDE the app call, so the server hasn't closed the connection and errors propagate to ServerErrorMiddleware (which can no longer change the response — response-started latch applies).
**Invariant:** sequential-not-concurrent; a raising task skips the rest. Porters wanting isolation must wrap tasks themselves.
**Probe:** `tests/test_background.py`; `tests/middleware/test_errors.py::test_background_task` (:83) pins error propagation through the 500 middleware.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "BackgroundTask", limit: 10 });
```

## Verdict
Adopt the run-after-final-message placement and construction-time async detection. Adapt by adding per-task isolation/error collection if your jobs are unreliable. Omit BackgroundTasks subclass for single-task frameworks.
