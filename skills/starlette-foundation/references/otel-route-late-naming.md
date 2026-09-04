<!-- capsule-v2 -->
# OpenTelemetry middleware — route-late span naming + re-entrancy guard

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** How does tracing get the ROUTE template when routing hasn't happened at request start, and how are nested/mounted apps kept single-span?

## OpenTelemetryMiddleware.__call__
**Path/Symbol:** `starlette/middleware/opentelemetry.py:OpenTelemetryMiddleware.__call__` (:21-98).
**Data Shape:** guards: non-http pass-through; `scope["starlette.opentelemetry"]` flag set/cleanup in finally (nested apps don't double-span); NoOp/Proxy tracer providers bypass entirely (zero overhead when untraced).
### Decisive source
```python
finally:
    route = scope.get("route")            # Router.app writes this AFTER matching
    if isinstance(route, Mount):
        route_path = scope.get("root_path") or "/"
    else:
        path_format = getattr(route, "path_format", None)
        route_path = (scope.get("root_path", "").rstrip("/") + path_format or "/" ...)
    if route_path is not None:
        span.update_name(f"{method} {route_path}")     # low-cardinality rename
        span.set_attribute("http.route", route_path)
```
**Flow:** span STARTS named by raw method with semconv attributes (`http.request.method`, `url.path`, `server.address/port`, `user_agent.original`, `network.protocol.version`); context extracted from headers via `propagate.extract` so upstream traceparents join. Response status recorded in the send shim; ≥500 marks span ERROR. Route template attached in FINALLY because routing completes mid-request — mounted requests fall back to root_path.
**Invariant:** `del scope["starlette.opentelemetry"]` runs even on exceptions — a leaked flag would permanently silence inner spans for that connection's scope dict lifetime.
**Probe:** `tests/middleware/test_opentelemetry.py` (full suite pins attributes, naming, error status).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "send_with_telemetry", limit: 5 });
```
(closure — resolve via file range :69-96 or the test module.)

## Verdict
Adopt the late-route-rename pattern for any per-request telemetry over a router. Adopt the re-entrancy flag for composable apps. Adapt attribute names as semconv versions move.
