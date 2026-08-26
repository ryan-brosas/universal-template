<!-- capsule-v2 -->
# Renderer preflight ladder + export gate — how does the runtime refuse a structurally-wrong video instead of rendering a subtly-broken one?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** Where does the rendered-video side enforce the composition contract, and what exactly happens when a rule fails?

## Accumulate-all-errors at module eval, then a single hard gate before MediaRecorder
**Path/Symbol:** `src/browser_harness/video-template.html` — preflight ladder `const preflightErrors = []` + pushes (:112-165), `window.videoPreflight` (:166-168), export gate inside `window.exportVideo` (:937-943).
**Signature:** module-scope arrays `preflightErrors`/`preflightWarnings` filled during script evaluation; `window.videoPreflight() -> {errors[], warnings[], frames[]}`; `window.exportVideo(filename)` returns a rejected Promise before any capture when errors exist.
**Data Shape:** 18 push sites cover: schemaVersion≠1; `frameStyle!=="native"` or `readingWpm!==380` (generated-typography freeze); computed DURATION over `durationBudget`; plan outside 2–5; first beat not intro card ≥4s; last beat not outcome card with outcomes; every used frame absent from `privacy.reviewedFrames`; cards shorter than their scan target (`cardTargetSeconds`); explanation points not exactly Observed|Mistake|Correction; synthetic browser chrome without `authenticity.allowSyntheticChrome=true`; redaction fill/stroke not opaque 6-digit hex (`opaqueHex`); narration >7 words; non-card beats missing valid chapter or semantic `route`; raw `url` field (route-only vocabulary); `unsafeRoute` regex hits (`@`, `?#`, `://`, `onmicrosoft`, tenant/user/object-id, UUID shapes) on `route`/`afterRoute`; plus click-outside-safe-viewport pushed from the `clickVisibility` build (:350).

### Decisive source
```js
if (!Array.isArray(C.plan) || C.plan.length < 2 || C.plan.length > 5)
  preflightErrors.push("plan must contain 2–5 steps");
for (const frame of usedFrames)
  if (!reviewedFrames.has(frame)) preflightErrors.push(`privacy review missing: ${frame}`);
...
window.exportVideo = (filename = "video.webm") => new Promise((resolve, reject) => {
  if (preflightErrors.length) {
    const message = `Export blocked: ${preflightErrors.join("; ")}`;
    window.__exportError = message;
    reject(new Error(message));
    return;
  }
  const stream = canvas.captureStream(60);
```

**Flow:** script eval compiles beats (durations, starts, cam targets) and runs every rule once, collecting ALL violations → the review harness reads `window.videoPreflight()` / `__exportError` through its marker-line protocol (see `video-browser-review-harness`) → exportVideo re-checks the array and refuses BEFORE `MediaRecorder` starts; playback/preview still works with errors present.
**Invariant:** A structurally invalid composition is UNRENDERABLE, not degraded: export is gated on zero errors; privacy review is a compile gate (an unreviewed frame fails even if it looks clean); identity material is banned at the route layer so no raw URL ever reaches the wire; errors accumulate (no first-throw) so one review pass reports everything; the check runs again at export time, so nothing can render between review and capture.
**Probe:** `grep -c 'preflightErrors.push' src/browser_harness/video-template.html` (= 18 rule sites) and `grep -cF 'Export blocked' src/browser_harness/video-template.html` (= 1 gate). No upstream JS unit suite exists — deterministic source anchors stand in (recorded caveat).

## Get live surrounding code
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "browser-harness", pattern: "videoPreflight", limit: 5 });` (resolves the `src.browser_harness.video-template` Module node line-exact; BM25 `search_graph` carries no tokens for this HTML file — doc-shaped-node caveat.)

## Verdict
Adopt the collect-all-then-gate-the-export shape for any generated-media pipeline (validate at compile, expose machine-readable verdicts, refuse capture while dirty). Adapt the specific rule set to your medium. Omit the canvas/MediaRecorder mechanics; pair with `video-integrity-gates` for the Python-side hash chain around this runtime gate.
