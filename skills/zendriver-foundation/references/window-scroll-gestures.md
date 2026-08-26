<!-- capsule-v2 -->
# window-scroll-gestures — state machine of set_window_state and the synthesized scroll contract

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How are window states applied, and why does scrolling sleep after dispatch?

## Fuzzy state names; scroll = gesture + proportional sleep
**Path/Symbol:** `zendriver/core/tab.py:Tab.set_window_state` (:1047-1097), `scroll_down` (:1099-1125) / `scroll_up` (:1127-1152).
**Signature:** `async def set_window_state(self, left=0, top=0, width=1280, height=720, state="normal")`; `async def scroll_down(self, amount: int = 25, speed: int = 800)`.
**Data Shape:** `available_states = ["minimized", "maximized", "fullscreen", "normal"]`; `amount` is a **percentage** of viewport height; `speed` in px/s.

### Decisive source
```python
for state_name in available_states:
    if all(x in state_name for x in state.lower()):
        break
else:
    raise NameError("could not determine any of %s from input '%s'" % (...))
...
if window_state == cdp.browser.WindowState.NORMAL:
    bounds = cdp.browser.Bounds(left, top, width, height, window_state)
else:
    # min, max, full can only be used when current state == NORMAL
    # therefore we first switch to NORMAL
    await self.set_window_state(state="normal")
    bounds = cdp.browser.Bounds(window_state=window_state)
```
and the scroll tail:
```python
await self.send(cdp.input_.synthesize_scroll_gesture(
    x=0, y=0, y_distance=-(height * (amount / 100)), ..., speed=speed))
await asyncio.sleep(height * (amount / 100) / speed)
```

**Flow:** fuzzy-match user state strings ("min", "maxi", "fu" all work — substring containment both ways); NORMAL sets geometry directly; every other state first recurses to normal because Chromium rejects transitions between non-normal states. Scrolling sends a *synthesized touch-like gesture* (not JS `scrollBy`) so sites see realistic scroll events, then sleeps exactly `distance/speed` seconds so callers can assume completion on return.
**Invariant:** the post-dispatch sleep is the completion guarantee — removing it makes subsequent DOM assertions race the compositor. And state recursion is depth-1 by construction.
**Probe:** static anchors at pin: `grep -n 'await asyncio.sleep(height' zendriver/core/tab.py` → :1125,:1152 (both directions); direct test: `tests/core/test_tab.py::test_wait_for_ready_state` covers the adjacent wait family; window tests run in `tests/core/test_tab.py` maximize/medimize paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "set_window_state normal maximize", limit: 5 });
```

## Verdict
Adopt the normalize-then-apply ordering and gesture+sleep pairing; adapt default speed/amount to app UX; keep substring matching only with the documented vocabulary.
