<!-- capsule-v2 -->
# Contact-sheet capture latch — how do you screenshot a generated HTML gallery of evidence images as ONE complete image without racing image loading?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** When your review artifact is an HTML grid of dozens of screenshots, how do you capture the whole grid deterministically — no half-loaded tiles, no clipped rows, no stale viewport size?

## makeContactSheet + contactSheetHtml — image-complete latch, then measure, then one shot
**Path/Symbol:** `skills/cdp/sdk/video-render.ts:contactSheetHtml` (:373-377), `makeContactSheet` (:379-387), `waitForValue` (:229-240); consumed by `review` (:427) and by the export path's final sheet.
**Signature:** `async function makeContactSheet(page: BrowserPage, recording: string, captures: Capture[], output: string, title: string, baseUrl: string): Promise<void>` · `function waitForValue<T>(page, expression, timeoutMs = 10_000): Promise<T>`.
**Data Shape:** `Capture = { path, time, label }`; sheet HTML is regenerated each run at `<recording>/video-review-contact-sheet.html` or `renderer-final-contact-sheet.html` (chosen by whether `output` ends with `final-contact-sheet.jpg`); final artifact is a single full-page JPEG q91.

### Decisive source
```ts
const html = output.endsWith('final-contact-sheet.jpg') ? 'renderer-final-contact-sheet.html' : 'video-review-contact-sheet.html';
writeFileSync(join(recording, html), contactSheetHtml(recording, captures, title));
await setMetrics(page, 1660, 900);
await navigate(page, `${baseUrl}/${html}`);
await waitForValue(page, '[...document.images].every(image => image.complete && image.naturalWidth)');
const size = await evaluate(page, '({width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight})');
await capture(page, output, 'jpeg', 91, { x: 0, y: 0, width: size.width, height: size.height, scale: 1 });

// waitForValue poll kernel:
while (Date.now() < deadline) {
  try { const value = await evaluate(page, expression); if (value) return value; }
  catch (error) { lastError = error; }
  await delay(50);
}
throw new Error(`renderer did not become ready: ${String(lastError || expression)}`);
```

**Flow:** write the grid HTML with every tile `<img src>` percent-encoded per path segment and captions HTML-escaped → set a generous working viewport → navigate → LATCH: poll every 50ms until EVERY `document.images` entry is `complete && naturalWidth > 0` (broken images never satisfy the latch) → only then read `scrollWidth/scrollHeight` so the document has its final layout → ONE full-page clipped screenshot at scale 1.
**Invariant:** ORDER IS LOAD-BEARING: latch → measure → shoot. Measuring before images finish yields a short page and a cropped sheet; shooting before the latch yields gray tiles. The latch tests `naturalWidth > 0`, not merely `.complete`, because a failed load also reports `complete`. The two-html-names split means the export-time final sheet never overwrites the review-time sheet mid-pipeline, and both names sit on `serveDirectory`'s allowlist (`isServableRecordingFile`, :100-108) so the token-guarded file server will serve them. `waitForValue` swallows per-iteration evaluation errors but surfaces the LAST one on timeout — a crash loop diagnoses itself.
**Probe:** no direct test (needs live Chromium). Deterministic probe executed pass 6: `grep -n "image.complete && image.naturalWidth\|renderer-final-contact-sheet\|scrollWidth" skills/cdp/sdk/video-render.ts` (:104, :380, :385).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "makeContactSheet", limit: 3, fields: ["signature", "name", "file"] });
// EXECUTED pass 6: resolves browser-harness-js.skills.cdp.sdk.video-render.makeContactSheet @ video-render.ts:379-387.
```

## Verdict
Adopt the complete-then-measure-then-shoot latch (with the `naturalWidth` strengthening) for any headless capture of generated galleries; adapt grid CSS, viewport seed size, and JPEG quality; omit the dual-filename dance only if your pipeline never regenerates sheets concurrently with reviewing them. Caveat: untested by direct suites; the serving half of this contract is separately pinned in `hardened-video-renderer.md`.
