<!-- capsule-v2 -->
# copy_current_request_context — how is the context handed to a background thread safely?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What does each spawned worker receive, and what are the documented race boundaries?

## Copy-then-push wrapper
**Path/Symbol:** `src/flask/ctx.py:copy_current_request_context` (154–206); `AppContext.copy` (355–368).
**Signature:** decorator `copy_current_request_context(f) -> f'` where `f'(*args, **kwargs)` pushes a COPY of the captured context then runs `ensure_sync(f)`.
**Data Shape:** captures `original = _cv_app.get(None)` at decoration time; `copy()` re-wraps the SAME `_request`/`_session` objects in a NEW AppContext (fresh g, fresh token/count).

### Decisive source
```python
original = _cv_app.get(None)
if original is None:
    raise RuntimeError("'copy_current_request_context' can only be used ...")
def wrapper(*args, **kwargs):
    # Copy the context before pushing, so each worker acts independently.
    with original.copy() as ctx:
        return ctx.app.ensure_sync(f)(*args, **kwargs)
```

**Flow:** decorate inside view → spawn `wrapper` on executor/thread → each worker copies (independent push bookkeeping) → runs with request/session/current_app visible → pop on exit. Docstring-mandated cautions: read `form`/`json`/`data` BEFORE spawning (body single-consumption race), touch session in the parent too (so Vary: Cookie is set) and never write session from the task (may run after cookie written).
**Invariant:** workers must NOT share one pushed context — copying prevents ContextVar token cross-talk; the request object itself IS shared, hence the read-before-spawn rule for body data.
**Probe:** `grep -Fc '# Copy the context before pushing, so each worker acts independently.' src/flask/ctx.py` = 1; test `tests/test_reqctx.py::test_copy_context_thread` (:147) runs 10 worker tasks through a ThreadPoolExecutor asserting request/session visibility.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "copy_current_request_context thread executor", limit: 4 });
```

## Verdict
Adopt copy-per-worker + capture-at-decoration. Adapt ensure_sync to your runner. Omit the gevent example (doc prose).
