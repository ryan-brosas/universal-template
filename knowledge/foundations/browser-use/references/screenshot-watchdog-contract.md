<!-- capsule-v2 -->
# Screenshot watchdog target validation + cancellation-safe highlight removal — how do you capture a clean screenshot from any focused-target state?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** what must happen before Page.captureScreenshot so iframe focus states and stale highlights never corrupt the capture?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdogs/screenshot_watchdog.py` whole (88L) — `ScreenshotWatchdog.on_ScreenshotEvent` (:22).
**Signature:** `LISTENS_TO = [ScreenshotEvent]`; handler returns base64 PNG str.

### Decisive source
```python
# Validate focused target is a top-level page (not iframe/worker) —
# CDP Page.captureScreenshot only works on page/tab targets.
focused_target = self.browser_session.get_focused_target()
if focused_target and focused_target.target_type in ('page', 'tab'):
    target_id = focused_target.target_id
else:
    ...  # fall back to any page target; none -> raise BrowserError

# Remove highlights BEFORE taking the screenshot. Done here (NOT in finally)
# so CancelledError is NEVER swallowed — any await in a finally block can
# suppress external task cancellation.
try:
    await self.browser_session.remove_highlights()   # has internal asyncio.timeout(3.0)
except Exception:
    pass

params_dict = {'format': 'png', 'captureBeyondViewport': event.full_page}
if event.clip: params_dict['clip'] = {**event.clip, 'scale': 1}
```

**Flow:** validate/fallback target selection → focused CDP session → strip highlights (best-effort, bounded 3s internally) → captureScreenshot with full-page flag and optional clip → missing `data` key raises BrowserError rather than returning None.
**Invariant:** highlight removal must precede capture but live OUTSIDE any finally block (finally-await can swallow CancelledError and break task cancellation semantics); target-type gating prevents cryptic CDP failures when focus sits on an iframe/worker; clip dict always carries explicit scale=1.
**Probe:** `tests/ci/test_screenshot_exclusion.py` (highlight exclusion around capture); fallback path covered by deterministic source citation (no dedicated watchdog test — coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "ScreenshotWatchdog captureScreenshot remove_highlights get_focused_target target_type", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt target-type validation with page-list fallback + cancel-safe pre-capture cleanup ordering; adapt formats/clipping; omit the observe_debug tracing wrapper.
