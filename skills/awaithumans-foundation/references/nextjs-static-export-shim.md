<!-- capsule-v2 -->
# Next.js Static-Export URL Shim — clean URLs against a flat .html export

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-agents-awaithumans`. **Question:** Why does stock StaticFiles 404 on `/setup` when `setup.html` exists, and what is the minimal override?

## Try `<path>.html` FIRST for extensionless paths, then fall through to stock
**Path/Symbol:** `packages/python/awaithumans/server/core/dashboard_static.py` — failure-mode docstring (:1-23), `DashboardStaticFiles.lookup_path` (:41-56).
**Signature:** `lookup_path(self, path: str) -> tuple[str, os.stat_result | None]` — SYNCHRONOUS override (Starlette calls it via anyio.to_thread; making it async breaks the super call chain).
**Data Shape:** Next `output: "export"` WITHOUT trailingSlash emits sibling layout: `setup.html` (real page) + `setup/` (metadata dir with NO index.html).

### Decisive source
```python
last = path.rsplit("/", 1)[-1] if path else ""
if path and last and "." not in last:                 # extensionless CLEAN url only
    html_full, html_stat = super().lookup_path(f"{path}.html")
    if html_stat is not None and stat_module.S_ISREG(html_stat.st_mode):
        return html_full, html_stat                    # must be a REGULAR FILE
return super().lookup_path(path)                       # assets + real dirs unchanged
```

**Flow:** GET /task → extensionless → try task.html → regular-file stat ⇒ serve. GET /favicon.ico → last segment contains a dot → straight to stock. Directory-with-index.html cases still resolve via stock html-mode behavior.
**Invariant:** the `.html` candidate must pass an S_ISREG check — without it a directory named `x.html` or weird layouts get served as files; covering `/setup /settings /login /task /audit /analytics` requires NO change to Next's build config (which would break dev hot reload).
**Probe:** `packages/python/tests/dashboard/test_dashboard_static.py` (`test_clean_url_falls_back_to_html_file`:85, `test_every_dashboard_route_resolves`:93, `test_exact_html_path_still_works`:114, `test_asset_404_stays_404`:121) — suite green at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-awaithumans", query: "DashboardStaticFiles lookup_path html", limit: 4 });
```
Live rank-1 line-exact (:41-56).

## Verdict
Adopt the 12-line override shape verbatim if you serve a Next static export from FastAPI/Starlette; adapt route sets freely; omit nothing — the S_ISREG guard and sync signature are both load-bearing.
