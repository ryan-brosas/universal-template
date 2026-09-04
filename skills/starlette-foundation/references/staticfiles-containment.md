<!-- capsule-v2 -->
# StaticFiles path containment + 304 revalidation

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** How does a static file mount prevent directory traversal, and when exactly does it answer 304 instead of streaming bytes?

## StaticFiles.lookup_path — realpath + commonpath gate
**Path/Symbol:** `starlette/staticfiles.py:lookup_path` (:154-173); `get_path` (:101-107) normalizes `route_path` segments (`os.path.normpath(os.path.join(*path.split("/")))`) BEFORE lookup.
### Decisive source
```python
if path.startswith(("/", "\\")):        # absolute → reject outright
    return "", None
for directory in self.all_directories:
    joined_path = os.path.join(directory, path)
    if self.follow_symlink:
        full_path = os.path.abspath(joined_path)     # symlink escape ALLOWED by opt-in
        directory = os.path.abspath(directory)
    else:
        full_path = os.path.realpath(joined_path)    # resolve symlinks...
        directory = os.path.realpath(directory)      # ...and compare resolved roots
    if os.path.commonpath([full_path, directory]) != str(directory):
        continue                                     # escaped the root → next candidate
```
**Flow:** multiple candidate dirs (directory + packages' statics/) tried in order; FileNotFoundError/NotADirectoryError continue the loop; nothing matched → `("", None)` → 404 upstream.
**Invariant:** BOTH sides are realpath'd before commonpath — comparing unresolved paths lets a symlink INSIDE the tree point anywhere. follow_symlink=True intentionally relaxes this (abspath, not realpath). Windows absolute-path form (`\`) covered.
**Probe:** `tests/test_staticfiles.py::test_staticfiles_prevents_breaking_out_of_directory` (:168).

## get_response — error-to-status mapping
**Path/Symbol:** `starlette/staticfiles.py:get_response` (:109-152).
**Data Shape:** method gate GET/HEAD only (405); PermissionError→401; ENAMETOOLONG→404 (name too long can't be a real file); ValueError (null bytes)→404; dir+html mode → index.html with slash-redirect; html mode miss → 404.html AS a 404-status FileResponse.
**Probe:** `::test_staticfiles_post` (:82), `::test_staticfiles_configured_with_missing_directory` (:131), `::test_staticfiles_with_directory_returns_404` (:96).

## is_not_modified + NotModifiedResponse
**Path/Symbol:** `starlette/staticfiles.py:is_not_modified` (:205-223), `NotModifiedResponse` (:22-36).
### Decisive source
```python
if if_none_match := request_headers.get("if-none-match"):
    etag = response_headers["etag"]
    return etag in [tag.strip().removeprefix("W/") for tag in if_none_match.split(",")]
# fall through to If-Modified-Since date comparison (>= means not modified)
```
**Flow:** ETag wins over date when present; weak-validator prefix W/ stripped from REQUEST tags (response etags are strong md5s here); 304 responses copy ONLY the RFC-listed headers (`cache-control, content-location, date, etag, expires, vary`) via NOT_MODIFIED_HEADERS filter.
**Invariant:** precedence order If-None-Match > If-Modified-Since is HTTP-mandated; porting the comparison before the etag check breaks conditional GET correctness.
**Probe:** `::test_staticfiles_304_with_etag_match` (:201); config-check-once flag pinned by `::test_staticfiles_config_check_occurs_only_once` (:154).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "lookup_path", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "is_not_modified", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "NotModifiedResponse", limit: 5 });
```

## Verdict
Adopt the double-realpath containment and the 304 header whitelist verbatim — both are security/correctness contracts, not style. Adapt the package-statics resolution to your asset pipeline. Omit html mode for pure-API services.
