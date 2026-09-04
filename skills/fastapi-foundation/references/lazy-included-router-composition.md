<!-- capsule-v2 -->
# Lazy included-router composition — Why does include_router no longer copy routes, and how do prefix/tags/dependencies apply at match time instead?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** How can routes added to a sub-router AFTER `include_router` still appear in the parent app with correct prefixes and defaults?

## _IncludedRouter + version-keyed effective cache
**Path/Symbol:** `fastapi/routing.py:include_router` (3133–3320, append at 3309–3312) + `_RouterIncludeContext.for_include/combine` (1305–1367) + `_IncludedRouter.effective_candidates` (1601–1624) + `_EffectiveRouteContext.from_api_route` (1425–1478).
**Signature:** `include_router(router, *, prefix="", tags=None, dependencies=None, ...) -> None` — appends ONE `_IncludedRouter(original_router, include_context)`; `_RouterIncludeContext.combine(child)` merges nested include metadata.
**Data Shape:** effective candidates cached under `_effective_candidates_version`, invalidated by comparing against `_get_routes_version()` = sum of the router's own `_routes_version` (bumped by EVERY add_*/include_router/frontend mutation) plus all transitively included routers' versions (cycle-guarded via `seen: set[int]`).

### Decisive source
```python
        self.routes.append(
            _IncludedRouter(original_router=router, include_context=include_context)
        )
        self._mark_routes_changed()
```
```python
    def effective_candidates(self):
        routes_version = self.original_router._get_routes_version()
        if routes_version == self._effective_candidates_version:
            return self._effective_candidates          # fast path
        with self._effective_routes_lock:
            routes_version = self.original_router._get_routes_version()  # re-check under lock
            ...
            for route in self.original_router.routes:
                if isinstance(route, _IncludedRouter):
                    child_context = self.include_context.combine(route.include_context)
                    ...append child branch...
                route_context = self._build_effective_context(route)  # rebuild _EffectiveRouteContext
```

**Flow:** matching descends parent router → `_IncludedRouter.matches/handle` stash themselves in scope (`fastapi.included_router`) then delegate to the ORIGINAL router's iteration over its LIVE routes; each APIRoute is matched through a freshly composed `_EffectiveRouteContext` (prefix applied via `_populate_api_route_state(path=include_context.path_for(route), tags=[...], dependencies=[...], responses={**parent, **route}, get_value_or_default ladder for response_class/generate_unique_id/strict_content_type)`) → during matching the context is injected into `scope["fastapi"]["effective_route_context"]` and restored in `finally`; `APIRoute.get_route_handler()` reads it via ContextVar to build the request handler from EFFECTIVE (prefixed, dependency-extended) state.
**Invariant:** (1) The double-checked version compare must happen BOTH outside and inside the lock — the outer check is just an optimization. (2) Cycle protection is two-layered: `include_router` asserts self-inclusion and reverse containment (`_contains_router`) at authoring time; `_get_routes_version(seen)` guards id-cycles at invalidation time. (3) Startup/shutdown handlers are still copied eagerly (`add_event_handler`) and lifespans merged via `_merge_lifespan_context` — nesting semantics live on the app, not the lazy route tree.
**Probe:** `tests/test_include_router_defaults_overrides.py` + `tests/test_ws_router.py:test_native_prefix_router`; late-added-route behavior pinned by `tests/test_openapi_route_extensions.py`.
