<!-- capsule-v2 -->
# video-honest-chrome-and-masks — when does the renderer draw fake browser chrome, and how are secrets masked?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** How does the template keep synthetic framing from masquerading as captured evidence, and why opaque masks instead of blur?

## Honesty defaults + opaque redaction
**Path/Symbol:** `skills/cdp/sdk/video-template.html` inline script → `FRAME_STYLE` (:32–35), chrome gate :141–142 + :405–414, `drawRedact` :550–569, mask fill/stroke preflight :143–153, typing redact :573, sticky() :499–504.
**Signature:** `drawRedact(r)` — page-rect → padded screen-space roundRect, `ctx.globalAlpha = 1` forced.
**Data Shape:** `FRAME_STYLE = C.frameStyle || "native"`; "native" = raw frame only; "browser" draws macOS light-theme traffic lights/tab/toolbar but REQUIRES `authenticity.allowSyntheticChrome === true` (preflight error otherwise). In-browser chrome text comes ONLY from beat-carried `route`/`tab`/`url` fields resolved through `sticky(i,key)` (most recent earlier non-empty beat wins); in-code comment: "Native framing keeps the recording honest: no reconstructed tab title or fake URL masquerading as captured browser evidence." Masks default `#f2f4f7` fill / `#e2e7ec` stroke; must be opaque six-digit hex (preflight-enforced).

### Decisive source
```js
// Opaque masks may match their surrounding surface, but never use alpha: unlike
// blur or pixelation, secrets cannot be reconstructed from them.
function drawRedact(r) {
  ...
  ctx.globalAlpha = 1;
  roundRect(x, y, w, h, radius);
  ctx.fillStyle = fill; ctx.fill();
```

**Flow:** composition declares frameStyle → synthetic chrome opt-in only via authenticity flag → masks drawn over every SHOWN source each frame (`shown` tracks which images were actually painted incl. the after-transition) → typed text renders `"••••••"` when `b.type.redact` is set (fail-closed twin of recording-privacy-scrub).
**Invariant:** Redaction must be OPAQUE and re-applied per shown frame — alpha/blur/pixelation are reversible; drawing masks only on the primary frame leaks them through the after-frame. Sticky-field resolution prevents one beat's URL from bleeding into unrelated shots' chrome.
**Probe:** `grep -cF 'secrets cannot be reconstructed' skills/cdp/sdk/video-template.html` → 1; `grep -cF 'hard cut unless explicitly asked' <same>` → 1; `grep -cF 'sticky(i,' <same>` ≥ 4; `grep -cF 'C.readingWpm || 380' <same>` → 1; `grep -cF 'b.type.redact ? "••••••"' <same>` → 1.
**Retrieve:** search_code --project browser-harness-js --pattern "drawRedact" (resolves into the template Module node).

## Verdict
Adopt opaque-only masking, per-shown-frame re-application, and the allowSyntheticChrome honesty gate as a unit. Adapt palette/radius/pad defaults. Omit the macOS chrome illustration outside screencast products that deliberately label themselves as reconstructions.
