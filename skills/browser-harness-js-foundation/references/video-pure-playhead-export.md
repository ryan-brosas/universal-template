<!-- capsule-v2 -->
# video-pure-playhead-export — how is deterministic playback + realtime webm export achieved in one file?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** How does a canvas renderer stay seek-exact AND export a real video without a headless render farm?

## Pure-function-of-playhead rendering + MediaRecorder realtime export
**Path/Symbol:** `skills/cdp/sdk/video-template.html` inline script → header comment :2–6, `window.seek/play/pause/duration` (:928–933), `window.exportVideo` (:937–962), `tick()` rAF loop (:915–926).
**Signature:** `window.exportVideo(filename = "video.webm") => Promise<filename>` (rejects on preflight errors).
**Data Shape:** every draw is `f(playhead)` — no wall-clock state; `seek(t)` clamps and redraws exactly. Export: `canvas.captureStream(30)` → MediaRecorder with mime ladder `["video/webm;codecs=vp9","video/webm;codecs=vp8","video/webm"].find(MediaRecorder.isTypeSupported)` at `videoBitsPerSecond: 8_000_000`; chunks collected on `ondataavailable` (zero-size filtered), blob + `<a download>` click on stop; `window.__exported` sentinel for the driver to poll.

### Decisive source
```js
// Realtime export: plays once from 0 while MediaRecorder captures the canvas.
// Keep this tab focused — rAF throttles in background tabs and stalls capture.
const stream = canvas.captureStream(30);
const mime = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"]
  .find(m => MediaRecorder.isTypeSupported(m));
recorder = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 8_000_000 });
```

**Flow:** exportVideo → preflight gate → captureStream+recorder start → play(0) once through → playhead hits DURATION → recorder.stop() → blob download. The template's own comment names the operational trap: background-tab rAF throttling stalls the capture — the hardened renderer drives this tab FOREGROUND (see hardened-video-renderer.md).
**Invariant:** Determinism comes from purity (seek(t) exact ⇒ scrubbing/review trustworthy), while export is REALTIME by construction — never mix wall-clock animation into the draw path or seeks stop being exact and exports become speed-dependent. Durations are computed from word counts at readingWpm (default 380) so pacing is data-derived, not hand-tuned per beat.
**Probe:** `grep -cF 'canvas.captureStream(30)' skills/cdp/sdk/video-template.html` → 1; `grep -cF 'Keep this tab focused' <same>` → 1; `grep -cF 'videoBitsPerSecond: 8_000_000' <same>` → 1; `grep -cF 'MediaRecorder.isTypeSupported' <same>` → 1.
**Retrieve:** search_code --project browser-harness-js --pattern "captureStream" (resolves into the template Module node).

## Verdict
Adopt pure-playhead rendering + the focus-required realtime export contract together (they are two halves of one design). Adapt fps/bitrate/mime ladder to your codec targets. Omit the keyboard HUD handlers outside interactive review.
