<!-- capsule-v2 -->
# mouse-position-quads — from content quads to clicks, drags, and element screenshots

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How are screen coordinates derived and used for input dispatch, and what does "abs" mean?

## Position unwraps the first quad; center drives everything
**Path/Symbol:** `zendriver/core/element.py:Element.get_position` (:502-527), `Position` (:1220-1251), `mouse_click` (:529-581), `mouse_drag` (:602-687), `Tab.mouse_move`/`flash_point` (`tab.py:1534-1651`).
**Signature:** `async def get_position(self, abs: bool = False) -> Position | None`; `Position(points: list[float])` where points is the 8-float quad `[x1,y1,x2,y2,x3,y3,x4,y4]`.
**Data Shape:** `quads[0]` unpacked as left,top,right,top,right,bottom,left,bottom; `center = (left + width/2, top + height/2)`.

### Decisive source
```python
quads = await self.tab.send(cdp.dom.get_content_quads(object_id=self._remote_object.object_id))
if not quads:
    raise Exception("could not find position for %s " % self)
pos = Position(quads[0])
if abs:
    scroll_y = (await self.tab.evaluate("window.scrollY")).value
    scroll_x = (await self.tab.evaluate("window.scrollX")).value
    abs_x = pos.left + scroll_x + (pos.width / 2)
    abs_y = pos.top + scroll_y + (pos.height / 2)
```
and the drag stepper (:661-678) interpolating `steps+1` points with `await asyncio.sleep(0)` between dispatches, then a single `mouseReleased` at the end point. `IndexError` (empty quads) → `None`, logged as *"mostly caused by element which is not 'in plain sight'"*.
**Flow:** resolve node → remote object → `dom.get_content_quads(object_id)` → first quad → viewport coords. `Element.screenshot_b64` converts the same Position into `cdp.page.Viewport(x, y, w, h, scale)` with `capture_beyond_viewport=True` (:906-918). `flash_point` injects a keyframed red dot div for debugging clicks.
**Invariant:** dispatched coordinates are **viewport-relative** unless `abs=True` adds scroll offsets — mixing these up clicks the wrong element on scrolled pages. `mouse_click` fires pressed+released as one `asyncio.gather` pair at `position.center`; hidden elements yield `None` and the click is skipped with a warning, never an exception.
**Probe:** static anchors at pin: `grep -n 'abs(len(text)' zendriver/core/tab.py` unrelated; element-side: `grep -c 'HTMLInputElement.prototype' zendriver/core/element.py` sanity; position sites: `get_content_quads` at :508; direct tests exercise clicking via `tests/docs/tutorials/test_account_creation_tutorial.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "mouse_drag steps dispatch", limit: 5 });
```

## Verdict
Adopt quad-unwrapping and the gather-pair click; adapt step interpolation to humanization needs; keep the None-on-hidden contract so callers can branch.
