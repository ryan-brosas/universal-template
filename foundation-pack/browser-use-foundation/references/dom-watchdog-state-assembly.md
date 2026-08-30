<!-- capsule-v2 -->
# DOM watchdog — parallel DOM+screenshot state assembly with budget-guarded recovery

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does a browser agent assemble the full per-step state (DOM + screenshot + page info + network) within a strict time budget without one slow subsystem starving the rest?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdogs/dom_watchdog.py` (877 lines): `DOMWatchdog` (:28) — `on_BrowserStateRequestEvent` (:244-547), `_build_dom_tree_without_highlights` (:551-688), `_capture_clean_screenshot` (:692-722), `_get_pending_network_requests` (:93-241), `_get_page_info` (:760-830), `_detect_pagination_buttons` (:724-758), `_get_recent_events_str` (:54-91).
**Signature:** `on_BrowserStateRequestEvent(event) -> BrowserStateSummary`; budget constant `_BROWSER_STATE_PARALLEL_TASK_BUDGET_SECONDS = 20.0`.

### Decisive source
```python
# Non-http(s) pages (about:blank etc.) take a fast path: minimal DOM, no screenshot
# DOM build + screenshot run as PARALLEL tasks (create_task_with_error_handling, suppress_exceptions)
# Screenshot gets a REMAINING-BUDGET timeout so a stalled capture can't consume the whole
#   BrowserStateRequestEvent 30s budget and block the DOM-only state from returning:
#   remaining = max(0.001, 20.0 - (monotonic() - started))
#   screenshot_b64 = await asyncio.wait_for(screenshot_task, timeout=remaining)
# Page info: single Page.getLayoutMetrics -> CSS-vs-device pixel ratio conversion for viewport/page/scroll
# Pending network: performance.getEntriesByType('resource') w/ responseEnd==0, filtered by ad/tracking
#   domains, data:/long URLs, >10s stuck, non-critical img/font>3s; capped at 20
# On any failure -> minimal recovery BrowserStateSummary (never raises to the agent loop)
```

**Flow:** check meaningful-website fast path → fetch pending requests (2s timeout) → brief stability wait → fetch tabs → start DOM + screenshot tasks in parallel → await DOM (fallback minimal on failure) → await screenshot with remaining-budget timeout → add browser-side highlights → page info (1s timeout) → pagination detection → cache summary + viewport size → return.
**Invariant:** the screenshot budget is derived from elapsed time so DOM-only state always returns within budget; failures degrade to a minimal recovery summary rather than raising; `_original_viewport_size` is cached for coordinate conversion; non-http pages skip DOM+screenshot entirely.
**Probe:** `tests/ci/browser/test_dom_serializer.py`, `tests/ci/test_dom_paint_order_serialization.py`, `tests/ci/browser/test_navigation.py`, `tests/ci/test_screenshot_exclusion.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "DOMWatchdog on_BrowserStateRequestEvent _capture_clean_screenshot _BROWSER_STATE_PARALLEL_TASK_BUDGET_SECONDS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the parallel DOM+screenshot assembly with the remaining-budget screenshot timeout (the key anti-starvation invariant), the meaningful-website fast path, and the minimal-recovery fallback. Adapt to host's state model.
