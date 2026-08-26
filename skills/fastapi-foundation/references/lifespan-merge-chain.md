<!-- capsule-v2 -->
# Lifespan merge chain — How do router lifespans and on_startup/on_shutdown compose into the app's single lifespan context?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** What runs at startup/shutdown when sub-routers define their own lifespans, and what does a merged lifespan yield?

## _merge_lifespan_context + vendored _DefaultLifespan
**Path/Symbol:** `fastapi/routing.py:_AsyncLiftContextManager` (193–212), `_wrap_gen_lifespan_context` (216–230), `_merge_lifespan_context` (233–247), `_DefaultLifespan` (250–271); wiring in `include_router` (3317–3320) and `APIRouter.__init__` lifespan default.
**Signature:** `_merge_lifespan_context(original_context: Lifespan[Any], nested_context: Lifespan[Any]) -> Lifespan[Any]`.
**Data Shape:** `Lifespan` = callable(app) → async CM yielding `Mapping[str, Any] | None`; sync generator lifespans are lifted via the vendored `_AsyncLiftContextManager` (Starlette removed its private copy).

### Decisive source
```python
    @asynccontextmanager
    async def merged_lifespan(app: AppType) -> AsyncIterator[Mapping[str, Any] | None]:
        async with original_context(app) as maybe_original_state:
            async with nested_context(app) as maybe_nested_state:
                if maybe_nested_state is None and maybe_original_state is None:
                    yield None                       # old ASGI compatibility
                else:
                    yield {**(maybe_nested_state or {}), **(maybe_original_state or {})}
```

**Flow:** each `include_router` folds the child's lifespan INTO the parent: `self.lifespan_context = _merge_lifespan_context(self.lifespan_context, router.lifespan_context)` → startup enters parent CMs outermost, then children in include order; shutdown unwinds in reverse → legacy `on_startup`/`on_shutdown` lists ride the vendored `_DefaultLifespan` (calls `router._startup()/_shutdown()`), copied eagerly to the parent via `add_event_handler`, while modern generator lifespans ride the merge chain.
**Invariant:** (1) Yielding `{}` vs `None` matters: two Nones yield None for ASGI-compat; any dict produces a merged mapping where ORIGINAL (outer) state overrides NESTED keys. (2) The merge is associative but order-sensitive for state precedence — later includes wrap earlier ones as the OUTER context. (3) A raising child shutdown still lets outer contexts unwind (structured concurrency via `async with` nesting).
**Probe:** `tests/test_router_events.py:test_router_nested_lifespan_state`, `test_merged_no_return_lifespans_return_none`, `test_merged_mixed_state_lifespans` pin both yield conventions and nesting order.
