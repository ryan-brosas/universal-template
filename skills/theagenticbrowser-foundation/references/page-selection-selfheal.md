<!-- capsule-v2 -->
# Page-selection self-heal — which tab does the agent act on after a crash, and how does a dead context come back?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** After a browser crash or tab closure, how do you pick the page to act on and recover the context without leaking stale handles?

## Filtered-last-page selection with recursive context re-creation
**Path/Symbol:** `core/browser_manager.py`:`PlaywrightManager.get_current_page` (`:286-309`), `create_browser_context` (`:181-261`, recovery branch `:228-259`), class-level singleton state (`:38-46`).
**Signature:** `async def get_current_page(self) -> Page`.
**Data Shape:** Playwright/context live in CLASS attributes (`PlaywrightManager._playwright`, `_browser_context`) shared across instances; `__async_initialize_done` gates double init. Selection input is `browser.pages` filtered by `page.is_closed()`.

### Decisive source
```python
# :293-309 — selection ladder + self-heal
try:
    browser: BrowserContext = await self.get_browser_context()
    pages: list[Page] = [page for page in browser.pages if not page.is_closed()]
    page: Page | None = pages[-1] if pages else None      # LAST open tab wins
    if page is not None:
        return page
    else:
        page:Page = await browser.new_page()              # zero pages → create one
        return page
except Exception:
        logger.warn("Browser context was closed. Creating a new one.")
        PlaywrightManager._browser_context = None          # drop ONLY the handle
        _browser:BrowserContext = await self.get_browser_context()  # recreate
        page: Page | None = await self.get_current_page()           # RECURSE once
        return page
```
**Flow:** every skill/tool starts with `PlaywrightManager()` + `get_current_page()` — the singleton returns the same underlying context, so "current page" = last tab in creation order among non-closed pages. If the context died, the except branch nulls `_browser_context` and lets `ensure_browser_context` rebuild it (`launch_persistent_context` on the same user dir), then recurses into selection. `create_browser_context`'s own recovery ladder handles launch-time death: `"Target page, context or browser has been closed"` → retry CDP (if Steel key) or relaunch into a fresh `tempfile.mkdtemp()` profile (:229-255); `"Chromium distribution 'chromium' is not found"` → actionable ValueError (:256-257).
**Invariant:** Never return a closed page — filter BEFORE indexing, and index from the END (`pages[-1]`). Recovery resets the handle, never the whole manager; the persistent user dir survives so cookies/session outlive crashes. The recursion depth is bounded by construction: after `_browser_context = None` the next `get_browser_context()` synchronously creates a real context.
**Probe:** `grep -n "Browser context was closed" core/browser_manager.py` → `305`; `grep -c "pages\[-1\]" core/browser_manager.py` → `1`; `grep -c "new_page()" core/browser_manager.py` → `1`; `grep -c "Target page, context or browser has been closed" core/browser_manager.py` → `1`; `grep -n bypass_csp core/browser_manager.py` → `219` (first-launch only — the temp-dir relaunch at :246 OMITS `bypass_csp`, so overlay injection can fail there). Coverage caveat: no upstream tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "get_current_page browser context closed new_page", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt: closed-filtered last-tab selection, null-handle-and-recreate recovery, and the two-branch launch-failure ladder. Adapt: Steel CDP endpoint and profile-dir env. Watch: the missing `bypass_csp=True` on the temp-profile relaunch is a real upstream asymmetry — add it when porting. Omit: video recording options. Coverage caveat: no upstream tests; probes line-pinned at pin `71daa28`.
