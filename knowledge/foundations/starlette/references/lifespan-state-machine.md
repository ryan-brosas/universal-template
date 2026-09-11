<!-- capsule-v2 -->
# Router.lifespan protocol — the state-machine behind startup/shutdown

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** What ASGI lifespan messages must a porter exchange, in what order, and how do failures map to `startup.failed` vs `shutdown.failed`?

## Router.lifespan
**Path/Symbol:** `starlette/routing.py:Router.lifespan` (:639-664).
**Signature:** `async def lifespan(self, scope: Scope, receive: Receive, send: Send) -> None`.
**Data Shape:** consumes exactly two receives (`lifespan.startup`, then `lifespan.shutdown`); emits one of `{startup.complete, startup.failed, shutdown.complete, shutdown.failed}` with `message` = `traceback.format_exc()` text on failure.

### Decisive source
```python
started = False
await receive()                       # lifespan.startup
try:
    async with self.lifespan_context(app) as maybe_state:
        if maybe_state is not None:
            if "state" not in scope:
                raise RuntimeError('The server does not support "state" in the lifespan scope.')
            scope["state"].update(maybe_state)
        await send({"type": "lifespan.startup.complete"})
        started = True
        await receive()               # blocks until shutdown
except BaseException:
    exc_text = traceback.format_exc()
    if started:
        await send({"type": "lifespan.shutdown.failed", "message": exc_text})
    else:
        await send({"type": "lifespan.startup.failed", "message": exc_text})
    raise                              # failure is SENT and RE-RAISED
else:
    await send({"type": "lifespan.shutdown.complete"})
```

**Flow:** the `started` latch is the discriminator — an exception inside `__aenter__` (or the state merge) → `startup.failed`; an exception inside the body/`__aexit__` after startup completed → `shutdown.failed`. Stateful lifespans (async CMs returning a dict) get their dict merged into `scope["state"]`, which servers copy into every request scope.
**Invariant:** re-raise AFTER sending the failure message so servers can also log; a porter who swallows the exception leaves the server hanging; one who forgets the send leaves the test client asserting on a message that never came.
**Probe:** `tests/test_routing.py::test_lifespan_state_async_cm` (:645) pins state merging; `::test_raise_on_startup` (:693) / `::test_raise_on_shutdown` (:717) pin both failure branches.

## Lifespan normalization ladder (Router.__init__)
**Path/Symbol:** `starlette/routing.py:Router.__init__` lifespan branch (:590-607) + `_DefaultLifespan` (:559-570), `_wrap_gen_lifespan_context` (:547-556), `_AsyncLiftContextManager` (:531-544).
**Data Shape:** `None` → `_DefaultLifespan` (no-op async CM whose `__call__` returns itself); bare async-generator function → DEPRECATION WARNING then `contextlib.asynccontextmanager`; bare sync generator → warning + wrapped into `_AsyncLiftContextManager` (sync `__enter__` run eagerly inside an async facade); anything else used as-is.
**Invariant:** all four shapes converge to `Callable[[app], AbstractAsyncContextManager[MaybeState]]`; `_DefaultLifespan.__call__: self → self` trick lets it double as its own bound factory without per-request allocation.
**Probe:** `tests/test_applications.py::test_app_async_cm_lifespan` (:390), `::test_app_async_gen_lifespan` (:422, expects warning), `::test_app_sync_gen_lifespan` (:444).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "lifespan", limit: 20 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "_wrap_gen_lifespan_context", limit: 5 });
```

## Verdict
Adopt the message protocol verbatim (it's dictated by the ASGI spec) plus the started-latch failure mapping. Adopt the normalization ladder if you accept multiple user styles. Adapt the `scope["state"].update` merge point if your server passes state differently. Omit the deprecated generator paths when you control all call sites.
