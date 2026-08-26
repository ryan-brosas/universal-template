<!-- capsule-v2 -->
# video-clicksafe-camera — how does the camera keep the click visible while zooming?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** How does a canvas video renderer zoom toward an action without letting captions/telemetry/the frame edge cover the click?

## Safe-click camera targeting
**Path/Symbol:** `skills/cdp/sdk/video-template.html` inline script → `CLICK_SAFE`, `clickPointIsSafe`, `nudgePointIntoSafeArea`, `clickSafeTarget` (:44–47, :261–292), per-beat visibility audit :344–358.
**Signature:** `clickSafeTarget(focus, point, scale, mode = "fixed") => { s, x, y, mode }`.
**Data Shape:** `CLICK_SAFE = { left: 140, right: 140, top: 150, bottom: 190, ...(MOTION.clickSafeInset || {}) }` — screen-space insets reserving caption rail + telemetry + edge. Camera targets computed PER BEAT at load; each click beat's projected cursor position is checked and a preflight error is pushed if the FINAL camera still leaves it outside the safe area (`beat N click falls outside the safe viewport`).

### Decisive source
```js
let low = Math.min(scale, WIDE_SCALE), high = scale;
let best = framedTarget(focus, low, mode);
if (!clickPointIsSafe(point, best)) return nudgePointIntoSafeArea(best, point);
for (let n = 0; n < 14; n++) {
  const mid = (low + high) / 2;
  const candidate = framedTarget(focus, mid, mode);
  if (clickPointIsSafe(point, candidate)) { best = candidate; low = mid; }
  else high = mid;
}
return best;
```

**Flow:** requested zoom → if click already safe, keep it → else binary-search (14 iterations) the LARGEST zoom that keeps the projected click inside the safe inset → if even WIDE_SCALE fails, translate the camera to pull the point into the box instead.
**Invariant:** Zoom preference order: keep the largest safe zoom; degrade to recentering only when no zoom works. The check runs against the camera AT CLICK TIME (reaction lag included), not beat start — and the result is audited again in `clickVisibility`, feeding preflight. A porter who clamps the zoom first (or checks at t=0) hides clicks under the caption rail.
**Probe:** `grep -cF 'function clickPointIsSafe' skills/cdp/sdk/video-template.html` → 1; `grep -cF 'n < 14' <same>` → 1; `grep -cF 'left: 140, right: 140, top: 150, bottom: 190' <same>` → 1.
**Retrieve:** search_code --project browser-harness-js --pattern "clickSafeTarget" (Module node resolves line-exact).

## Verdict
Adopt the binary-search-largest-safe-zoom + post-audit pattern for any synthetic-camera screencast renderer. Adapt the inset pixel values and the STAGE=0.94 backdrop margin to your layout. Omit the Screen-Studio-style window entrance easing if you don't emulate chrome.
