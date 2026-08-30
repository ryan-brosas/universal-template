<!-- capsule-v2 -->
# create_collapsing_task_group + threadpool iterators — anyio exception-group ergonomics

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** Why does Starlette unwrap single-exception ExceptionGroups, and how do sync iterators stream without poisoning the loop?

## create_collapsing_task_group
**Path/Symbol:** `starlette/_utils.py:create_collapsing_task_group` (:82-93).
**Signature:** `@asynccontextmanager async def ... -> AsyncGenerator[anyio.abc.TaskGroup, None]`.
### Decisive source
```python
async with anyio.create_task_group() as tg:
    yield tg
# on exit, anyio raises BaseExceptionGroup:
except BaseExceptionGroup as excs:
    if len(excs.exceptions) != 1:
        raise                                  # genuine multi-failure: keep the group
    exc = excs.exceptions[0]
    context = None if exc.__suppress_context__ else exc.__context__
    raise exc from exc.__cause__ or context   # re-raise THE exception, not a 1-wrap group
```
**Flow:** used by BaseHTTPMiddleware, StreamingResponse's disconnect race, and WSGIMiddleware — everywhere "first task to finish decides" semantics exist. Single-failure groups collapse so user code sees the ORIGINAL exception type (except clauses match); multi-failure groups stay groups.
**Invariant:** `raise exc from cause-or-context` preserves traceback chaining minus the noise; suppressing `__context__` when `__suppress_context__` honors user `raise ... from None`.
**Probe:** `tests/test_concurrency.py` pins collapse vs multi behavior.

## run_in_threadpool / iterate_in_threadpool / _StopIteration coercion
**Path/Symbol:** `starlette/concurrency.py:run_in_threadpool` (:32-34), `_next` (:41-48), `iterate_in_threadpool` (:51-59).
### Decisive source
```python
def _next(iterator):
    try:    return next(iterator)
    except StopIteration:
        raise _StopIteration     # StopIteration raised inside a coroutine/generator
                                 # turns into RuntimeError — coerce to a private type
...
yield await anyio.to_thread.run_sync(_next, as_iterator)
```
**Flow:** every sync endpoint/iterator crossing into async land goes through these two functions; `functools.partial(func, *args)` binds kwargs for `run_sync` which takes no kwargs.
**Invariant:** NEVER let raw `StopIteration` escape a threadpool callback into async code — PEP 479 makes it a RuntimeError that destroys the generator. The `_StopIteration` rename is the whole trick.
**Probe:** `tests/test_concurrency.py`; exercised by every sync-endpoint test (`tests/test_routing.py::test_partial_async_endpoint` covers the partial+sync path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "create_collapsing_task_group", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "_StopIteration", limit: 5 });
```

## Verdict
Adopt both kernels verbatim regardless of framework — they fix Python-level footguns (PEP 479, ExceptionGroup opacity), not Starlette specifics. Adapt the limiter/pool choice if not on anyio.
