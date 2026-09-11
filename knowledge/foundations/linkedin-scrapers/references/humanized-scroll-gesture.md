<!-- capsule-v2 -->
# Humanized scroll gesture — how do you scroll a page in a way that looks like a person, not a script?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do you scroll with a natural gesture (speed + prevent-fling) instead of a jarring instant jump, and how do you pace it to the actual scroll duration?

## Synthesized scroll gesture with prevent-fling + self-paced sleep
**Path/Symbol:** `zendriver/core/tab.py:scroll_down` (:1099-1125), `scroll_up` (:1127-1152).
**Signature:** `Tab.scroll_down(amount=25, speed=800)`; `scroll_up(amount=25, speed=800)`.
**Data Shape:** `amount` = percentage of the current window HEIGHT (25 = quarter page, 1000 = 10× page); `speed` = pixels/second (default 800). Uses `cdp.input_.synthesize_scroll_gesture` with `prevent_fling=True`, `repeat_delay_ms=0`, and a `y_distance` computed from the window bounds height.

### Decisive source
```python
(window_id, bounds) = await self.get_window()
height = bounds.height if bounds.height else 0
await self.send(cdp.input_.synthesize_scroll_gesture(
    x=0, y=0,
    y_distance=-(height * (amount / 100)),   # down = negative y
    y_overscroll=0, x_overscroll=0,
    prevent_fling=True, repeat_delay_ms=0, speed=speed))
await asyncio.sleep(height * (amount / 100) / speed)   # sleep == scroll duration
```

**Flow:** reads the window bounds, computes the pixel distance as a percentage of viewport height, sends a synthesized scroll gesture with an explicit pixel/second `speed` and `prevent_fling=True` (so the gesture doesn't trigger momentum/overscroll), then sleeps exactly `distance/speed` seconds so the script doesn't outrun the visual scroll. `scroll_up` mirrors with positive `y_distance`.
**Invariant:** the sleep is DERIVED from the gesture (distance ÷ speed), not a magic constant — this keeps pacing correct across viewport sizes and speeds. `prevent_fling` is the anti-"scripted snap" tell: without it the browser may fling/overscroll in a way real users don't. This is the scroll counterpart to the humanization-scroll capsule already in this suite (joeyism's humanized scrolling) — zendriver is the CDP-native, deterministic version.
**Probe:** no dedicated upstream unit test (needs live browser — coverage caveat). Deterministic pins (anchored at the `zendriver/` package dir): `grep -n 'synthesize_scroll_gesture' core/tab.py` → :1114,:1142; `grep -n 'prevent_fling' core/tab.py` → :1120. Behavioral adjacency: `tests/core/test_tab.py` exercises the tab's live-browser methods generally.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "scroll_down synthesize_scroll_gesture prevent_fling", limit: 5 });
```

## Verdict
Adopt: percentage-of-viewport scroll with explicit speed + prevent_fling + derived sleep. Adapt the default speed to your target site's feel. Omit the overscroll params (they're CDP-specific). Coverage: source-pinned only.
