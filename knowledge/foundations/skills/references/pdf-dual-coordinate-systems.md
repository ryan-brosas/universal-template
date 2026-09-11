<!-- capsule-v2 -->
# PDF Dual Coordinate Systems — why does the same fields.json accept two coordinate systems, and how does the filler know which it got?

**Source:** anthropics/skills (pdf skill, source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** How are structure-extracted PDF-point coordinates and visually-estimated image-pixel coordinates unified into one fillable input without a mode flag?

## Sentinel keys + Y-flip transforms
**Path/Symbol:** `skills/pdf/scripts/fill_pdf_form_with_annotations.py` (`transform_from_image_coords` :10–20, `transform_from_pdf_coords` :23–30, dispatch :52–67, skip-guards :69–74, `FreeText` emission :80–90); contract at `skills/pdf/forms.md` :134/:226 ("Use pdf_width...signals PDF coordinates" / "image_width...signals image coordinates") and Hybrid conversion :263–266.
**Signature:** `transform_from_pdf_coords(bbox, pdf_height) -> (left, bottom, right, top)`; `transform_from_image_coords(bbox, img_w, img_h, pdf_w, pdf_h) -> same`. Dispatch: `"pdf_width" in page_info` → PDF-coords transform; else image-coords transform.
**Data Shape:** fields.json = `{pages: [{page_number, pdf_width?, pdf_height? | image_width?, image_height?}], form_fields: [{page_number, description, field_label, label_bounding_box, entry_bounding_box, entry_text}]}`. The PRESENCE of the sentinel key is the mode bit — no explicit coordinate-system field exists.

### Decisive source
```python
top = pdf_height - (bbox[1] * y_scale)
bottom = pdf_height - (bbox[3] * y_scale)
...
pypdf_top = pdf_height - bbox[1]
pypdf_bottom = pdf_height - bbox[3]
```
```markdown
**Important**: Use `pdf_width`/`pdf_height` and coordinates directly from
form_structure.json.   /   **Important**: Use `image_width`/`image_height`
and the refined pixel coordinates from the zoom analysis.
```

**Flow:** Both source systems measure top-down with origin at top-left; pypdf annotation rects want bottom-up PDF space — every path flips Y (`pdf_h − y`, scaled first for pixels). Per page: look up real mediabox dims → pick transform by sentinel key → emit one `FreeText` annotation (border_color/background_color None so only text lands) via `writer.add_annotation(page_number=page_num−1)`. Empty/missing `entry_text.text` entries are silently skipped (:73), not errors.
**Invariant:** Mixing systems in ONE file corrupts placement silently — the Hybrid section exists precisely to convert visual estimates back into PDF points so a single system ships; the doc says "Use a single coordinate system in fields.json". A porter who feeds raw top-down coords to pypdf gets vertically mirrored text with no error.
**Probe:** No unit tests upstream. Deterministic probes (anchors re-derived & executed byte-exact 2026-08-24 from repo root): `sed -n '134p' skills/pdf/forms.md` = "Create fields.json using \`pdf_width\` and \`pdf_height\` (signals PDF coordinates):" and `sed -n '226p'` = the image-coords twin (both sentinel-key lines line-exact); `grep -c 'transform_from_image_coords' skills/pdf/scripts/fill_pdf_form_with_annotations.py` ≥ 1; the 1-field round-trip render comparison remains a fixture-level observation — recorded honestly, not re-executed this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-reference-skills", query: "transform_from_image_coords", limit: 5 });
```

## Verdict
Adopt the sentinel-key mode detection and the always-flip-Y rule for any top-down→PDF-space porting. Adapt the FreeText defaults (Arial 14pt black) and pypdf dependency to your host. Omit nothing else — the transforms ARE the contract. Caveat: script-only pinning, verified by reading + deterministic reruns.
