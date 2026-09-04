<!-- capsule-v2 -->
# Repeat-run dual naming — how do N repetitions of one case stay distinct in reports while remaining groupable back to the source case?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How are repeated evaluations named, and when is `source_case_name` set vs left None?

## `_build_tasks_to_run` expansion + positional fallback names
**Path/Symbol:** `pydantic_evals/pydantic_evals/dataset.py:Dataset._build_tasks_to_run` (:269-279); consumers `_run_task_and_evaluators(source_case_name=...)` (:1107-1133) and reporting aggregation.
**Signature:** `_build_tasks_to_run(repeat: int) -> list[tuple[Case, str, str | None]]` — (case, report_case_name, source_case_name).
**Data Shape:** Report names embed a 1-based run index; `source_case_name` is None IFF repeat == 1.

### Decisive source
```python
if repeat > 1:
    return [(case, f'{case_name} [{run_idx}/{repeat}]', case_name)
            for i, case in enumerate(self.cases, 1)
            for run_idx in range(1, repeat + 1)
            if (case_name := case.name or f'Case {i}')]
else:
    return [(case, case.name or f'Case {i}', None) for i, case in enumerate(self.cases, 1)]
```

**Flow:** Unnamed cases get POSITIONAL report names (`f'Case {i}'`, 1-based dataset position) while their STORED name stays None — evaluation never mutates the dataset. With repeat>1 every row carries `[run/total]` in its report name and its original name as source_case_name (which also becomes the `logfire.experiment.source_case_name` span attribute); with repeat==1 source_case_name stays None so downstream `case_groups()` treats the experiment as single-run and returns None.
**Invariant:** The dual-name pair (report display name vs grouping key) is the contract: display uniqueness by run index, grouping stability by original name. Setting source_case_name unconditionally would flip single-run experiments into degenerate groups downstream.
**Probe:** `tests/evals/test_dataset.py::test_unnamed_cases` (:1616-1640) pins stored-None vs reported-'Case 1'/'Case 3'; `tests/evals/test_multi_run.py::test_repeat_with_unnamed_cases` asserts exact order `['Case 1 [1/2]', 'Case 1 [2/2]', 'Case 2 [1/2]', 'Case 2 [2/2]']`; `test_repeat_1_produces_identical_behavior` (:55-75) pins all-source_case_name-None.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_build_tasks_to_run repeat source_case_name", limit: 6 });
```
Live check this pass: search_graph mapped Dataset methods (:269-279 decisive); test_multi_run.py executed GREEN at pin (42 passed incl. multi-run file).

## Verdict
Adopt the expansion grammar and the None-means-single-run sentinel. Adapt the `[i/n]` display format to your report surface; keep stored cases immutable and grouping keyed on source names.
