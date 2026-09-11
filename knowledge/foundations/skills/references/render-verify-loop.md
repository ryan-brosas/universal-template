<!-- capsule-v2 -->
# Render-Verify Loop — what mandatory QA closes the gap between "file written" and "document correct"?

**Source:** anthropics/skills (docx/pptx skills, source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** After generating an Office document, what is the exact render-and-inspect procedure, and which defects does it catch that validation cannot?

## soffice → pdftoppm → look at every page
**Path/Symbol:** `skills/docx/SKILL.md` "Verify the output" (lines 35-44); `skills/pptx/SKILL.md` "QA (Required)" + "Converting to Images" (lines ~200-233); wrapper `scripts/office/soffice.py` (`get_soffice_env`, `run_soffice`) used by xlsx recalc.py too.
**Signature:** `python scripts/office/soffice.py --headless --convert-to pdf out.pptx && rm -f slide-*.jpg && pdftoppm -jpeg -r 150 out.pdf slide && ls -1 "$PWD"/slide-*.jpg`.
**Data Shape:** PDF intermediates; JPEG pages zero-padded by page-count width (`slide-01.jpg` for 10-99, `slide-001.jpg` for 100+); content QA via `markitdown output.pptx` (one block per slide under `<!-- Slide number: N -->`; xlsx: `## SheetName` per sheet).

### Decisive source
```markdown
After writing a `.docx`, render it and look at it:
```bash
python scripts/office/soffice.py --headless --convert-to pdf output.docx
pdftoppm -jpeg -r 100 output.pdf page
ls page-*.jpg   # then Read the images
```
...
Your first render usually has a few real issues — overlaps, overflow,
misalignment. Find and fix those, re-render only the slides you changed,
and stop.
...
**Text overflow or text cut off at a box or slide boundary — check this
first.** It is the most common defect and always user-visible.
...
**After fixes, rerun all four commands above** — the PDF must be regenerated
from the edited `.pptx` before `pdftoppm` can reflect your changes.
```

**Flow:** Content QA (markitdown text dump: missing content, typos, wrong order; template decks grep for placeholder leftovers `\bx{3,}\b|lorem|ipsum|\bTODO|\[insert`) → file QA (schema validator, `--original` when template-derived) → visual QA: convert to PDF → rasterize → inspect EVERY page fresh ("after staring at the generating code you tend to see what you expect rather than what rendered" — a subagent is ideal) → fix → REGENERATE PDF from the edited file before re-rasterizing → stop.
**Invariant:** The rendered artifact is ground truth, not the generator's intent; stale rasters must be rm'd first or fixes appear unapplied; font-substitution caveat — LibreOffice renders fonts it doesn't have with different widths, so QA text-fit on non-safe-list fonts is approximate (~10% slack), while Arial/Calibri/Cambria/Times/Courier/Bookman/Century Schoolbook are metric-reliable both in QA and Office.
**Probe:** No unit tests upstream. Deterministic probes (anchors re-derived & executed 2026-08-24 from repo root): `grep -c 'run_soffice\|get_soffice_env' skills/docx/scripts/office/soffice.py` = 8 (wrapper surface present; xlsx recalc.py consumes the same env shim); the overflow-deck demonstration remains a fixture-level observation — recorded honestly, not re-executed this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "soffice convert-to pdf pdftoppm", limit: 10 });
```

## Verdict
Adopt the full three-gate loop (content/file/visual) for any document-generation pipeline — it is tool-agnostic. Adapt rasterization DPI and the safe-font list to your environment. Omit pptx-specific design guidance unless producing decks. Caveat: depends on LibreOffice + poppler on host; prose-pinned, no unit tests.
