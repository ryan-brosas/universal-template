<!-- capsule-v2 -->
# Report diff table — how are added/removed cases and per-key diffs rendered, and who owns the ascii_only decision?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How does a baseline-vs-report diff handle cases present on one side only, missing keys, and terminals that cannot encode ✔/✗/→?

## three-way case partition + renderer-inference over union
**Path/Symbol:** `pydantic_evals/pydantic_evals/reporting/__init__.py` — `EvaluationRenderer.build_diff_table` (:1558-1626), `_baseline_cases_to_include` (:1486-1490), `ReportCaseRenderer.build_diff_row` (:1133-1199), `_render_dicts_diff` (:1297-1314), `_render_assertion_mark` (:1378-1381); glyph helpers `_check_mark/_cross_mark/_arrow` (:69-78).
**Signature:** `build_diff_table(report, baseline, *, with_title=True) -> Table`; `_render_dicts_diff(baseline_dict, new_dict, renderers) -> str`.
**Data Shape:** rows keyed by case NAME (assertion `baseline.name == new_case.name`); columns auto-omitted when empty via `include_scores(report, baseline)`-style predicates scanning BOTH sides.

### Decisive source
```python
for case_id in sorted(set(baseline_cases_by_id.keys()) | set(report_cases_by_id.keys())):
    if maybe_baseline_case and maybe_report_case: diff_cases.append(...)
    elif maybe_baseline_case: removed_cases.append(maybe_baseline_case)
    else: added_cases.append(maybe_report_case)
...
# added row prefix:
row[0] = f'[green]+ Added Case[/]\n{row[0]}'
```

**Flow:** baseline cases filtered to report-matching names unless `include_removed_cases` → sorted union of names partitioned into diff/removed/added → diff rows use per-key renderers where a key present on ONE side renders the other side as `[i]<missing>[/i]`; equal rendered values collapse to a single string → added/removed rows get green/red prefixed labels → averages row from flat averaging → metadata panel above shows per-key +/-/arrow styles.
**Invariant:** The console OWNS ascii_only (`console.options.ascii_only`) and threads it through every renderer — rich degrades its own glyphs but NOT text we hand it, so a redirected Windows stdout would raise UnicodeEncodeError without these ASCII fallbacks (in-source comment). Column inclusion predicates scan both reports so a score appearing only in the baseline still gets a column. `render_value` returning '' falls back to `'-'` EMPTY_CELL_STR, keeping table geometry stable.
**Probe:** `tests/evals/test_reporting.py` (27 tests incl. diff rendering + ascii glyph fallbacks); `tests/evals/test_report_evaluators.py::test_report_rendering_includes_analyses` (:502+).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"EvaluationRenderer build_diff_table","limit":3,"detail":"compact"}'
```
Live check this pass: rank-1 line-exact `reporting/__init__.py 1558-1626`.

## Verdict
Adopt the partition/missing-value/ascii threading. Adapt to your table library. Omit rich Panel/Table specifics if your host renders differently — keep the ownership rule (caller's console decides encoding). Direct tests executed GREEN at pin.
