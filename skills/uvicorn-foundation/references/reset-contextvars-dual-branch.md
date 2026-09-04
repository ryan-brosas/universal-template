<!-- capsule-v2 -->
# reset_contextvars dual-branch — why does the contextvars leak workaround differ between Python 3.10 and 3.11+?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae` (opt-in flag; cpython#140947); Codebase Memory `ext-uvicorn`. **Question:** What are the two task-creation forms, and which Python versions take which?

## create_task(context=...) on ≥3.11; Context().run(create_task, ...) below
**Path/Symbol:** identical block in all four HTTP impls — `httptools_impl.py:303–309`, `h11_impl.py:257–263`, `zttp_impl.py:202–208`, `zttp_h2_impl.py:247–253`.
**Signature:** `if sys.version_info >= (3, 11): task = self.loop.create_task(coro, context=contextvars.Context()) else: task = contextvars.Context().run(self.loop.create_task, coro)`.
**Data Shape:** `config.reset_contextvars: bool = False` (CLI `--reset-context-vars`, main.py help: "Run each ASGI request in a fresh contextvars.Context. Hides context set in the lifespan.").

### Decisive source
```python
# httptools_impl.py :303-309 — both arms produce an isolated-context task
if self.config.reset_contextvars:
    # Opt-in workaround for https://github.com/python/cpython/issues/140947:
    # asyncio can leak context vars between tasks. Hides context set in the
    # lifespan or by external instrumentation.
    if sys.version_info >= (3, 11):
        task = self.loop.create_task(cycle.run_asgi(app), context=contextvars.Context())
    else:
        task = contextvars.Context().run(self.loop.create_task, cycle.run_asgi(app))
else:
    task = self.loop.create_task(cycle.run_asgi(app))
task.add_done_callback(self.tasks.discard)
self.tasks.add(task)
```

**Flow:** default path creates tasks inheriting the CURRENT context (lifespan state visible to requests). With the flag ON and Python ≥3.11: a fresh empty `Context()` is passed via the native `create_task(..., context=)` kwarg. On 3.10 (no context kwarg): the SAME effect is achieved by entering a fresh Context around the create_task call so the task copies THAT instead. Every request gets its own blank slate either way.
**Invariant:** The two branches are semantically equivalent but NOT syntactically portable in either direction — using `context=` below 3.11 raises TypeError; wrapping `.run()` above 3.11 works but is redundant. Task bookkeeping (`tasks.add` + done-callback discard) applies to ALL branches so graceful shutdown still sees flagged tasks.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'contextvars.Context()' uvicorn/uvicorn/protocols/http/httptools_impl.py"` → 2 (both branch arms); same → 2 for h11/zttp/zttp_h2 impls. Behavioral pins: `tests/test_server.py:test_reset_contextvars_asyncio` :229 and `tests/protocols/test_http2.py:test_reset_contextvars_runs_each_stream_in_a_fresh_context` :847.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"reset contextvars fresh context task","limit":5,"detail":"ids"}` → resolves the four impl sites + direct tests line-exact.
**Verdict:** Adopt BOTH branch shapes verbatim if you support 3.10; otherwise collapse to the kwarg form. Adapt the flag name. Omit the cpython-issue rationale beyond the pointer.

