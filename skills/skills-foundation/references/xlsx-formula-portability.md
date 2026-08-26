<!-- capsule-v2 -->
# XLSX Formula Portability — which formulas survive LibreOffice verification, and which silently truncate to one cell?

**Source:** anthropics/skills (xlsx skill, source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** Which functions can an openpyxl-written workbook use so that (a) the verification runtime evaluates them and (b) Excel accepts them — and which must never be written?

## Function whitelist + dual-load reading rule
**Path/Symbol:** `skills/xlsx/SKILL.md` "Choosing formulas that survive verification" (lines 60-71) + "openpyxl gotchas" (lines 73-79).
**Signature:** N/A — formula-string authoring contract for `sheet['B10'] = '=...'`.
**Data Shape:** openpyxl writes formulas into XML VERBATIM; Excel stores post-2007 function names `_xlfn.`-prefixed (UI hides the prefix). A formula LibreOffice cannot parse is written back LOWERCASED beside a `#NAME?`.

### Decisive source
```markdown
- **Prefer Excel-2007-era functions** — `SUMIFS`, `INDEX`, `MATCH`, `IFERROR`,
  `SUMPRODUCT` — which need no prefix.
- **Six post-2007 functions work, but only with an `_xlfn.` prefix** ...
  `_xlfn.TEXTJOIN`, `_xlfn.CONCAT`, `_xlfn.IFS`, `_xlfn.SWITCH`, `_xlfn.MAXIFS`,
  `_xlfn.MINIFS`. Written bare, each yields `#NAME?`.
- **Never use `XLOOKUP`, `XMATCH`, `SORT`, `FILTER`, `UNIQUE`, or `SEQUENCE`.**
  The runtime's LibreOffice cannot evaluate them under *any* prefix. Newer
  builds do evaluate them, but they are spilling array functions and an
  openpyxl-written file has no spill metadata, so only the top-left cell of
  the range gets a value — and `recalc.py` reports `total_errors: 0` on the
  truncated result. Use `INDEX`/`MATCH` for lookups.
- **Reading a model takes two loads.** `data_only=True` yields cached values
  with the formulas gone; the default yields formula strings with no values.
- **`data_only=True` is destructive if you save.**
```

**Flow:** Author with 2007-era core → need TEXTJOIN/CONCAT/IFS/SWITCH/MAXIFS/MINIFS? write them `_xlfn.`-prefixed → never emit dynamic-array functions; sort/filter/dedupe in Python before writing cells → read models with TWO loads (values pass + formula pass) → never save a `data_only=True` handle (it permanently replaces every formula with its literal) → quote sheet names containing spaces in cross-sheet refs (`='Assumptions Inputs'!$B$5`) or get `#VALUE!`.
**Invariant:** The verification runtime's function coverage defines the portable subset — a function outside it either hard-fails (`#NAME?`) or, worse, SILENTLY truncates spill results while recalc reports zero errors. Formulas are the deliverable, not Python-computed constants ("the sheet must recalculate when its inputs change").
**Probe:** Write `=TEXTJOIN(",",TRUE,A1:A3)` bare vs `_xlfn.TEXTJOIN(...)` in two cells, run recalc.py: bare → lowercased `#NAME?`; prefixed → evaluates. Write `=SEQUENCE(3)` → single top-left value with `total_errors: 0`, demonstrating silent truncation.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "skills", "pattern": "formulas", "limit": 10}'
# resolves `skills/xlsx/SKILL.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt: the three-tier function policy (2007-core / `_xlfn.`-six / forbidden-spillers), two-load reading, and data_only-save destructiveness — all stem from how openpyxl+LibreOffice+Excel actually interact. Adapt the exact runtime boundary if your verifier is real Excel instead of LO. Omit financial-model color/number conventions unless producing finance workbooks (worth adopting wholesale when you do). Caveat: prose-pinned contract; probes are behavioral via recalc.py.
