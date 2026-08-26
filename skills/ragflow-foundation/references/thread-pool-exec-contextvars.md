<!-- capsule-v2 -->
# thread-pool-exec-contextvars — why not asyncio.to_thread or a shared executor?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ext-ragflow`. **Question:** What does thread_pool_exec guarantee that naive wrappers break?

## Per-call executor + explicit context propagation
**Path/Symbol:** `common/misc_utils.py:245-260` (`thread_pool_exec`); contrast helper `thread_pool_exec_long_time` `:263+`.
**Signature:** `async def thread_pool_exec(func, *args, **kwargs)`.
**Data Shape:** kwargs presence switches between `functools.partial` form and direct arg forwarding — both run under `ctx.run`.

### Decisive source
```python
# loop.run_in_executor() submits the callable without propagating the caller's
# contextvars (unlike asyncio.to_thread, which copies the context). Copy the
# current context and run the callable inside it so ContextVars set by the
# caller (e.g. tracing / per-request state) are visible in the worker thread.
#
# Use a short-lived executor per call instead of a shared singleton. Python
# 3.13's executor reuse can deadlock in this environment when the same helper
# is awaited repeatedly inside one event loop.
loop = asyncio.get_running_loop()
ctx = contextvars.copy_context()
with ThreadPoolExecutor(max_workers=1) as executor:
    if kwargs:
        inner = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, ctx.run, inner)
    return await loop.run_in_executor(executor, ctx.run, func, *args)
```

**Flow:** every Dealer/store call (`dataStore.search`, embeddings, metadata loads) goes through this wrapper; the comment documents BOTH reasons — contextvars loss in raw run_in_executor AND a Py3.13 shared-executor reuse deadlock observed in this exact environment. Long-lived work must instead use `thread_pool_exec_long_time` because the short-lived `with` block's shutdown(wait=True) can swallow request cancellation.
**Invariant:** contextvars set by callers are visible inside worker threads; per-call executor lifetime means no cross-request thread state leaks. A porter swapping in `asyncio.to_thread` gets context for free but loses nothing — swapping in bare run_in_executor silently breaks tracing/request-scoped ContextVars.
**Probe:** `grep -n 'contextvars.copy_context()' common/misc_utils.py` → 1 hit :255; `sed -n '251,253p' common/misc_utils.py | grep -c 'Python' ` → 1 (deadlock note present); `grep -n 'def thread_pool_exec\b' common/misc_utils.py` → 1 hit :245. Executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ragflow", query: "thread_pool_exec contextvars executor", limit: 5, fields: ["signature", "file"] });
```

## Verdict
Adopt ctx.run wrapping as-is; adapt executor sizing to your workload; omit only if your runtime guarantees context propagation natively — then document the divergence in-source like upstream does.
