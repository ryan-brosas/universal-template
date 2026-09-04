<!-- capsule-v2 -->
# Low-priority frontend routing — How does `router.frontend("/", directory="dist")` serve an SPA only after every API route misses, with dependencies applied?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** What is the match order that guarantees API routes win over static files, and when do frontend dependencies run?

## Two-phase dispatch: normal routes → low-priority routes
**Path/Symbol:** `fastapi/routing.py:APIRouter.app` (2719–2781; low-priority hook 2761–2781) + `_match_low_priority` (2811–2859) + `_FrontendRouteGroup.handle/_solve_dependencies` (2171–2252) + `_FrontendStaticFiles.get_response` (1946–1972).
**Signature:** `APIRouter.frontend(path, *, directory, fallback="auto", check_dir="auto") -> None`; `_FrontendRoute.matches_with_path(scope, path)` stores the matched sub-path in `scope["fastapi"]["frontend_path"]` + its length as `frontend_specificity`.
**Data Shape:** frontend mounts accumulate on `_low_priority_routes` (one `_FrontendRouteGroup` per router); included routers contribute their children's low-priority routes via `effective_low_priority_routes()` (same version-keyed cache pattern).

### Decisive source
```python
        for route in self.routes:                 # PHASE 1: normal + _IncludedRouter routes
            match, child_scope = route.matches(scope)
            if match == Match.FULL:
                scope.update(child_scope); await route.handle(...); return
            if match == Match.PARTIAL and partial is None:
                partial = (route, child_scope)
        ...redirect_slashes retry...
        (low_priority_match, low_priority_scope, low_priority_route,
         low_priority_context) = self._match_low_priority(scope)   # PHASE 2
        if low_priority_match != Match.NONE and low_priority_route is not None:
            ...
            if isinstance(original_route, APIRoute):
                scope["route"] = original_route
                await original_route.handle(scope, receive, send)
```
and in `_FrontendRouteGroup.handle`: dependencies solve inside freshly installed exit stacks (`fastapi_inner_astack`/`fastapi_function_astack` saved & restored in finally) ONLY on Match.FULL, then `response.background` adopts solved background tasks and dependency headers are merged.

**Flow:** normal FULL wins immediately; a PARTIAL from phase 1 still beats ALL frontend matches (405 method-mismatch case pinned by tests) → phase 2 picks the most SPECIFIC frontend prefix (longest `_frontend_path_specificity`) → static resolution ladder: exact file → dir/index.html (+ trailing-slash redirect for directory indexes) → `404.html` fallback (status 404) → `index.html` ONLY for navigation requests (Accept contains text/html|application/xhtml+xml with q≠0, parsed via email.message q-values) → else HTTPException 404. `check_dir="auto"` skips existence checks with a warning under `FASTAPI_ENV=development`.
**Invariant:** (1) Frontend dependencies must NOT run when an API route matches — they execute exclusively inside `_FrontendRouteGroup.handle` after both phases miss. (2) Specificity lives in child_scope, not on the group — cross-router comparisons use it to pick winners. (3) The SPA fallback is navigation-gated so `/api/missing.json` 404s instead of returning index.html.
**Probe:** `tests/test_frontend.py:test_normal_route_partial_match_wins_before_frontend`, `test_included_low_priority_routes_cache_is_reused`, `test_frontend_dependency_overrides_apply`, `test_index_fallback_ignores_invalid_q_value`.
