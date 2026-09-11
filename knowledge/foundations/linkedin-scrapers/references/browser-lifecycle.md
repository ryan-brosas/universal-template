<!-- capsule-v2 -->
# Browser lifecycle & session state — how do I own a Playwright browser as a context manager and carry sessions across runs?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb` (`core/browser.py` whole, 244L); cross-referenced with linvo MIT login service (token return) and hassan NO-LICENSE CDP attach. Codebase Memory `joeyism-linkedin-scraper`. **Question:** what launch/close ordering, session save/load contract, and guard rails make a reusable browser manager safe under partial failure?

## BrowserManager
**Path/Symbol:** `linkedin_scraper/core/browser.py:BrowserManager` (:15–244) — `__aenter__/__aexit__` (:48–55), `start` (:57–88), `close` (:90–112), `save_session` (:163–181), `load_session` (:183–213), `set_cookie` (:215–234).
**Signature:** `BrowserManager(headless=True, slow_mo=0, viewport=None, user_agent=None, **launch_options)`; async context manager exposing `.page`, `.context`, `.browser`; `save_session(filepath)` / `load_session(filepath)` via Playwright storage_state.
**Data Shape:** session file = Playwright `storage_state()` JSON (cookies + origins) written indent=2 after mkdir-parents; load swaps the CONTEXT (new_context(storage_state=…)), not the browser.

### Decisive source
```python
async def start(self):
    try:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless, slow_mo=self.slow_mo, **self.launch_options)
        self._context = await self._browser.new_context(viewport=self.viewport, user_agent=...)
        self._page = await self._context.new_page()
    except Exception as e:
        await self.close()                       # NEVER leak a half-started stack
        raise NetworkError(f"Failed to start browser: {e}")

async def close(self):                             # page → context → browser → playwright, in order
    ...each step guarded, nulled after close...
```

**Flow:** enter → start() launches the full stack or tears down and re-raises as NetworkError → scrape → optional save_session → exit → close() walks page/context/browser/playwright in strict order, each guarded so a failure mid-teardown still frees the rest. `load_session` closes only the context, rebuilds it with stored state, re-creates the page, and flags `_is_authenticated = True`.
**Invariant:** teardown order is leaf-to-root with null-after-free guards; every property accessor raises RuntimeError with an actionable message when used pre-start ("Use async context manager or call start()") — no silent None propagation; session identity lives at the context level so cookies+localStorage travel together.
**Probe:** `tests/test_browser.py::test_browser_manager_context`, `::test_browser_manager_navigation`, `::test_browser_manager_session_save_load(tmp_path)` (asserts round-trip file exists then loads into a second manager), `::test_browser_manager_headless_mode`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "BrowserManager", limit: 5 });
// direct test nodes: test_browser_manager_* resolve in graph
```

## Verdict
Adopt ordered-guarded teardown, half-start rollback, context-level session persistence, and loud accessors; adapt viewport/UA defaults and add proxy plumbing if needed; omit the boolean-only is_authenticated flag (derive from cookie presence instead). Probe caveat: tests cover lifecycle/round-trip, not LinkedIn-specific behavior.
