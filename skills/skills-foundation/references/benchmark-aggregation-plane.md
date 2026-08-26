<!-- capsule-v2 -->
# Benchmark aggregation plane — what must A/B run aggregation discover dynamically, and where do its defaults lie?

**Source:** anthropics/skills (Apache-2.0) `main@3b3fad96`; Codebase Memory `skills`. **Question:** How does aggregate_benchmark turn a tree of grading.json files into honest with-skill/without-skill statistics, and which of its numbers are measured versus placeholder?

## Discovery + metric-extraction ladder (`aggregate_benchmark.py`, whole file)
**Path/Symbol:** `skills/skill-creator/scripts/aggregate_benchmark.py` — `load_run_results` (:67–173), `aggregate_results` (:176–224), `calculate_stats` (:45–64), `generate_benchmark` (:227–278).
**Signature:** `load_run_results(benchmark_dir: Path) -> dict[str, list]`; `aggregate_results(results: dict) -> dict`; `calculate_stats(values: list[float]) -> dict`.
**Data Shape:** layout `eval-N/<config>/run-M/grading.json` (optionally under `runs/`); grading carries `summary{pass_rate,passed,failed,total}`, optional `timing`, `execution_metrics`, `expectations[]`, `user_notes_summary`.

### Decisive source
```python
# :100-107 — config names are DISCOVERED, never hardcoded
for config_dir in sorted(eval_dir.iterdir()):
    if not config_dir.is_dir():
        continue
    if not list(config_dir.glob("run-*")):
        continue          # skip inputs/, outputs/, etc.
    config = config_dir.name
# :206-209 — delta is first-two-configs by directory insertion order
if len(configs) >= 2:
    primary = run_summary.get(configs[0], {})
    baseline = run_summary.get(configs[1], {})
```

**Flow:** pick search root (`runs/` if present, else direct `eval-*`, else print + return `{}`) → per eval dir resolve `eval_id` through a three-step ladder (eval_metadata.json → int dirname suffix → enumeration index; each step catches its own parse error) → discover config dirs dynamically → per run: warn-and-skip missing/invalid grading.json → extract summary metrics → timing fallback chain (`grading.timing.total_duration_seconds`, then sibling timing.json which ALSO supplies tokens) → token fallback to `execution_metrics.output_chars` when unset → validate expectations carry `text`+`passed` (warning only; evidence documented) → notes = uncertainties + needs_review + workarounds concatenated → `calculate_stats` gives mean/stddev/min/max rounded to 4 with SAMPLE stddev (n−1; n=1 ⇒ 0.0; empty ⇒ zero-dict) → delta = signed mean differences between configs[0] (primary) and configs[1] (baseline).
**Invariant:** Nothing about configuration identity is assumed — any dir containing `run-*` is a config, so new_skill/old_skill or three-way comparisons work unchanged; the delta is ORDER-DEPENDENT (sorted-dirname order decides which side is baseline) and is formatted, not normalized (`f"{delta_pass_rate:+.2f}"`). Placeholder metadata (`"<skill-name>"`, `executor_model: "<model-name>"`, hardcoded `runs_per_configuration: 3`) is filled later by the analyzer — benchmark.json numbers from load/aggregate are real, metadata strings are not.
**Probe:** No upstream tests exist repo-wide. Deterministic anchors (executed this pass):
`grep -c 'runs_per_configuration": 3' skills/skill-creator/scripts/aggregate_benchmark.py` = 1;
`grep -cF 'list(config_dir.glob("run-*"))' skills/skill-creator/scripts/aggregate_benchmark.py` = 1 (the guard line is `if not list(...)` at :105 — a config dir must CONTAIN runs);
behavioral (executed): `calculate_stats([0.5])` → `{'mean': 0.5, 'stddev': 0.0, 'min': 0.5, 'max': 0.5}` and `calculate_stats([])` → all-zero dict (n=1 ⇒ zero stddev; empty ⇒ zero-dict).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "load_run_results grading eval config discovery", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: dynamic config discovery, three-step eval_id ladder, warn-and-skip per-run loading, timing fallback chain, sample-stddev stats. Adapt: delta semantics if you need normalized effect sizes or named primary/baseline. Omit: the markdown table renderer if you post to a different UI; do NOT trust metadata placeholders or the hardcoded runs_per_configuration as measurements. Caveat: no upstream tests; claims pinned by whole-file source read + executed probes.
