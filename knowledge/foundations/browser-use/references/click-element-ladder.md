<!-- capsule-v2 -->
# Click-element ladder — geometry, occlusion, CDP mouse seq, checkbox verify, JS fallback

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does a robust CDP click reliably hit an element across scroll, occlusion, dialogs, and framework-reverted toggles?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdogs/default_action_watchdog.py`: `DefaultActionWatchdog._click_element_node_impl` (:702-1062), `_check_element_occlusion` (:573-700), `_click_on_coordinate` (:1064-1142).
**Signature:** `async _click_element_node_impl(element_node) -> dict | None` returning `{'click_x','click_y'}` (+ `checked` for toggles).
**Data Shape:** guard rails reject `<select>` and `<input type=file>` with `validation_error` dicts (never raise); checkbox/radio capture pre-click `checked` state via `Runtime.callFunctionOn` to verify the toggle actually flipped.

### Decisive source
```python
# 1. scrollIntoViewIfNeeded FIRST, then get_element_coordinates (unified DOMRect)
# 2. if no quads -> JS this.click() fallback (assert objectId, 'No node with given id' -> raise)
# 3. pick largest visible quad intersecting viewport; clamp center to viewport-1
# 4. occlusion check: elementFromPoint containment + label<->input association cases
#   -> if occluded: JS this.click() fallback
# 5. CDP mouse seq: mouseMoved -> mousePressed(clickCount=1) -> mouseReleased
#   each with asyncio.wait_for(3.0/5.0) so a dialog doesn't hang the click
# 6. checkbox/radio: re-read checked; if unchanged -> JS this.click() fallback, re-verify
# 7. finally: re-focus top-level session (runIfWaitingForDebugger) in case click opened a tab/dialog
```

**Flow:** guard rails → scroll into view → get geometry → pick largest visible quad → occlusion check (asymmetric: resolve failure ⇒ occluded; JS check failure ⇒ not occluded) → CDP mouse sequence with per-step timeouts → checkbox toggle verification (JS fallback if unchanged) → re-focus in `finally`.
**Invariant:** a dialog or slow page never hangs the click (per-event `asyncio.wait_for`); occlusion fails toward JS-click (not toward a silent miss); after any click the session is re-focused back to the top-level page; stale-index errors get a helpful `long_term_memory` hint.
**Probe:** `tests/ci/test_element_click_error.py`, `tests/ci/test_coordinate_clicking.py`, `tests/ci/browser/test_true_cross_origin_click.py`, `tests/ci/test_action_loop_detection.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_click_element_node_impl _check_element_occlusion scrollIntoViewIfNeeded mousePressed checkbox", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the scroll-then-geometry-then-largest-visible-quad ladder, the asymmetric occlusion policy, per-step timeouts, checkbox verify-and-fallback, and re-focus in `finally`. Adapt CDP client API to host.
