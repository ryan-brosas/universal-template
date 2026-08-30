<!-- capsule-v2 -->
# PDF Tool Ladder — for a given PDF operation, which library does the reference bless and why?

**Source:** anthropics/skills (pdf skill, source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** When several libraries can do the same PDF task, which does the skill's advanced reference pick per task, and what are the pinned performance claims?

## Task→tool mapping with explicit speed/quality tradeoffs
**Path/Symbol:** `skills/pdf/reference.md` (611 lines, read whole): pypdfium2 render/text :5–44; pdf-lib load/create/merge :46–168; pdfjs-dist browser render + coords + annotations :170–263; poppler CLI (`pdftotext -bbox-layout`, `pdftoppm -r`, `pdfimages`) :265–299; qpdf split/pages/linearize/check/fix-qdf/encrypt :301–341; pdfplumber chars/bbox/tables :345–383; reportlab platypus tables :385–424; batch error-continue pattern :463–507; performance ladder :528–565; encrypted/corrupted troubleshooting :567–601.
**Signature:** N/A (prose+recipes; the contract is the mapping table below).
**Data Shape:** one canonical tool per operation: render→pypdfium2 (PDFium/Chromium engine, `page.render(scale=)` → PIL); JS mutation→pdf-lib (`copyPages` for cross-doc page theft); in-browser→pdfjs-dist (worker setup mandatory); text-with-coords→`pdftotext -bbox-layout` XML ("fastest for plain text"); structured tables→pdfplumber (`vertical_strategy:"lines"`, snap/intersection tolerances); embedded images→`pdfimages` ("much faster than rendering pages"); structural surgery/split/repair→qpdf (`--check`, `--fix-qdf`, `--replace-input`); generation with styled tables→reportlab.

### Decisive source
```markdown
- `pdftotext -bbox-layout` is fastest for plain text extraction
- Use pdfplumber for structured data and tables
- Avoid `pypdf.extract_text()` for very large documents
...
- `pdfimages` is much faster than rendering pages
```
```python
except Exception as e:
    logger.error(f"Failed to process {pdf_file}: {e}")
    continue   # batch pattern: per-file failure never kills the run
```

**Flow:** pick tool by TASK first (never by language availability alone) → large files: stream or qpdf-split, process pages individually → batch jobs wrap per-file work in try/log/continue so one corrupt PDF doesn't abort the sweep → corrupted input: `qpdf --check` diagnoses, `--fix-qdf`/`--replace-input` repairs in place → OCR (pytesseract over pdf2image rasters) only as last resort when no text layer exists.
**Invariant:** The ladder encodes measured tradeoffs as rules, not suggestions — e.g. rendering pages to get images wastes the embedded originals; pypdf's pure-Python extractor loses to poppler at scale; form structure survives best under pdf-lib. A porter substituting a different tool inherits an unmeasured regression.
**Probe:** No runner. Deterministic probes (anchors re-derived & executed byte-exact 2026-08-24 from repo root): `grep -c 'bbox-layout' skills/pdf/reference.md` = 2; license footer verified line-exact at :603–611 — poppler-utils "GPL-2 License" vs qpdf "Apache License" (redistribution-relevant distinction confirmed); the blessing-line greps above are the executable anchors.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-reference-skills", query: "pdftotext bbox-layout pdfimages", limit: 10 });
```

## Verdict
Adopt the mapping and the batch try-log-continue shape for any document-processing harness. Adapt tool availability to your host (the ladder degrades gracefully: pdfplumber↔pypdfium2 cover most needs). Omit the tutorial code bodies — keep the mapping + rationale. Caveat: prose-only pinning; claims are the upstream author's measurements.
