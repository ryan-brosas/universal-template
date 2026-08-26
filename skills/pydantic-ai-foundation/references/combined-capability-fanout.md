<!-- capsule-v2 -->
# CombinedCapability — capability fan-out: ordering, deferral gating, and middleware chain direction

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a porter composes multiple capabilities, what is the exact fan-out direction (before vs after/wrap/on-error), how are deferred capabilities skipped, and how does the middleware chain build from outermost to innermost?

## CombinedCapability fan-out contract
**Path/Symbol:** `pydantic_ai/capabilities/combined.py:CombinedCapability` (46-746), composition helpers `_make_*_wrap` (754-854), `_ctx_for_available_cap` (880-886), `_capability_loaded` (889-896).
**Signature:** `CombinedCapability(capabilities: Sequence[AbstractCapability])`; every lifecycle hook fan-outs over `self.capabilities`.
**Data Shape:** `capabilities` is flattened (nested `CombinedCapability`s are splatted) and optionally `sort_capabilities`-ordered in `__post_init__`.

### Decisive source
```python
# The universal fan-out pattern: before* in order, after*/wrap*/on_*_error in REVERSE.
async def before_run(self, ctx):
    for capability in self.capabilities:
        if (cap_ctx := _ctx_for_available_cap(capability, ctx)) is not None:
            await capability.before_run(cap_ctx)
async def after_run(self, ctx, *, result):
    for capability in reversed(self.capabilities):
        if (cap_ctx := _ctx_for_available_cap(capability, ctx)) is not None:
            result = await capability.after_run(cap_ctx, result=result)
    return result
async def wrap_run(self, ctx, *, handler):
    chain = handler
    for capability in reversed(self.capabilities):
        if _ctx_for_available_cap(capability, ctx) is not None:
            chain = _make_run_wrap(capability, ctx, chain)   # outermost first, innermost last
    return await chain()

def _ctx_for_available_cap(capability, ctx):
    capability_loaded = _capability_loaded(capability, ctx)
    if capability.defer_loading is True and not capability_loaded:
        return None          # skip unloaded deferred capability entirely
    return replace(ctx, capability_loaded=capability_loaded)
```

**Flow:** Every `before_*` hook iterates `self.capabilities` forward. Every `after_*`, `wrap_*`, and `on_*_error` iterates `reversed(self.capabilities)`. For `wrap_*`, the chain is built by wrapping the handler with each capability in reverse order, so the FIRST capability in `capabilities` is the OUTERMOST middleware and the LAST is INNERMOST (adjacent to the real operation). `_ctx_for_available_cap` returns `None` for a deferred capability that isn't loaded yet — that capability is skipped entirely for this hook. `on_*_error` chains: each capability's error hook runs in reverse; if it raises, the new error replaces the old and the next capability sees it; the last error is re-raised.
**Invariant:** before=forward, after/wrap/on-error=reverse. Deferred-and-unloaded capabilities are transparent (skipped). `wrap_*` builds outermost-first/innermost-last. `handle_deferred_tool_calls` accumulates results and breaks early when `remaining()` returns `None`.
**Probe:** `tests/test_capabilities.py` covers combined-capability ordering and deferral gating (e.g. deferred accumulation across two capabilities at :22576).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "CombinedCapability before_run after_run wrap_run reversed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the before-forward / after-wrap-error-reverse fan-out and the deferred-unloaded skip; adapt the `ctx.capabilities` registry and `_capability_loaded` to your host; omit nothing — the middleware chain direction is the portable invariant. Coverage clean.
