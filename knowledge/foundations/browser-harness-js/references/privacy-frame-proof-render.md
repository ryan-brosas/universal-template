<!-- capsule-v2 -->
# Privacy-frame proof render — how do you produce full-resolution human-reviewable proof that redaction masks land correctly on exactly the frames the export will show?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** How does the pipeline generate reviewable evidence that every redaction rectangle is correctly placed and sized on each exported frame, without trusting a downscaled preview?

## privacyReview + privacyPageHtml — per-used-frame canvas re-render of masks at natural image scale
**Path/Symbol:** `skills/cdp/sdk/video-render.ts:privacyPageHtml` (:306-340), `privacyReview` (:342-361); frame selection by `usedFrames` (`video.ts:102-111`); driven by `review` (:420).
**Signature:** `async function privacyReview(page: BrowserPage, recording: string, composition: Json, baseUrl: string): Promise<Capture[]>` · `function privacyPageHtml(): string` · `export function usedFrames(composition: Json): string[]`.
**Data Shape:** mask spec per frame: `composition.redact[frame] = [{x,y,w,h, pad?, radius?, fill?, stroke?}]` in composition-viewport coordinates; output = one JPEG per used frame under `<recording>/.privacy-review/<frame>` plus Capture labels `privacy · <frame> · masks:<n>`.

### Decisive source
```ts
// privacy-frame.html (generated page):
const name = new URLSearchParams(location.search).get('frame') || '';
if (!/^\d+\.jpg$/.test(name)) throw new Error('invalid frame');   // vet BEFORE use
...
const sx = image.naturalWidth / viewport.w, sy = image.naturalHeight / viewport.h;
for (const rectangle of (window.COMPOSITION.redact || {})[name] || []) {
  const pad = Number(rectangle.pad ?? privacy.pad ?? 8);
  const x = Math.max(0, (rectangle.x - pad) * sx), y = Math.max(0, (rectangle.y - pad) * sy);
  const w = Math.min(image.naturalWidth - x, (rectangle.w + pad * 2) * sx);
  const h = Math.min(image.naturalHeight - y, (rectangle.h + pad * 2) * sy);
  const radius = Number(rectangle.radius ?? mask.radius ?? 7) * Math.min(sx, sy);
  context.beginPath(); context.roundRect(x, y, w, h, radius);
  context.fillStyle = rectangle.fill || mask.fill || '#f2f4f7'; context.fill();
}
window.frameReady = { width: image.naturalWidth, height: image.naturalHeight };

// privacyReview:
for (const frame of usedFrames(composition)) {
  await navigate(page, `${baseUrl}/privacy-frame.html?frame=${encodeURIComponent(frame)}`);
  const dimensions = await waitForValue(page, 'window.frameReady');
  await setMetrics(page, dimensions.width, dimensions.height);
  await capture(page, join(directory, frame), 'jpeg', 94,
    { x: 0, y: 0, width: dimensions.width, height: dimensions.height, scale: 1 });
}
```

**Flow:** wipe and recreate `.privacy-review/` → write the generated mask-rendering page → enumerate `usedFrames(composition)` (each beat's `frame` and `after` refs, dedup'd in beat order — ONLY frames the export can actually show) → for each: navigate with the encoded frame param → wait the page's own `frameReady` latch (set only after draw + masks applied) → resize the emulated viewport to the image's NATURAL pixel size → capture a clipped scale-1 JPEG q94 named exactly like the frame.
**Invariant:** PROOF AT EXPORT GEOMETRY. The review image reproduces the exact mask math the video itself uses (viewport→image scaling `sx/sy`, ±pad expansion default 8, opaque roundRect fill `#f2f4f7` default with radius 7×min(sx,sy), optional stroke clamped to [1, min(sx,sy)]) at FULL resolution — a reviewer sees precisely what will ship, not a thumbnail where an off-by-a-few-pixels mask hides. The frame query parameter is regex-vetted against `^\d+\.jpg$` before any file access, so the review surface cannot be talked into arbitrary paths.
**Probe:** no direct test (needs live Chromium). Deterministic probe executed pass 6: `grep -n "roundRect\|invalid frame\|naturalWidth / viewport" skills/cdp/sdk/video-render.ts` (:316, :323, :331).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "privacyReview", limit: 3, fields: ["signature", "name", "file"] });
```
**Retrieve (executed pass 6):** resolves `…video-render.privacyReview` @ :342-361 and companion `privacyPageHtml` @ :306-340; `get_code_snippet(video.usedFrames)` returned :102-111 confirming dedup'd beat-order `frame`/`after` collection.

## Verdict
Adopt full-resolution, used-frames-only mask proof rendered through the SAME geometry code as the artifact (and the regex vetting of any file-bearing query param); adapt pad/radius/fill defaults and JPEG quality to your redaction schema; omit the canvas-roundRect specifics only if your masks are already rasterized into the frames themselves. Caveat: untested by direct suites; the honest-redaction doctrine this proves is carried by `video-honest-chrome-and-masks.md` — read them together.
