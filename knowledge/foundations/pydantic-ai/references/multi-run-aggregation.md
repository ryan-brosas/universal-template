<!-- capsule-v2 -->
# Multi-run aggregation — how does averaging work for repeat runs, and why does the diff table use a different average than the summary table?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do per-case multi-run results aggregate into group summaries, and why is `build_diff_table`'s average computed differently from `build_table`'s?

## source_case_name grouping + two-level vs flat averages
**Path/Symbol:** `pydantic_evals/pydantic_evals/reporting/__init__.py` — `ReportCase.source_case_name` (:111-113), `EvaluationReport.case_groups` (:343-378), `averages` (:380-392), `ReportCaseAggregate.average` (:193-255), `average_from_aggregates` (:257-313), diff-table divergence comment (:1614-1624).
**Signature:** `case_groups() -> list[ReportCaseGroup] | None` (None when NO case/failure carries `source_case_name`, i.e. single-run); `average(cases) -> ReportCaseAggregate`; `averages()` picks two-level when grouped.
**Data Shape:** aggregate = synthetic case `{name='Averages', scores: dict[str,float], labels: dict[str, dict[str,float]] (value→frequency), metrics, assertions: float|None (pass rate), task_duration, total_duration}`.

### Decisive source
```python
# build_diff_table:
# Use flat averaging for both sides to keep the diff symmetric.
# baseline_cases is already filtered to only cases matching the report.
# Note: for multi-run reports, this differs from build_table which uses two-level
# aggregation via report.averages(). In practice the results are identical when all
# runs succeed (equal group sizes), and only diverge with partial failures within a
# group — a rare edge case. We can revisit if users report confusing behavior.
report_average = ReportCaseAggregate.average(report_cases) if report_cases else None
```

**Flow:** run-indexed cases carry their original name in `source_case_name` → `case_groups` buckets cases AND failures by it (fallback `case.name`) preserving insertion order → each group's summary = `average(runs)` (label distributions averaged as value→frequency dicts; assertion pass-rate = passing/total with None when zero assertions) → `averages()` = group summaries averaged AGAIN via `average_from_aggregates` when grouped, flat otherwise → renderer appends one `[b i]Averages[/]` row.
**Invariant:** The deliberate flat-vs-two-level asymmetry exists to keep DIFFS symmetric (baseline side filtered to matching names); equal group sizes make both identical — only partial-failure groups diverge, documented in-source as an accepted trade-off rather than a bug. Empty-input arms return the zeroed 'Averages' aggregate (never raise), and label averaging divides by COUNT OF RUNS CONTAINING THE KEY, not total runs.
**Probe:** `tests/evals/test_reporting.py::test_report_case_aggregate_average` (:390-483) pins score/label/metric/assertion averaging incl. missing-key handling; `tests/evals/test_multi_run.py` covers group assembly.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"ReportCaseAggregate average","limit":3,"detail":"compact"}'
```
Live check this pass: rank-1 line-exact `reporting/__init__.py 194-255`.

## Verdict
Adopt the aggregation semantics including the documented flat-vs-grouped divergence. Adapt aggregate field names. Omit nothing — the comment IS the spec for the asymmetry. Direct tests executed GREEN at pin (27-test reporting suite).
