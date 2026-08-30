<!-- capsule-v2 -->
# XLSX Recalc Gate — how does an openpyxl-written formula file get cached values, and which exit codes lie about workbook health?

**Source:** anthropics/skills (xlsx skill, source-available per LICENSE.txt) `main@3b3fad96`; Codebase Memory `skills`. **Question:** Why do formulas written by openpyxl read back as None, what is the recalculation contract, and how is a clean exit distinguished from a healthy workbook?

## LibreOffice in-place recalculation with JSON verdict
**Path/Symbol:** `skills/xlsx/scripts/recalc.py` (module docstring lines 1-6; `EXTERNAL_REF_RE` at line 23; `RECALCULATE_MACRO` StarBasic module at 26-32; MAX_LOCATIONS=100); contract documented at `skills/xlsx/SKILL.md` "Recalculate (mandatory...)" lines 29-56.
**Signature:** `python scripts/recalc.py output.xlsx [timeout_seconds=30]` → JSON `{status: success|errors_found, total_formulas, total_errors, error_summary}`.
**Data Shape:** openpyxl writes formula STRINGS with no cached values; until recalculation every formula cell reads back as `None` to pandas / `load_workbook(data_only=True)` / previewers. LibreOffice computes all formulas and REWRITES THE FILE IN PLACE.

### Decisive source
```markdown
LibreOffice computes every formula, the file is **rewritten in place**, and
you get JSON: `status` (`success` | `errors_found`), `total_formulas`,
`total_errors`, and an `error_summary` naming up to 100 cells per error type
... Fix what it names and run it again. **JSON with an `error` key instead of
a `status` means nothing was recalculated**, and only that case exits non-zero
— `errors_found` exits 0, so never treat a clean exit as a clean workbook.

**A green recalc proves your formulas *evaluate*, not that they are *right*.**
```
```python
EXTERNAL_REF_RE = re.compile(r"""(?<![\w"\[])'?\[\d+\][^!"\[\]]*'?!""")
```

**Flow:** Write workbook via openpyxl → run recalc.py → parse JSON status → if `errors_found`, fix named cells (up to 100 locations per error type; trust `total_errors` over list length) and rerun → only `status:"success"` ships. External-link guard: a formula like `='[1]Returns Analysis'!$B$2` indexes the external-references list — re-saving strips cached values, LibreOffice then resolves for real, fails to `#NAME?` and DELETES every link, so recalc.py refuses to run (`--force` overrides accepting loss); copy those values out of the original first.
**Invariant:** Clean process exit ≠ clean workbook (`errors_found` exits 0); a missing `status` key is the ONLY failure signal that means nothing ran; green recalc validates evaluability, never correctness (off-by-one ranges yield error-free wrong numbers — write 2-3 probe formulas first); `.xlsm` needs `keep_vba=True` or macros are lost on rewrite.
**Probe:** Run `recalc.py` on a fresh openpyxl file containing `=SUM(B2:B9)` — before recalc `data_only=True` reads None everywhere; after recalc the cached value appears and JSON reports `total_formulas ≥ 1`. Feed it a workbook with an external `[1]Sheet!A1` ref and observe the refusal.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "recalculate store LibreOffice", limit: 10 });
```

## Verdict
Adopt: mandatory recalc-after-write, exit-code skepticism, external-link refusal semantics, evaluate≠correct separation — a complete integrity gate for any headless spreadsheet pipeline. Adapt the LibreOffice wrapper (`office/soffice.py` env handling) to your host. Omit the StarBasic macro text if your LO build exposes a CLI recalc. Caveat: no unit tests upstream; script behavior is the probe.
