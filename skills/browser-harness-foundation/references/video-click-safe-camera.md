<!-- capsule-v2 -->
# Click-safe camera framing — how do you auto-zoom a screencast camera without ever pushing the click under captions, chrome, or the frame edge?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** What algorithm keeps an action's click point visible at every zoom level, and how is it verified?

## Binary search for the largest safe zoom; nudge as last resort
**Path/Symbol:** `src/browser_harness/video-template.html` — safety predicate `clickPointIsSafe` + inset table (:261-265), nudge fallback `nudgePointIntoSafeArea` (:266-275), binary search `clickSafeTarget` (:276-292), per-beat target selection (:294-314), live re-evaluation in `camera(t)` follow mode (:316-342), verification ledger `clickVisibility` (:344-359).
**Signature:** `clickPointIsSafe(point, cam) -> bool` against projected screen coords; `clickSafeTarget(focus, point, scale, mode="fixed") -> {s,x,y,mode}`; insets default `{left:140,right:140,top:150,bottom:190}` overridable via `MOTION.clickSafeInset`.
**Data Shape:** camera = scale+center `{s,x,y}`; projection multiplies by stage inset `STAGE=0.94`; zoom requests come from beat `zoom.scale`, default `AUTO_ZOOM=1.7`; wide floor = `WIDE_SCALE=0.8`; search bounded to 14 iterations.

### Decisive source
```js
function clickSafeTarget(focus, point, scale, mode) {
  const requested = framedTarget(focus, scale, mode);
  if (clickPointIsSafe(point, requested)) return requested;

  // Edge actions should pull back before they push the click under captions,
  // telemetry, or the video edge. Keep the largest zoom that remains safe.
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
}
const visible = clickPointIsSafe(b.cursor, cam);
if (!visible) preflightErrors.push(`beat ${i + 1} click falls outside the safe viewport`);
```

**Flow:** every cursor-active beat gets a camera target: plain zooms use framedTarget; clicks (and auto-follow beats) route through clickSafeTarget — if the requested zoom hides the click point, binary-search DOWN from the request toward the WIDE floor for the largest still-safe scale, and only if even the floor fails, translate the camera just enough to pull the point into the inset box → `camera(t)` recomputes the same predicate per frame in follow mode so a moving cursor never crosses into an occlusion zone → after compile, `clickVisibility()` evaluates each planned click time against its final camera and pushes a preflightError for any invisible click (feeds the export gate).
**Invariant:** The action must always outrank the aesthetics: a click point may never sit under narration rail, telemetry chip, HUD, or frame edge — reduce zoom before moving the camera, move the camera before hiding the action, and verify visibility as part of the compile gate rather than trusting the renderer. Insets are screen-space constants of THIS layout (1920×1080 with bottom rail); ports must re-derive them.
**Probe:** `grep -c 'clickSafeTarget(' src/browser_harness/video-template.html` (= 4 call sites: 2 selection-time + 2 per-frame) and `grep -c 'nudgePointIntoSafeArea(' src/browser_harness/video-template.html` (= 2: def + floor fallback). No upstream JS unit suite exists — deterministic source anchors stand in (recorded caveat).

## Get live surrounding code
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "browser-harness", pattern: "clickSafeTarget", limit: 5 });` (resolves the `src.browser_harness.video-template` Module node line-exact; BM25 `search_graph` carries no tokens for this HTML file — doc-shaped-node caveat.)

## Verdict
Adopt the largest-safe-zoom binary search plus the verify-at-compile ledger for any automated camera/crop system (screen recorders, demo generators, game cameras). Adapt inset numbers and projection math to your canvas. Omit the Screen-Studio-style entrance/staging polish around it.
