<!-- capsule-v2 -->
# OpenAPI schema caching — When is the schema regenerated, and how does the /openapi.json handler inject the root-path server?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** How does `app.openapi()` avoid regenerating on every request, and what makes it pick up routes added later?

## Version-checked memoization
**Path/Symbol:** `fastapi/applications.py:FastAPI.openapi` (1070–1103) + init fields `self.openapi_schema = None` / `self._openapi_routes_version = None` (924–925) + `setup()` openapi route (1105–1122).
**Signature:** `openapi(self) -> dict[str, Any]`; guard: regenerate iff `not self.openapi_schema or self._openapi_routes_version != routes_version` where `routes_version = self.router._get_routes_version()`.
**Data Shape:** cached document stored on the app; docs UI routes registered in `setup()` with `include_in_schema=False`.

### Decisive source
```python
        routes_version = self.router._get_routes_version()
        if not self.openapi_schema or self._openapi_routes_version != routes_version:
            self.openapi_schema = get_openapi(...)
            ...
            self._openapi_routes_version = routes_version
        return self.openapi_schema
```
```python
            async def openapi(req: Request) -> JSONResponse:
                root_path = req.scope.get("root_path", "").rstrip("/")
                schema = self.openapi()
                if root_path and self.root_path_in_servers:
                    server_urls = {s.get("url") for s in schema.get("servers", [])}
                    if root_path not in server_urls:
                        schema = dict(schema)      # shallow copy per request
                        schema["servers"] = [{"url": root_path}] + schema.get("servers", [])
                return JSONResponse(schema)
```

**Flow:** any route mutation (add_api_route/include_router/frontend/websocket) bumps `_routes_version`, so the next `/openapi.json` call rebuilds — this is what makes lazy router composition safe for docs → otherwise the SAME dict object is returned, so callers who mutate `app.openapi_schema` intentionally customize it persistently (documented extension hook) → root_path injection prepends a servers entry only when missing, on a shallow copy so the cache never sees the mutated shape.
**Invariant:** (1) The version check must compare against `_get_routes_version()` (recursive sum over included routers), NOT just the top-level counter — nested mutations would otherwise be missed. (2) Customizing via an `openapi()` override should still set/return `app.openapi_schema` to keep the single-cache invariant. (3) `setup()` runs once at app construction; disabling `openapi_url` removes docs AND validation asserts on title/version.
**Probe:** `tests/test_openapi_route_extensions.py` (schema reflects late additions) and application suites pinning `servers` behavior under mounted sub-apps (`tests/test_sub_apps.py`).
