<!-- capsule-v2 -->
# Budget evaluators — why does MaxToolCalls default to counting failures while MaxModelRequests prefers a metric?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do the two budget evaluators source their counts, and why do their defaults differ?

## include_failed asymmetry + metrics-first request count
**Path/Symbol:** `pydantic_evals/pydantic_evals/evaluators/agentic.py:MaxToolCalls` (:510-542) and `MaxModelRequests` (:545-582).
**Signature:** `MaxToolCalls(max_calls: int, include_failed: bool = True)`; `MaxModelRequests(max_requests: int)` (no include_failed — model requests have no failure semantics here).
**Data Shape:** reasons carry the observed count and budget (`'2 tool call(s), budget=1'` / `'3 model request(s) (from ctx.metrics['requests']), budget=2'`) so threshold tuning is readable from reports.

### Decisive source
```python
# MaxToolCalls: failed attempts still consumed time and tokens
include_failed: bool = True
...
tool_count = _count_tool_calls(span_tree, include_failed=self.include_failed)

# MaxModelRequests: prefer the recorded metric, fall back to identical span criteria
metric = ctx.metrics.get('requests')
if isinstance(metric, int | float):
    request_count = int(metric); source = "ctx.metrics['requests']"
else:
    request_count = _count_model_requests(span_tree); source = 'span tree'
```

**Flow:** ToolCorrectness/TrajectoryMatch/ArgumentCorrectness all default `include_failed=False` (a retry after ModelRetry should not break trajectory assertions), but MaxToolCalls INVERTS to `True` because a failed attempt still burns budget — the module docstring calls this exception out explicitly. MaxModelRequests counts spans carrying `gen_ai.request.model` + `operation.name == 'chat'`, the SAME criteria `_task_run.extract_span_tree_metrics` uses for its `requests` metric (in-source comment), so metric-first and span-first paths agree whenever both exist.
**Invariant:** A porter who copies one default to the other gets wrong budgets in both directions: strict-correctness defaults undercount spend; budget defaults overcount logical work. The `isinstance(metric, int|float)` guard means a non-numeric `requests` metric silently falls back to span counting instead of crashing.
**Probe:** `tests/evals/test_agentic_evaluators.py::test_max_tool_calls_counts_failed_attempts_by_default` (:289-303) asserts both directions of the inversion; `test_max_model_requests_from_metrics` (:950-956) pins the metrics-first source label.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"MaxModelRequests metrics requests","limit":3,"detail":"compact"}'
```
Live check this pass: rank-1 direct test `test_agentic_evaluators.py 950-956`, rank-2 class `agentic.py 546-582`.

## Verdict
Adopt both evaluators with their asymmetric defaults and dual-source count. Adapt metric key names. Omit nothing. Direct tests executed GREEN at pin.
