<!-- capsule-v2 -->
# Fire-and-forget highlight tasks — how do you decorate the page for screenshots without ever blocking or leaking exceptions?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does browser-use draw element/coordinate highlights without adding latency or unretrieved-task noise to actions?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/service.py` call sites (:798, :806, :869) via `create_task_with_error_handling`; implementation `browser_use/utils.py` :800; pixel renderer `browser_use/browser/python_highlights.py` whole (font cache :24, `_FONT_PATHS`, `get_cross_platform_font` :36, ELEMENT_COLORS, `create_highlighted_screenshot` :407, `get_viewport_info_from_cdp` :468).
**Signature:** `create_task_with_error_handling(coro: Coroutine[Any, Any, T], *, name=None, logger_instance=None, suppress_exceptions=False) -> asyncio.Task[T]`.

### Decisive source
```python
task = asyncio.create_task(coro, name=name)
def _handle_task_exception(t: asyncio.Task[T]) -> None:
    try:
        exc = t.exception()   # retrieved so fire-and-forget tasks do NOT emit
                              # "Task exception was never retrieved" warnings
        if exc is not None:
            if suppress_exceptions: log.error(...)
            else:                   log.warning(...)
    except asyncio.CancelledError:
        pass                        # cancellation is normal, not an error
task.add_done_callback(_handle_task_exception)
return task

# Every highlight call site uses the SAME shape:
create_task_with_error_handling(
    browser_session.highlight_interaction_element(node),
    name='highlight_click_element',
    suppress_exceptions=True,     # decoration must NEVER break the action
)
```
```python
# python_highlights.py invariants:
_FONT_CACHE[cache_key] = font          # cache EVEN None results — no re-scan per frame
# PIL ImageDraw is NOT thread-safe -> elements processed sequentially in one loop
except Exception as e:
    ...
    return screenshot_b64              # on ANY failure return the ORIGINAL unhighlighted shot
```

**Flow:** action dispatches highlight coroutine as a named background task with done-callback exception retrieval → action proceeds immediately (zero added latency) → renderer decodes base64 PNG, draws dashed boxes + index labels per tag color using cached cross-platform font, re-encodes → viewport scaling comes from CDP `Page.getLayoutMetrics` (devicePixelRatio = visual/css width ratio).
**Invariant:** decoration failures must be logged-and-dropped, never propagated into the action result; the font cache must store negative results too or every frame rescans filesystem fonts; image cleanup (`image.close()`) happens in finally/error paths to avoid long-session memory leaks.

### Renderer geometry (whole-file re-read at pin 85ddbfe, python_highlights.py 546L)
```python
# process_element_highlight :357-372 — CSS→device pixel scaling, then clamp, then skip
x1 = int(bounds.x * device_pixel_ratio); y1 = int(bounds.y * device_pixel_ratio)
x2 = int((bounds.x + bounds.width) * device_pixel_ratio)
y2 = int((bounds.y + bounds.height) * device_pixel_ratio)
...clamp to image bounds...
if x2 - x1 < 2 or y2 - y1 < 2: return          # min-2px bounding-box skip

# filter_highlight_ids :386-394 — index couples to what the LLM can see
if filter_highlight_ids:
	meaningful_text = element.get_meaningful_text_for_llm()
	if len(meaningful_text) < 3:               # code says 3; adjacent comment says '5' — TRUST THE CODE
		index_text = str(element_id)

# get_viewport_info_from_cdp :468-496 — DPR ladder with degrade
css_width = css_visual_viewport.get('clientWidth', css_layout_viewport.get('clientWidth', 1280.0))
device_width = visual_viewport.get('clientWidth', css_width)
device_pixel_ratio = device_width / css_width if css_width > 0 else 1.0
except Exception: return 1.0, 0, 0            # CDP failure degrades to identity transform

# enhanced label :150-191 — viewport-relative font, small-element label goes ABOVE
css_width = img_width   # NOTE: the '/ device_pixel_ratio' is COMMENTED OUT at :153
base_font_size = max(10, min(20, int(css_width * 0.01)))
padding = max(4, min(10, int(css_width * 0.005)))
if element_width < 60 or element_height < 30:
	bg_y1 = max(0, y1 - container_height - 5)  # small element: place label ABOVE the box
else:
	bg_y1 = y1 + 2                             # regular: inside top-center

# plain variant :294-318 — area-ratio anti-occlusion ladder (white bg + black border label)
size_ratio = element_area / max(index_box_area, 1)
if size_ratio < 4:    text_x, text_y = x2 + padding, y2 - text_height   # OUTSIDE bottom-right
elif size_ratio < 16: text_x, text_y = x2 - text_width - padding, y2 - text_height - padding  # inside corner
else:                 centered within the element
```
Geometry invariants: CSS-pixel coordinates are multiplied by DPR because screenshots are captured at device resolution; labels are clamped back inside image bounds after placement; `create_highlighted_screenshot_async` (:499-542) degrades to `(DPR=1.0, scroll 0,0)` on any CDP failure before drawing, and dumps the result via `asyncio.to_thread` only when `BROWSER_USE_SCREENSHOT_FILE` is set.
**Probe (executed live, PIL pixel assertions):** tiny element (20×10) → label drawn strictly outside bottom-right with box interior clean; large element (340×240) → centered white/black label present; enhanced variant small element (40×15) → colored label ABOVE the box top edge; element without `absolute_position` skipped silently.
**Probe:** deterministic — no dedicated test file for highlights (coverage caveat); pinned by usage at tools/service.py:798/:806/:869 and by `tests/ci/test_screenshot_exclusion.py` (highlights removed BEFORE capture).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "create_task_with_error_handling create_highlighted_screenshot get_cross_platform_font highlight_interaction_element", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the done-callback task wrapper as the universal fire-and-forget primitive and the fail-open highlight pipeline; adapt font paths/colors; omit BROWSER_USE_SCREENSHOT_FILE debug dumping.
