<!-- capsule-v2 -->
# Element actor — quad-based geometry fallback chain and real-mouse clicks

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how do you click/type into an element reliably when CDP geometry APIs each fail differently (inline elements, transformed layouts, detached nodes)?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/actor/element.py` (1,182 lines): `Element` (:62) — `click` (:93-380+), `_get_node_id` (:76), `_get_remote_object_id` (:82), geometry resolution (:107-249), viewport-intersection scoring (:215-257), modifier bitmask (:268-273), `Input.dispatchMouseEvent` sequence (:276+); siblings `actor/mouse.py`, `actor/page.py`.
**Signature:** geometry fallback chain: `DOM.getContentQuads` → `DOM.getBoxModel` → JS `getBoundingClientRect` → last resort JS `this.click()`; then pick the quad with the LARGEST VISIBLE area inside the viewport.
**Data Shape:** quads = flat `[x1,y1, x2,y2, x3,y3, x4,y4]` arrays; click point = clamped centroid of the best quad.

### Decisive source
```ts
# 3-way geometry resolution, each swallowing its own failure:
try: quads = DOM.getContentQuads({backendNodeId})            # inline/complex layouts
except: pass
if not quads: try: quads = [boxModel.model.content]           # simple boxes
if not quads: try: rect = Runtime.callFunctionOn(getBoundingClientRect)
if not quads: Runtime.callFunctionOn('function(){ this.click() }'); return  # last resort
# pick the most-visible quad, not the first:
for quad in quads:
    visible_area = intersection(quad_bounds, viewport).area
    if visible_area > best_area: best_quad = quad
center_x = clamp(sum(x_i)/4, 0, viewport_width - 1)
# REAL mouse event sequence (not JS click):
scrollIntoViewIfNeeded → Input.dispatchMouseEvent(mouseMoved)   # hover state!
                       → mousePressed(button, clickCount, modifiers bitmask Alt=1 Ctrl=2 Meta=4 Shift=8)
                       → mouseReleased
```

**Flow:** resolve geometry through the degradation ladder → score quads by visible-in-viewport area (multi-column inline elements produce several quads; a partially-scrolled-off button still yields its visible half) → scrollIntoViewIfNeeded → dispatch a genuine mouseMoved (triggering CSS :hover, dropdowns on hover) before press/release with the modifier bitmask. Every step has small sleeps letting the renderer settle.
**Invariant:** never trust one geometry API (each fails on different DOM shapes); click the most-visible fragment of multi-quad elements; use real input events so hover-dependent UI works; JS `element.click()` is the escape hatch only when no geometry exists at all.
**Probe:** `tests/actor/` tests (quad fallback ordering; offscreen element scrolled before click; hover events fired).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "Element click getContentQuads getBoxModel dispatchMouseEvent modifiers scrollIntoViewIfNeeded", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the geometry degradation ladder + largest-visible-quad selection + genuine mouse-event sequences for browser automation. Adapt to host's driver protocol.
