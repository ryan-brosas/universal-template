<!-- capsule-v2 -->
# Bench pier paired comparison — how do you compare two agent-eval jobs trial-by-trial when trial directory names differ between runs, and refuse to average unmatched pairs?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what loading/pairing discipline makes a two-job A/B report over external `result.json` trees statistically honest?

## Deterministic rep indexing by start order + strict (task, rep) key-set equality before any delta
**Path/Symbol:** `bench/analyze_pier.py`: `_cell` (:21-59), `load_job` (:62-75), `_values` (:78-79), `summarize` (:82-112), `pair_cells` (:115-144), `paired_summary` (:147-162), `print_report` (:173-195), `main` (:198-220). Direct tests: `bench/test_analyze_pier.py` whole (86L, 2 tests OK via stdlib unittest).
**Signature:** `load_job(path: Path) -> list[dict]`; `pair_cells(left, right) -> list[{"task","rep","left","right","delta"}]`; `paired_summary(pairs) -> {"pairs", "median_delta_<metric>", "mean_delta_<metric>"}`.

### Decisive source
```python
task_cells.sort(key=lambda cell: (cell["started_at"], cell["trial"]))
for rep, cell in enumerate(task_cells):
    cell["rep"] = rep                      # deterministic pairing index per task
# …
left_index  = {(cell["task"], cell["rep"]): cell for cell in left}
right_index = {(cell["task"], cell["rep"]): cell for cell in right}
if left_index.keys() != right_index.keys():
    raise ValueError(f"Jobs are not matched; missing left={missing_left[:5]}, missing right={missing_right[:5]}")
```

**Flow:** each trial's `result.json` becomes a flat cell with DEFENSIVE derivations: combined tokens fall back to input+output when metadata lacks `combined_total_tokens`; fresh input falls back to input−cache. Trials within a task are ordered by `(started_at, trial)` and indexed as rep 0..n — so "a-late"/"a-early" on one side pairs with "a-1"/"a-2" on the other despite unrelated directory names. Pairing then REQUIRES equal (task, rep) key sets; any gap raises with up to five missing keys named per side — averages over silently-dropped trials are impossible by construction. Deltas (`right − left`) are computed only where both cells carry numeric values; summaries report medians/means over numeric-only lists, solve counts as `reward == 1`, and `whole_read_rate` guards its zero denominator.
**Invariant:** pairing is positional-within-task by recorded start time, never by filesystem name; unmatched jobs fail LOUDLY; every aggregate tolerates missing fields but never fabricates them.
**Probe:** executed byte-for-byte: `grep -n "not matched" bench/analyze_pier.py` → :125; `grep -n 'cell\["rep"\] = rep' bench/analyze_pier.py` → :74; suite: `cd bench && python3 -m unittest test_analyze_pier -v` → Ran 2 tests, OK (pins rep order [0,1], token deltas [-20,-40], whole_read_rate 0.25, median_delta_outer_calls −1.5).

## Get live surrounding code
**Retrieve:** executed live against project `pi-fabric`:
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "load_job pair_cells paired_summary matched jobs rep task started order median delta", limit: 6 });
```
(Rank #3–6 resolve `load_job` :62-75, `paired_summary` :147-162, `pair_cells` :115-144 plus both pinning test methods line-exact.)

## Verdict
Adopt start-order rep indexing plus strict key-set-equality pairing for any A/B comparison of externally-produced run artifacts; adapt the metric list and result.json field names to your evaluator; omit the fabric-specific metadata columns (outer/nested calls, whole-read rate) unless your agent records the same observability — the invariant to keep is loud rejection of unmatched corpora.
