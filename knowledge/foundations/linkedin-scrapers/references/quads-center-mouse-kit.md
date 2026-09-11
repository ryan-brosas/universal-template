<!-- capsule-v2 -->
# Element geometry + native-mouse action kit — how do you click/drag/hover a CDP element by REAL coordinates instead of `el.click()`?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do you get an element's viewport box and fire trusted mouse events at it — including drags with human-like stepped paths and absolute-page coordinates — when synthetic DOM clicks don't trigger site handlers?

## content-quads → center/abs math → dispatch ladder
**Path/Symbol:** `zendriver/core/element.py:Position` (:1220-1251), `Element.get_position` (:502-527), `mouse_click` (:529-581), `mouse_move` (:583-600), `mouse_drag` (:602-687), `scroll_into_view` (:689-697), `click` (:401-425); tab-level twins `Tab.mouse_click` (:1561-1606)/`Tab.mouse_move` (:1534-1559).
**Signature:** `get_position(abs=False) -> Position | None`; `Position.center`, `.left/.top/.width/.height`, `.to_viewport(scale) -> cdp.page.Viewport`; `mouse_drag(destination, relative=False, steps=1)`; both `Tab.mouse_click` and the CF solver take `_until_event` (reserved hook, currently unused).
**Data Shape:** `cdp.dom.get_content_quads(object_id=...)` returns quads; `[0]` unpacked as corner list `(left,top,right,top,right,bottom,left,bottom)`; center = `(left+w/2, top+h/2)`; abs = `pos.left+scrollX+w/2` / `pos.top+scrollY+h/2`.

### Decisive source
```python
quads = await self.tab.send(cdp.dom.get_content_quads(object_id=self._remote_object.object_id))
if not quads:
    raise Exception("could not find position for %s " % self)
pos = Position(quads[0])
if abs:
    scroll_x = (await self.tab.evaluate("window.scrollX")).value   # quads are VIEWPORT coords
    pos.abs_x = pos.left + scroll_x + (pos.width / 2)              # page coords need + scroll offset

# element.mouse_click: press+release as ONE gather — near-simultaneous pair
await asyncio.gather(
    self._tab.send(cdp.input_.dispatch_mouse_event("mousePressed", x=center[0], y=center[1],
                     modifiers=modifiers, button=..., buttons=buttons, click_count=1)),
    self._tab.send(cdp.input_.dispatch_mouse_event("mouseReleased", x=center[0], y=center[1], ...)),
)

# mouse_drag: linear interpolation pathway, yield between steps
step_size_x = (end_point[0] - start_point[0]) / steps
pathway = [(start_point[0] + step_size_x * i, start_point[1] + step_size_y * i)
           for i in range(steps + 1)]
for point in pathway:
    await self._tab.send(cdp.input_.dispatch_mouse_event("mouseMoved", x=point[0], y=point[1]))
    await asyncio.sleep(0)          # cooperative yield between micro-moves
```

**Flow:** everything keys off `resolve_node(backend_node_id)` → `object_id` → `get_content_quads`; empty quads mean the element is not rendered/in plain sight → return None (callers log-and-skip rather than raise). The `Position` subclass of `Quad` derives center/width/height once. Two click flavors exist BY DESIGN: `Element.click()` runs `(el)=>el.click()` via `call_function_on` (a DOM-synthetic click that works headless but some frameworks ignore), while `Element.mouse_click`/`Tab.mouse_click` dispatch real `input.dispatchMouseEvent` press+release at coordinates (trusted event stream). Note the two flavors even differ in ordering: element-level sends press/release as one gathered pair; Tab-level sends them sequentially. `mouse_drag` presses at start, interpolates `steps` linear waypoints toward the destination (relative mode adds offsets to the START point), yields cooperatively (`asyncio.sleep(0)`) between moves so the browser can process each, then releases at the end point. `scroll_into_view` uses the CDP-native `DOM.scrollIntoViewIfNeeded` in a swallow-all wrapper. Missing-position failures degrade: every consumer checks `if not position: log warning; return` — geometry absence is a skip condition, never an exception path (the CF solver's "could not find position after click ⇒ success" rule is the deliberate exception).
**Invariant:** (1) content quads are VIEWPORT-relative — any page-absolute use MUST add window.scrollX/Y (the `abs=True` branch is the only correct recipe; forgetting this makes off-screen clicks land wrong); (2) keep `click_count=1` on BOTH press and release or the browser sees a double-click; (3) drag pathways must yield between waypoints (`sleep(0)`) or the whole gesture coalesces into a jump; (4) unrendered elements produce EMPTY quads (not errors) — treat None position as skip-not-crash.
**Probe:** no upstream unit test drives real mouse events for these methods (coverage caveat; upstream itself notes "this likely does not work atm" on element.mouse_click's docstring — prefer Tab.mouse_click). Deterministic pins (anchored at the `zendriver/` package dir): `grep -n 'get_content_quads' core/element.py` → :509; `grep -n 'window.scrollY' core/element.py` → :515; `grep -n 'asyncio.sleep(0)' core/element.py` → :678; graph probes resolve `mouse_drag Method 602-687`, `to_viewport Method 1245-1248`, `get_content_quads Function 976-1004` (cdp.dom).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "get_content_quads dispatch_mouse_event mouse_drag Position to_viewport", limit: 5 });
```

## Verdict
Adopt: quads→center→dispatch pipeline, viewport-vs-page coordinate correction (+scroll), press/release `click_count=1` pairing, stepped drag interpolation with cooperative yields, and skip-don't-crash missing-geometry semantics. Prefer the DOM-click flavor (`Element.click`) where handlers accept synthetic clicks; reserve native-mouse for anti-bot surfaces that require trusted events (pairs with ghost-cursor-click-ladder from linvo). Coverage: source-pinned only (no live-mouse runner upstream).
