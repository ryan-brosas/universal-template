<!-- capsule-v2 -->
# Mask rasterization plane — how do redaction rectangles defined in CSS pixels become opaque burned-in pixels in BOTH the live renderer and the offline review sheets?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** How do you rasterize privacy masks off-render so human review certifies the exact pixels that ship?

## masked_frame / privacy_review / contact_sheet trio
**Path/Symbol:** `src/browser_harness/video_render.py:contact_sheet/masked_frame/privacy_review` (:207-226, :228-251, :254-274); consumed by `review()` (:277+); live twin at `src/browser_harness/video-template.html` drawRedact (:144-151, :540-557).
**Signature:** `masked_frame(recording, comp, frame) -> PIL.Image`; `privacy_review(recording, comp) -> tuple[Path, list[dict]]`; `contact_sheet(captures, output, title) -> None`.
**Data Shape:** comp.redact = {frame: [{x,y,w,h, pad?, fill?, stroke?, radius?}]}; defaults pad=8 (privacy.pad), fill #f2f4f7 / stroke #e2e7ec / radius 7 from comp.privacy.mask; scale factors sx,sy = image px ÷ viewport CSS px; review dir `<recording>/.privacy-review` (stale *.jpg unlinked first); sheet 4 cols × tile 400×225 + label_h 34 + banner 42 on #171a20; captures carry {path,time,label:"privacy · <frame> · masks:N"}.

### Decisive source
```python
sx, sy = image.width / vw, image.height / vh
for rectangle in redactions.get(frame, []):
    rect_pad = float(rectangle.get("pad", pad))
    x0 = max(0, (float(rectangle["x"]) - rect_pad) * sx)
    y1 = min(image.height, (float(rectangle["y"]) + float(rectangle["h"]) + rect_pad) * sy)
    radius = float(rectangle.get("radius", mask.get("radius", 7))) * min(sx, sy)
```

**Flow:** privacy_review iterates video.used_frames(comp), raises `missing frame: <name>` on absent source, renders masked_frame → quality=94 JPG per frame into .privacy-review, labels each with its mask count; review() later merges these full-res captures with mode/click captures and renders ONE contact_sheet (quality=91) titled "PRIVACY · EVERY BEAT · EXACT CLICK + RESULT" as renderer-review-contact-sheet.jpg.
**Invariant:** masks are OPAQUE by contract (preflight bans non-six-digit-hex fill/stroke in BOTH planes — video-template.html :149/:151 vs the same defaults hardcoded here); rect coords are clamped to image bounds (max(0,…)/min(width|height,…)) so a bad rect degrades to a partial mask instead of an exception; radius scales by min(sx,sy) to stay visually equal across axes; the Python plane re-implements the canvas defaults verbatim (#f2f4f7/#e2e7ec/7) because review sheets must show the same pixels the live renderer draws — if you change one default, change both or review lies.
**Probe:** From repo root: `grep -n 'def contact_sheet\|def masked_frame\|def privacy_review' src/browser_harness/video_render.py` → exactly :207/:228/:254; `grep -n 'quality=91' src/browser_harness/video_render.py` → :225 (sheet) and `grep -n 'quality=94' …` → :266 (privacy frames); dual-plane census `grep -c 'redact' src/browser_harness/video-template.html src/browser_harness/video_render.py` → 4 and 4 lines respectively (sum per file, not total). No unit test covers this plane — coverage caveat.
**Anchored at the repo root** (paths are repo-root-relative).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "masked_frame privacy review mask", limit: 10, fields: ["signature", "file"] });
```
(Resolves privacy_review :254-274 + masked_frame :228-251 line-exact.)

## Verdict
Adopt a second, offline rasterization of every privacy-sensitive region so review artifacts are pixel-faithful. Adapt geometry keys. Keep clamp-don't-throw rectangle handling unless your rects are machine-generated only.
