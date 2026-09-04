<!-- capsule-v2 -->
# zoomed-after-annotation — Why does the judge get a zoomed AFTER crop, and how is it anchored?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** How is the zoom region computed and enhanced, and when is it omitted?

## Zoom seam
**Path/Symbol:** `gui_agents/s3/bbon/behavior_narrator.py:get_zoomed_image` (:106-168) + wiring in `judge` (:201-238).
**Signature:** `get_zoomed_image(image_bytes, x, y, width=300, height=300, upscaling=False, scale=4, add_bounding_box=False) -> Tuple[bytes, bytes]`.
**Data Shape:** Returns (zoomed crop bytes [WEBP], full-frame bytes optionally with red bounding box). Anchor = coordinates of the LAST mouse sub-action (`mouse_actions[-1]`). judge() calls with width=height=300, scale=4, upscaling=True, add_bounding_box=True.

### Decisive source
```python
cx, cy = x - width // 2, y - height // 2        # center the crop on the anchor
W, H = img.size
left  = min(max(cx, 0), W - width)              # clamp so the crop stays inside
top   = min(max(cy, 0), H - height)
right, bottom = left + width, top + height
zoomed_img = img.crop((left, top, right, bottom))
if upscaling:
    zoomed_img = cv2.resize(zoomed_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    zoomed_img = cv2.fastNlMeansDenoisingColored(zoomed_img, None, 5, 5, 7, 21)
# no-mouse-action arm: zoom is OMITTED entirely
else:
    after_img_message = {...plain after image...}; zoomed_after_img_message = None
```

**Flow:** last mouse coord from the action string → 300×300 crop centered there (clamped at edges) → Lanczos ×4 upscale + fast non-local-means denoise (targets JPEG speckle) → both the zoomed view and the full frame with a red rectangle marking WHERE the zoom lives are sent as separate message parts ("ZOOMED AFTER:").
**Invariant:** (1) The clamp formula `min(max(v,0), dim-size)` keeps crop size constant near borders (shifts the window rather than shrinking). (2) Zoom exists ONLY for mouse actions — keyboard-only turns send the plain after image; the prompt's claim of a zoom accompanies "any mouse action". (3) The bounding box on the full frame is what lets the model localize the zoom within the screen; sending zoom alone loses context. (4) compress_image re-encodes to WEBP unconditionally (halves payload; format chosen over PNG purely for size).
**Probe:** `grep -n 'min(max(cx, 0), W - width)' gui_agents/s3/bbon/behavior_narrator.py` → :138.
**Probe:** `grep -n 'fastNlMeansDenoisingColored' gui_agents/s3/bbon/behavior_narrator.py` → :161.
**Probe:** `grep -n 'ZOOMED AFTER:' gui_agents/s3/bbon/behavior_narrator.py` → :255.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "get_zoomed_image add_bounding_box upscaling", limit: 5 });
```

## Verdict
Adopt anchor-centered clamped crops with paired full-frame context for change-detection judges; adapt crop size/denoise to your resolution; omit cv2 if your images are clean. The no-mouse ⇒ no-zoom branch is part of the contract.
