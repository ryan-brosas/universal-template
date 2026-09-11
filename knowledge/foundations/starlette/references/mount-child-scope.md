<!-- capsule-v2 -->
# Mount child-scope rewrite — how does root_path grow and why does app_root_path exist?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** When a request enters a Mount, exactly which scope keys change, and what must a porter preserve so `request.url_for` still builds correct URLs?

## Mount.matches — the scope surgery
**Path/Symbol:** `starlette/routing.py:Mount.matches` (:394-425); construction at :376-388 compiles `self.path + "/{path:path}"`.
**Data Shape:** regex match yields `{path}` (the remainder) plus any mount params; the code pops `"path"` back out: `remaining_path = "/" + matched_params.pop("path")`; `matched_path = route_path[: -len(remaining_path)]`.

### Decisive source
```python
child_scope = {
    "path_params": path_params,
    "app_root_path": scope.get("app_root_path", root_path),
    "root_path": root_path + matched_path,
    "endpoint": self.app,          # NOTE: the mounted ASGI app, not an endpoint fn
}
return Match.FULL, child_scope
```

**Flow:** mount params convert like Route params; `path_params` MERGE with inherited ones; `root_path` accumulates the matched prefix so nested mounts compose; the original `scope["path"]` is left untouched — inner apps call `get_route_path(scope)` to re-derive their local path by stripping `root_path`.
**Invariant:** `app_root_path` is written ONCE (only if absent) with the TOP-level root_path, so every nested child still sees the outermost prefix — this is what `HTTPConnection.base_url` uses for absolute URL building. A porter who overwrites it per-mount breaks `url_for` under nested mounts.
**Probe:** `tests/test_routing.py::test_url_for_with_double_mount` (:564) pins two-level composition; `::test_mount_urls` (:376) pins prefix stripping.

## get_route_path — root_path stripping ladder
**Path/Symbol:** `starlette/_utils.py:get_route_path` (:96-111).
### Decisive source
```python
if not root_path:            return path
if not path.startswith(root_path):  return path
if path == root_path:        return ""
if path[len(root_path)] == "/":     return path[len(root_path):]
return path                  # prefix matches but next char != "/" → don't strip
```
**Invariant:** stripping is char-boundary safe (`/files` must NOT strip from `/files2`); empty-string return for exact-root hits keeps `Route("/")` matchable inside a mount.
**Probe:** `tests/test__utils.py` pins the boundary cases (10 tests incl. no-strip-on-prefix-without-slash).

## Host route
**Path/Symbol:** `starlette/routing.py:Host.matches` (:478-491).
**Data Shape:** reads the `host` HEADER, strips `:port`, fullmatches against a host-pattern regex built by the SAME `compile_path` (so subdomains can carry typed params). Child scope gets converted `path_params` + `endpoint=self.app`; it does NOT touch root_path.
**Flow:** compile_path's host branch anchors on hostname only (`split(":")[0]`) aligning with header parsing.
**Probe:** `tests/test_routing.py::test_subdomain_routing` (:504), `::test_host_reverse_urls` (:479).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "get_route_path", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "matches", limit: 20 });
```

## Verdict
Adopt the three-key child-scope contract (`path_params` merged, `root_path` accumulated, `app_root_path` write-once) and the conservative strip ladder. Adapt param merging if your framework namespaces per-level params. Omit `Mount.routes` introspection property only when you don't need schema/reverse-routing over mounts.
