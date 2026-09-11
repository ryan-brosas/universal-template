<!-- capsule-v2 -->
# PDF Form Structure Extraction — how do you get machine-usable coordinates out of a flat (non-fillable) PDF?

**Source:** anthropics/skills (pdf skill, source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** How is form geometry (labels, rows, checkboxes) recovered from a PDF with no AcroForm fields, and when must the pipeline fall back to vision?

## pdfplumber words/lines/rects → structure JSON
**Path/Symbol:** `skills/pdf/scripts/extract_form_structure.py` (`extract_form_structure` :16–80; word labels :28–36; wide-line row boundaries :37–43; square-rect checkbox heuristic :44–53); consumed by `skills/pdf/forms.md` Approaches A/B/Hybrid.
**Signature:** `python scripts/extract_form_structure.py <input.pdf> form_structure.json` → `{pages:[{page_number,width,height}], labels:[{page,text,x0,top,x1,bottom}], lines:[{page,y,x0,x1}], checkboxes:[{page,x0,top,x1,bottom,center_x,center_y}], row_boundaries:[...]}`.
**Data Shape:** labels = every extracted WORD (not line of text) with PDF-point coords rounded to 0.1; "row boundary" = horizontal line spanning > 50% of page width; checkbox = rect with both sides in [5,15]pt AND |width−height|<2 — deliberately conservative.

### Decisive source
```python
if abs(float(line["x1"]) - float(line["x0"])) > page.width * 0.5:
    structure["lines"].append(...)
...
if 5 <= width <= 15 and 5 <= height <= 15 and abs(width - height) < 2:
    structure["checkboxes"].append(...)
```
```markdown
If the PDF is scanned/image-based and structure extraction found no usable
text labels (e.g., all text shows as "(cid:X)" patterns), use Approach B.
```

**Flow:** extract per page → group adjacent words into label phrases, cluster by similar `top` into rows → entry area derives geometrically: `x0 = label.x1 + 5`, right edge = next label's x0 or the row's boundary line below. Structure output drives Approach A; scanned pages (cid-garbage text, no labels) force visual estimation with magick zoom-crops; Hybrid mixes per-field and converts everything to one system before shipping.
**Invariant:** Detection has known blind spots the doc names — circular checkboxes (only SQUARE rects match), decorative graphics, faded elements — so structure JSON is trusted only after cross-checking against rendered page images ("Check for Missing Elements"). Entry coordinates are DERIVED from label+row geometry, never guessed freely when structure exists.
**Probe:** No unit tests upstream. Deterministic probe: run the extractor on a lined form PDF and verify labels carry real text while `(cid:X)` output routes to Approach B per the doc's routing rule; grep the 5–15pt/square heuristics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "extract form structure", limit: 5 });
```

## Verdict
Adopt the extraction heuristics (>50%-width row rule, square-checkbox window) and the cid-pattern→vision fallback trigger as ported behavior. Adapt pdfplumber to your host's text-layer extractor. Omit the doc's worked examples. Caveat: script-only pinning.
