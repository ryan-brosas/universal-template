<!-- capsule-v2 -->
# ASGI2 sniffing — how does auto interface detection distinguish ASGI3 from ASGI2 without running the app?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** What static inspection decides `asgi3` vs `asgi2`, and what false classifications must a porter guard against?

## Three-branch static probe on the callable
**Path/Symbol:** `uvicorn/config.py:Config.load` (:517–525); helper `uvicorn/_compat.py:iscoroutinefunction` (:7–13).
**Signature:** property logic over `self.loaded_app`; no app execution.
**Data Shape:** `self.loaded_app` may be a class, function, or arbitrary callable instance.

### Decisive source
```python
if self.interface == "auto":
    if inspect.isclass(self.loaded_app):
        use_asgi_3 = hasattr(self.loaded_app, "__await__")
    elif inspect.isfunction(self.loaded_app):
        use_asgi_3 = iscoroutinefunction(self.loaded_app)
    else:
        call = getattr(self.loaded_app, "__call__", None)
        use_asgi_3 = iscoroutinefunction(call)
    self.interface = "asgi3" if use_asgi_3 else "asgi2"
```
```python
# _compat.py — asyncio's version (accepts functools.partial) until 3.14, then inspect's
if sys.version_info >= (3, 14):
    from inspect import iscoroutinefunction
else:
    from asyncio import iscoroutinefunction
```

**Flow:** class ⇒ ASGI2-era instances expose `__await__` on the CLASS object only for old-style apps, so presence of `__await__` marks asgi3-compatible awaitable factories; plain function ⇒ coroutine-function check; anything else (callable object) ⇒ check its `__call__`. Failing all three probes classifies as asgi2 and gets the `ASGI2Middleware` adapter (`scope -> instance(scope)(receive, send)` shape).
**Invariant:** Detection never CALLS the app (side-effect safety); it only inspects. The `__call__` branch can misclassify an async `__call__` defined via `partial`-style wrappers — that's why uvicorn uses `asyncio.iscoroutinefunction` (<3.14), which unwraps partials, instead of `inspect`'s stricter variant.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'use_asgi_3 = hasattr' uvicorn/uvicorn/config.py"` → 1; `bash -c "grep -c 'from asyncio import iscoroutinefunction' uvicorn/uvicorn/_compat.py"` → 1.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"interface auto detect asgi3 asgi2 wsgi","limit":5,"detail":"ids"}` → resolves `Config.load` and `INTERFACES` usage line-exact.
**Verdict:** Adopt the three-branch static probe and the partial-tolerant predicate choice. Adapt to your framework's adapter vocabulary. Omit WSGI detection (explicit flag only in uvicorn).

