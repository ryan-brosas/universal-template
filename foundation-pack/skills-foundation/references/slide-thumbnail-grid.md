<!-- capsule-v2 -->
# Slide Thumbnail Grid — how is a whole deck turned into labeled visual evidence without mislabeling a single slide?

**Source:** anthropics/skills (source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `mnt-hdd-utopia-inspo-reference-skills`. **Question:** How does thumbnail.py map rendered page images back to slide XML names, and how do hidden slides stay truthful?

## Registration-order walk + render-count reconciliation
**Path/Symbol:** `skills/pptx/scripts/thumbnail.py` — `get_slide_info` (:109–139), `build_slide_list` (:142–176), `convert_to_images` (:188–215), `create_grids` (:218–244), `_is_hidden` (:99–106).
**Signature:** `get_slide_info(pptx_path) -> list[{"name": str, "hidden": bool}]`; `build_slide_list(slide_info, visible_images, temp_dir) -> list[(Path, label)]`.
**Data Shape:** order source = `ppt/_rels/presentation.xml.rels` filtered to `SLIDE_REL_TYPE` → rId→part via `opc_target` (reuse of the OPC helper; TargetMode-aware) → then `ppt/presentation.xml` `p:sldId` elements walked IN ORDER pulling `r:id` — registration order defines grid position. Hidden = root `show` attr in `("0","false")` read via one-shot iterparse.

### Decisive source
```python
rendered_hidden = len(visible_images) == len(slide_info) != visible_count

if not rendered_hidden and visible_count != len(visible_images):
    raise ValueError(
        f"LibreOffice rendered {len(visible_images)} page(s) for {visible_count} "
        f"visible slide(s) of {len(slide_info)}; thumbnails would be mislabeled"
    )
```
```python
if info["hidden"] and not rendered_hidden:
    ...  # synthesize gray X-cross placeholder labeled "slideN.xml (hidden)"
```

**Flow:** soffice→PDF→pdftoppm -jpeg -r 100 → sorted glob slide-*.jpg → reconcile: if render count == total ≠ visible, LibreOffice rendered hidden slides too (consume images in order for them); else hidden slots get synthetic placeholders — and ANY other count combination RAISES rather than mislabels → chunk grids at cols×(cols+1) per image with `-N` suffixes when overflowing, labels centered above each LANCZOS-fit bordered cell.
**Invariant:** The renderer (soffice) decides whether hidden slides appear in the PDF, and the code DETECTS which regime happened from counts instead of assuming — the refusal-to-mislabel invariant beats convenience: an unmatched count aborts with the exact numbers. Slide identity comes from rels+rIds, never filename sort order. Labels carry the XML part name (`slide7.xml`), so review feedback maps directly back to edit targets.
**Probe:** No upstream tests. Deterministic probes (anchors re-derived & executed 2026-08-24): `grep -c 'thumbnails would be mislabeled' skills/pptx/scripts/thumbnail.py` = 1; `grep -c 'p:sldId' skills/pptx/scripts/thumbnail.py` = 1.
**Coverage caveat:** needs soffice+poppler on host to exercise; contract pinned to source lines.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-reference-skills", query: "get_slide_info build_slide_list", limit: 6 });
// skills.skills.pptx.scripts.thumbnail.get_slide_info Function thumbnail.py 109-139
```

## Verdict
Adopt for any document-render-and-label pipeline: derive identity from package relationships + registration order, reconcile render counts against expected before labeling, refuse over guessing, chunk oversized outputs deterministically. Adapt DPI/chunk math; keep the raise-on-mismatch.
