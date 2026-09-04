<!-- capsule-v2 -->
# coordinate-fallback-ladder — when are viewport coordinates the RIGHT targeting tool, and how do you stop using them again?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** What is the entry/exit contract for pixel-driven automation, and which stale-coordinate failure modes repeat?

## Fallback-not-default ladder
**Path/Symbol:** `skills/cdp/interaction-skills/coordinate-fallback.md` whole doc — when-to-drop (:5–11), when-NOT-to (:13–15), the loop (:17–31), getting coordinates (:33–54), primitives (:56–94), return-to-refs (:96–98), Traps (:100–108).
**Signature:** loop = `Page.captureScreenshot` → read (x,y) as vision model → `Input.dispatchMouseEvent` press/release → screenshot verify. Compute-instead-of-eyeball: `Runtime.evaluate` `getBoundingClientRect()` center for DOM-present-but-unref'd elements.
**Data Shape:** ENTER coordinates for: canvas-rendered apps (Figma/maps/games — pixels, not nodes), custom visual controls (sliders/handles/crop boxes) with no semantic role, stale/obscured/absent refs, OOPIFs you don't want to attach to, visual verification. Coordinates are MORE brittle than refs: any layout shift/scroll/animation invalidates them.

### Decisive source
```md
When refs, axTree, and selectors can't target an element reliably, drop to
**viewport-coordinate `Input.*`** and drive the page like a human reading
pixels. This is the fallback, not the default — refs are more durable than
coordinates whenever they work.
...
- **Don't coordinate-guess in a loop.** If the same coordinate fails 2–3
  times, you're almost certainly clicking stale coords. Stop, re-screenshot,
  re-read. Repeating a blind guess never self-corrects.
```

**Flow:** refs → axTree → selectors → ONLY THEN coordinates for one visual subtask → back to DOM the moment the surface returns to ordinary controls ("Don't coordinate-click a button you could have targeted by role"). CSS-vs-device-pixel division at read-off (viewport contract); wait ~300ms after animated actions; sticky headers eat coordinate space; iframe-local rects need offset addition.
**Invariant:** The ladder has an EXIT: coordinate mode is a subtask scope, not a session mode. The anti-loop rule encodes that blind retries cannot self-correct — stale coords stay stale no matter how often clicked.
**Probe:** `grep -cF 'fallback, not the default' skills/cdp/interaction-skills/coordinate-fallback.md` → 1; `grep -cF 'Return to refs as soon as you can' <same>` → 1; `grep -cF 'fails 2–3 times' <same>` → 1; `grep -cF 'stale coords' <same>` → 1.
**Retrieve:** search_code --project browser-harness-js --pattern "coordinate" (Module node resolves line-exact).

## Verdict
Adopt the ladder + exit discipline + anti-guessing rule as universal agent doctrine. Adapt dwell times and jitter per surface. Omit nothing — this doc defines when all other docs apply.
