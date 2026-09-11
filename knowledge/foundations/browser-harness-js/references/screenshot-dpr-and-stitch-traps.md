<!-- capsule-v2 -->
# screenshot-dpr-and-stitch-traps — what coordinate system do screenshots return, and when does full-page capture lie?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** How do pixels read off a screenshot map back to Input.* coordinates, and when does captureBeyondViewport corrupt the page?

## DPR + full-page trap matrix
**Path/Symbol:** `skills/cdp/interaction-skills/screenshots.md` whole doc — core calls (:7–26), when-to-shoot (:28–32), element shots via DOM.getBoxModel (:34–49), Traps (:51–55); cross-ref viewport.md + scrolling.md.
**Signature:** `Page.captureScreenshot({format, quality?, clip?, captureBeyondViewport?})`; element clip: `DOM.getBoxModel` → `model.border` = `[x1,y1, x2,y1, x2,y2, x1,y2]` (4 corners) → origin = first two numbers.
**Data Shape:** viewport-only default (fastest, matches user); JPEG ~5× smaller for eyeballing; `clip` in page coordinates; high-DPI returns DEVICE-pixel image — coordinates read off it must be divided by devicePixelRatio before Input.*.

### Decisive source
```md
- **Verification:** after every meaningful action. The DOM can lie about
  state; pixels cannot.
- `captureBeyondViewport: true` re-layouts the page (fires resize). Don't use
  it in the middle of a user-driven flow — use viewport shots.
...
- Pages with fixed/sticky headers over `captureBeyondViewport` can produce
  duplicated headers down the stitched image.
```

**Flow:** discovery-shot after navigate before inventing selectors → verification-shot after meaningful actions → coordinate-debug loop (shot → read → Input → shot) → element shot = getBoxModel clip.
**Invariant:** Screenshots are ground truth BECAUSE they bypass DOM state; but captureBeyondViewport mutates layout (resize event + sticky-header duplication), so the truth-telling mode must not itself disturb a live flow. The devicePixelRatio division is the difference between clicking the target and clicking 2–3× off.
**Probe:** `grep -cF 'captureBeyondViewport' skills/cdp/interaction-skills/screenshots.md` → 3; `grep -cF 'device-pixel image' <same>` → 1; `grep -cF 'model.border' <same>` → 2; `grep -cF 'pixels cannot.' <same>` → 1.
**Retrieve:** search_code --project browser-harness-js --pattern "captureScreenshot" (Module node resolves line-exact).

## Verdict
Adopt viewport-default + verify-with-pixels discipline and the getBoxModel element-clip recipe as portable primitives. Adapt format/quality policy to your token budget. Omit nothing else.
