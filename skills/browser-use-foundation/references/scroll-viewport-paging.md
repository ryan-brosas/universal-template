<!-- capsule-v2 -->
# Scroll viewport measurement + multi-page sequencing — how do you scroll N pages reliably when each scroll is async?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does the scroll action convert "pages" into pixels and guarantee each page-scroll completes before the next?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/service.py` — `scroll` action (:1416-1553): viewport probe (:1436-1447), full-page loop (:1450-1495), fractional handling (:1496-1516).
**Signature:** `async def scroll(params: ScrollAction, browser_session)` with `pages: float = 1.0`, `down: bool = True`, optional `index`.

### Decisive source
```python
# Viewport height via CDP layout metrics, prioritizing cssVisualViewport:
metrics = await cdp_session.cdp_client.send.Page.getLayoutMetrics(session_id=...)
css_viewport = metrics.get('cssVisualViewport', {})
css_layout_viewport = metrics.get('cssLayoutViewport', {})
viewport_height = int(css_viewport.get('clientHeight') or css_layout_viewport.get('clientHeight', 1000))
except Exception: viewport_height = 1000     # fallback, never raise on metrics failure

if params.pages >= 1.0:
    for i in range(num_full_pages):          # ONE event per page, awaited serially
        dispatch ScrollEvent(direction, abs(pixels), node)
        await event.event_result(raise_if_any=True, ...)
        await asyncio.sleep(0.15)            # ensure scroll completes before next
        # per-page failures logged and SKIPPED - remaining scrolls still attempted
    if remaining_fraction > 0: single fractional event
```

**Flow:** index≠0 resolves target element (index==0 means whole page) → measure viewport (cssVisualViewport preferred, fallback chain to layout viewport to 1000px) → ≥1 page loops one awaited ScrollEvent per page with 150ms inter-event gaps → fractional remainder issues a scaled single event → memory reports either px (single page) or completed-pages count.
**Invariant:** each page-scroll must be individually awaited with a settle gap or momentum/timing races drop intermediate positions; metric failures degrade to the 1000px default rather than failing the action; direction sign flips pixels once at dispatch.
**Probe:** `tests/ci/test_actor_mouse_scroll_anchor.py` (actor-side scroll anchor semantics); service-level loop pinned by deterministic citation :1436-:1516 (coverage caveat: no dedicated scroll-loop test).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "scroll getLayoutMetrics cssVisualViewport ScrollEvent num_full_pages", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt measured-viewport paging with serial awaited events + settle gaps + graceful metric degradation; adapt the 0.15s gap to your renderer; omit index-targeting if you have no element-scoped scrolling.
