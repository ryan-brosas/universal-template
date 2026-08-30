<!-- capsule-v2 -->
# PDF Pre-Fill Bounding-Box Gate — what must be validated about hand-authored field geometry before any annotation is committed?

**Source:** anthropics/skills (pdf skill, source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** Which two geometric failure modes does the pipeline refuse before filling, and why is the gate mandatory in all three approaches?

## Intersection + font-fit checks with capped message flood
**Path/Symbol:** `skills/pdf/scripts/check_bounding_boxes.py` (`get_bounding_box_messages` :14–66; `rects_intersect` :18–21; label/entry pair collection :24–27; entry-height check :41–49).
**Signature:** `python scripts/check_bounding_boxes.py fields.json` → human-readable messages ending `SUCCESS: All bounding boxes are valid` or `FAILURE: ...` lines (abort note after 20).
**Data Shape:** reads the same fields.json the filler consumes (label_bounding_box + entry_bounding_box per field); checks only within equal `page_number`.

### Decisive source
```python
def rects_intersect(r1, r2):
    disjoint_horizontal = r1[0] >= r2[2] or r1[2] <= r2[0]
    disjoint_vertical = r1[1] >= r2[3] or r1[3] <= r2[1]
    return not (disjoint_horizontal or disjoint_vertical)
...
if entry_height < font_size:
    has_error = True
    messages.append(f"FAILURE: entry bounding box height ({entry_height}) ... is too short for the text content (font size: {font_size}). Increase the box height or decrease the font size.")
```

**Flow:** collect 2 rects per field → O(n²) pairwise intersection test per page (self-intersection = label overlapping its own entry) → per-entry height vs `font_size` (default 14) → first 20 failures then abort. The doc mandates this gate at the end of Approach A (:163–168), Approach B (:247–252), and again as global Step 2 (:270–279) — "Always validate bounding boxes before filling".
**Invariant:** Geometry errors surface HERE or they surface on paper: intersecting boxes produce overlapping printed text and short boxes clip glyphs — both invisible until a human looks at the rasterized page. The gate converts visual failures into named, fixable JSON errors pre-commit. Note the top-down coordinate convention makes "height" simply `rect[3]-rect[1]` regardless of mode.
**Probe:** No unit tests upstream. Deterministic probe (anchors re-derived & executed 2026-08-24 from repo root): `grep -c 'FAILURE\|SUCCESS: All bounding boxes are valid' skills/pdf/scripts/check_bounding_boxes.py` = 4 (both message classes present; `rects_intersect` :18–21 and the entry-height check :41–49 pin the two FAILURE classes in source); the two-overlaps-plus-short-entry fixture behavior remains a fixture-level observation — recorded honestly, not re-executed this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-reference-skills", query: "check bounding boxes", limit: 5 });
```

## Verdict
Adopt the validate-before-write gate and both check semantics verbatim for any annotation-placement pipeline. Adapt message formatting to your harness. Omit nothing. Caveat: no direct tests; behavior pinned by source read.
