<!-- capsule-v2 -->
# Steel-CDP fallback launch — how does a persistent-context browser manager survive cloud-browser outages and crashed profile dirs?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How do you structure browser bring-up so that remote CDP failure and corrupt user-data dirs degrade to local automation instead of dying?

## CDP-first, local persistent fallback, temp-dir recovery, closed-page resurrection
**Path/Symbol:** `core/browser_manager.py`:`PlaywrightManager.create_browser_context` (`:181-261`), `get_current_page` (`:286-309`), `stop_playwright` (`:148-165`), class attrs (`:37-46`), `__init__` (`:53-86`).
**Signature:** `async def create_browser_context(self)`; `async def get_current_page(self) -> Page`.
**Data Shape:** Class-level singletons `_playwright/_browser_context/_browser` (idempotent via `__async_initialize_done`). Launch flags: `bypass_csp=True`, `channel="chromium"`, `--disable-blink-features=AutomationControlled --disable-session-crashed-bubble --disable-infobars`, `no_viewport=True`, optional video recording into `videos/`. Env knobs: `STEEL_DEV_API_KEY` (remote CDP via `wss://connect.steel.dev`), `BROWSER_STORAGE_DIR` (persistent profile).

### Decisive source
```python
if steel_api_key:
    try:
        PlaywrightManager._browser = await ...connect_over_cdp(f'wss://connect.steel.dev?apiKey={steel_api_key}')
        PlaywrightManager._browser_context = PlaywrightManager._browser.contexts[0]   # FIRST context, never new_page()
        return
    except Exception as cdp_error:
        logger.warning(f"CDP connection failed, falling back to local browser: {cdp_error}")
PlaywrightManager._browser_context = await ...launch_persistent_context(user_dir, ...)
...
except Exception as e:
    if "Target page, context or browser has been closed" in str(e):
        new_user_dir = tempfile.mkdtemp()      # crashed/corrupt profile dir -> throwaway dir
```
And the resurrection path in `get_current_page`: filter to non-closed pages, take the LAST one, else `new_page()`; if the CONTEXT itself was closed, null the class singleton and recurse through `ensure_browser_context`.
**Flow:** async_initialize (start_playwright → ensure_browser_context → setup_handlers → homepage) → CDP attempt when key present → fallback persistent launch → on "has been closed": mkdtemp + one CDP retry → local relaunch; chromium-missing becomes a loud install hint.
**Invariant:** Remote contexts are ADOPTED (`contexts[0]`), never created fresh — your cookies/login live in the cloud browser's existing session. Video flush depends on closing pages BEFORE context close in stop_playwright (page.close triggers save). `os.environ["PW_TEST_SCREENSHOT_NO_FONTS_READY"] = "1"` is set at import time to stop screenshots waiting on font loads (upstream playwright#28995). GUI/API mode fork lives in the orchestrator's factory call (headless only for API).
**Probe:** No tests (coverage caveat). Graph pins: semantic search "mmid attribute injection accessibility tree" ranks five PlaywrightManager lifecycle methods top-8, confirming the seam's centrality; `trace_path Orchestrator.run` shows exactly two PlaywrightManager constructor references plus `async_initialize/get_current_page/stop_playwright/notify_user/take_screenshots` calls.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "connect_over_cdp launch_persistent_context fallback", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the CDP→local→temp-dir degradation ladder and last-non-closed-page selection. Adapt the provider URL/flags; keep the adopt-don't-create rule for remote contexts. Omit video recording if you don't replay runs — but then also drop the page-close-before-context-close coupling.
