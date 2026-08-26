<!-- capsule-v2 -->
# PDF Form Fill Fork — how do you fill a PDF form, and why does the path split on fillable fields before anything else?

**Source:** anthropics/skills (pdf skill, source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What is the decision procedure for filling any PDF form, and what invariant must hold before a single value is written?

## Fillability gate → two disjoint pipelines
**Path/Symbol:** `skills/pdf/forms.md` (whole doc, 294 lines); probe script `skills/pdf/scripts/check_fillable_fields.py` (whole, 13 lines).
**Signature:** `python scripts/check_fillable_fields.py <file.pdf>` → prints "This PDF has fillable form fields" iff `PdfReader.get_fields()` is truthy, else the non-fillable message.
**Data Shape:** `get_fields()` returns AcroForm field dictionaries or `None`. The fork is binary and mandatory: fillable → field-ID-driven pipeline (`extract_form_field_info.py` JSON of `{field_id, page, rect, type}` + per-type extras `checked_value`/`radio_options`/`choice_options`; build `field_values.json` keyed by `field_id`; `fill_fillable_fields.py` validates IDs+values server-side and refuses invalid entries); non-fillable → coordinate-driven annotation pipeline (`extract_form_structure.py` → labels/lines/checkboxes/row_boundaries; Approach A structure-based PDF coords, Approach B visual zoom-crop pixel coords, Hybrid converts image→PDF via `pdf_x = image_x * pdf_width/image_width`).

### Decisive source
```markdown
If you need to fill out a PDF form, first check to see if the PDF has
fillable form fields. Run this script ... and depending on the result go to
either the "Fillable fields" or "Non-fillable fields" and follow those
instructions.
```
```python
reader = PdfReader(sys.argv[1])
if (reader.get_fields()):
    print("This PDF has fillable form fields")
else:
    print("This PDF does not have fillable form fields; you will need to visually determine where to enter data")
```

**Flow:** check_fillable_fields → fillable? extract field info JSON → analyze page PNGs (`convert_pdf_to_images.py`) to learn each field's PURPOSE (IDs are opaque like `Checkbox12`) → `field_values.json` (checkbox values MUST be the field's own `checked_value`, e.g. `/On`) → fill script validates and errors name the bad entries : non-fillable? structure extraction → meaningful labels? Approach A else visual Approach B → `check_bounding_boxes.py` gate → annotate-fill → re-render and verify placement.
**Invariant:** The fork happens BEFORE any writing attempt — you never try to set AcroForm values on a flat PDF or overlay annotations on a live form. Checkbox/radio values are never invented; they come from the extracted `checked_value`/`radio_options`. Both pipelines end in the same verification loop: rasterize the output and LOOK at it (pairs with render-verify-loop).
**Probe:** No unit tests upstream (docs+scripts repo). Deterministic probes: run `check_fillable_fields.py` against a form-bearing and a flat PDF and observe the two messages; grep `forms.md` for `get_fields`-gated fork wording and `/On` checked-value example.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "fillable form fields", limit: 10 });
```

## Verdict
Adopt the gate-first fork, purpose-learning via rendered pages before filling, checked-value discipline, and validate→fix→refill loops — they transfer to any headless PDF pipeline. Adapt the bundled-script paths to your host layout; substitute your own renderer if poppler/pypdf are absent. Omit nothing here; the fork is the whole contract. Caveat: behavior is pinned by scripts + prose, no direct tests.
