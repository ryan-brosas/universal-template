<!-- capsule-v2 -->
# Deferred tool-call handler capability — inline resolution with None-declines chaining

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/deferred_tool_handler.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When tools need approval or external execution, how do you offer an "resolve them inside this run" path WITHOUT breaking the default pause-and-return-DeferredToolRequests contract for hosts that can't resolve? A porter will make the handler mandatory and destroy the escape hatch.

## Path / Symbol
`capabilities/deferred_tool_handler.py` — `HandleDeferredToolCalls(AbstractCapability)` dataclass (:14–75): `handler: Callable[[RunContext, DeferredToolRequests], DeferredToolResults | None | Awaitable[...]]` (:51–54), `handle_deferred_tool_calls(ctx, *, requests) → results | None` (:66–75).

## Signature
```python
async def handle_deferred_tool_calls(self, ctx, *, requests: DeferredToolRequests) -> DeferredToolResults | None:
    result = self.handler(ctx, requests)
    if inspect.isawaitable(result):
        return await result
    return result
```

## Data Shape
Handler returns `DeferredToolResults` (partial allowed — some/all pending calls resolved; `requests.build_results(approve_all=True)` convenience) or `None`. The dispatch chain continues to later capabilities on None; if ALL decline, calls bubble up as `DeferredToolRequests` output exactly as if no handler existed.

### Decisive source
The decline semantics (docstring :26–28): "It may return DeferredToolResults with results for SOME or all pending calls, or return `None` to decline handling (the next capability in the chain gets a chance, otherwise the calls bubble up as `DeferredToolRequests` output)." Serialization name is None — handlers aren't spec-constructible.

**Flow:** Normal deferred flow pauses the run and surfaces requests. With this capability registered, each deferral is offered first to the handler chain (sync/async); a full-or-partial result feeds back into the run which CONTINUES without surfacing anything; partial results leave remainder pending. This is the in-process twin of external approval flows — same envelope types, different transport.

**Invariant:** Decline must be representable (None) and distinct from empty results; bubbling behavior is preserved verbatim when every handler declines.

**Probe:** `tests/test_capabilities.py` — imported/pinned at :39; exercised through approval/deferred e2e suites (test_deferred_tools* family). Coverage caveat: dedicated unit file absent; behavior pinned via integration tests of the deferred-tool pipeline this hooks into.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'HandleDeferredToolCalls DeferredToolRequests build_results'
```

## Verdict
**Adopt** None-declines chaining for any optional resolver hook. **Adopt** partial-result acceptance (resolve what you can, bubble the rest). **Omit** the approve_all convenience if your approval policy requires explicit per-call decisions.
