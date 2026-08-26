<!-- capsule-v2 -->
# Wrapper vs Pipeline — when does middleware need re-invocable next()?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** Why is the LLM-call retry policy a different composition primitive than every other hook, and how is it composed?

## Nested closures for wrap semantics; single-pass continuation for everything else
**Path/Symbol:** `backend/python/app/agent_loop_lib/hooks/middleware/wrapper.py:Wrapper.compose` (L42–54); `backend/python/app/agent_loop_lib/hooks/registry.py:_WRAPPER_EVENTS` (L31).
**Signature:** `WrapMiddleware = Callable[[WrapNext[T]], Awaitable[T]]`; `compose(terminal: WrapNext[T]) -> WrapNext[T]`.

```python
def compose(self, terminal: "WrapNext[T]") -> "WrapNext[T]":
    handler = terminal
    for mw in reversed(self._stack):
        handler = self._bind(mw, handler)
    return handler

@staticmethod
def _bind(mw, next_handler):
    async def bound() -> T:
        return await mw(next_handler)
    return bound
```

**Data Shape:** `use(mw)` appends to a plain list; first-registered = outermost (its pre-`next` code runs first, its post-`next` code runs last). `terminal` is the actual action being wrapped (the real LLM call) taking no args. Contrast with `Pipeline`: `(matcher, middleware)` pairs + per-event `is_terminal`/`fail_closed`; a Pipeline's `Next = Callable[[], Awaitable[None]]` returns nothing and can only be consumed.

### Decisive source
```python
# wrapper.py module docstring (L2-8): "Pipeline ... is a *single-pass* next()
# continuation: once a middleware calls next(), that step of the chain is
# consumed and can't be re-invoked — which is exactly right for gate/observe/
# reducer semantics ..., but wrong for a middleware like a retry policy that
# needs to call 'the rest of the chain' an arbitrary number of times."
```

**Flow:** ControlPlane step 6 registers `kernel.wrapper(PRE_MODEL_CALL).use(retry_model_call(RetryConfig(...)))` → at call time the agent loop builds `handler = kernel._wrappers[PRE_MODEL_CALL].compose(actual_llm_call)` → awaiting `handler()` runs retry's before-code → invokes inner (possibly several times with backoff) → returns the final result outward through each layer.

**Invariant:** exactly ONE event uses Wrapper; adding a second wrap event means adding to `_WRAPPER_EVENTS`, not shoehorning retry semantics into a Pipeline (a Pipeline middleware literally cannot re-run downstream steps). Wrapper composition order is reversed at compose time so registration order reads naturally (first = outermost); getting this backwards makes backoff surround the wrong calls.
**Probe:** `tests/unit/agents/adapter/test_factory_wiring.py:121` asserts a factory wiring preserves `ControlPlane`'s default `retry_model_call` wrapping behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "Wrapper compose retry_model_call PRE_MODEL_CALL", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-primitive split and `reversed(stack)` composition. Adapt RetryConfig fields/backoff curve to host. Omit the concrete retry policy internals if your transport already retries. Coverage caveat: pipeline/wrapper engines have no isolated unit tests in-repo; the pinned probe is the wiring-level assertion above plus transitively via every kernel-driving test.
