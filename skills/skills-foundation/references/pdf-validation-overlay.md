<!-- capsule-v2 -->
# PDF Validation Overlay — how are extracted form-field boxes rendered into visual proof for a vision model?

**Source:** anthropics/skills (source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `mnt-hdd-utopia-inspo-reference-skills`. **Question:** How does create_validation_image.py turn fields.json + a page raster into the check image, and which coordinate space must it receive?

## Two-box-per-field overlay in IMAGE pixel coordinates
**Path/Symbol:** `skills/pdf/scripts/create_validation_image.py::create_validation_image` (:9–26, whole file read).
**Signature:** `create_validation_image(page_number, fields_json_path, input_path, output_path)`; CLI arity exactly 4 after script name.
**Data Shape:** reads `data["form_fields"]`, filters `field["page_number"] == page_number`, draws `field["entry_bounding_box"]` in RED width 2 and `field["label_bounding_box"]` in BLUE width 2 directly on the PIL image; prints box count.

### Decisive source
```python
for field in data["form_fields"]:
    if field["page_number"] == page_number:
        entry_box = field['entry_bounding_box']
        label_box = field['label_bounding_box']
        draw.rectangle(entry_box, outline='red', width=2)
        draw.rectangle(label_box, outline='blue', width=2)
```

**Flow:** load fields.json → open the PAGE RASTER (pdftoppm output of that one page — NOT the PDF) → per matching field draw both boxes → save.
**Invariant:** The boxes must already be in image-pixel space: this consumer sits DOWNSTREAM of pdf-dual-coordinate-systems (fields.json carries sentinel keys pdf_width/image_width; top-down coords were flipped `pdf_h − y` at extraction time). Feeding it PDF-space or top-down-space boxes silently draws in wrong places — the failure is visible only to a model looking at the output. Color coding is the contract with the reviewing agent: red = where text GOES (entry), blue = what the field MEANS (label). Counting both boxes per field makes "2×N" the sanity number in stdout.
**Probe:** No upstream tests. Deterministic probes (anchors re-derived & executed 2026-08-24): `grep -c "entry_bounding_box" skills/pdf/scripts/create_validation_image.py` = 1; `grep -c "label_bounding_box" skills/pdf/scripts/create_validation_image.py` = 1. ERRATUM: original claimed entry_bounding_box = 2 — the script reads each box ONCE (:19/:20); the "red=entry blue=label" pairing spans two distinct keys, not two occurrences of one key. Behavioral (trivially portable): render any page, synthesize two boxes, confirm red/blue rectangles land as drawn.
**Coverage caveat:** single-purpose utility; pinned by source lines only.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-reference-skills", query: "create_validation_image", limit: 5 });
// skills.skills.pdf.scripts.create_validation_image.create_validation_image Function create_validation_image.py 9-26
```

## Verdict
Adopt the pattern for any coordinate-bearing QA artifact: consume ONLY post-transform pixel-space geometry, encode semantic roles in stable colors, print a countable invariant. Adapt colors/labels; keep the downstream-of-normalization boundary explicit.
