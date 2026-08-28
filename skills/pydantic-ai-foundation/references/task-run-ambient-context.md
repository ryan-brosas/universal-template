<!-- capsule-v2 -->
# Task-run ambient context — how does user code record attributes/metrics from inside an evaluated run, and why must nested evaluation be suppressed?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter exposing in-run instrumentation (`set_eval_attribute`, `increment_eval_metric`) must decide what happens when those calls run OUTSIDE any evaluated context, how span-derived metrics merge with user-recorded ones, and how the system prevents an online-eval decorator from double-evaluating a function already running under `Dataset.evaluate()`.

## ContextVar accumulator + silent no-op + nesting guard
**Path/Symbol:** `pydantic_evals/pydantic_evals/_task_run.py:TaskRun/run_task/extract_span_tree_metrics/CURRENT_TASK_RUN` (whole file, :1-77); `pydantic_evals/pydantic_evals/dataset.py:set_eval_attribute/increment_eval_metric` (:1263-1284); `pydantic_evals/pydantic_evals/online.py:OnlineEvalConfig.should_evaluate` (:597-600); `pydantic_evals/pydantic_evals/otel/_context_subtree.py` (whole file).
**Signature:** `run_task() -> Generator[Callable[[], dict[str, Any]]]` (contextmanager); `set_eval_attribute(name: str, value: Any) -> None`; `increment_eval_metric(name: str, amount: int | float) -> None`.
**Data Shape:** `TaskRun` holds `attributes: dict[str, Any]` and `metrics: dict[str, int|float]`; the yielded closure returns `{'attributes', 'metrics', 'duration', '_span_tree'}` which is splatted into `EvaluatorContext(**kwargs)`.

### Decisive source
```python
@contextmanager
def run_task():
    task_run = TaskRun()
    token = CURRENT_TASK_RUN.set(task_run)
    def get_eval_context_kwargs():
        return {'attributes': task_run.attributes, 'metrics': task_run.metrics,
                'duration': duration, '_span_tree': span_tree}
    t0 = time.perf_counter()
    try:
        with context_subtree() as span_tree:
            yield get_eval_context_kwargs
    finally:
        duration = time.perf_counter() - t0
        CURRENT_TASK_RUN.reset(token)
    if isinstance(span_tree, SpanTree):
        extract_span_tree_metrics(task_run, span_tree)   # AFTER reset — late enrichment

def set_eval_attribute(name, value):
    current_case = _task_run.CURRENT_TASK_RUN.get()
    if current_case is not None:          # SILENT no-op outside a run
        current_case.record_attribute(name, value)

# TaskRun.increment_metric zero-suppression:
def increment_metric(self, name, amount):
    current_value = self.metrics.get(name, 0)
    incremented_value = current_value + amount
    if current_value == 0 and incremented_value == 0:
        return                             # 0+0 never creates the key
    self.record_metric(name, incremented_value)

# online.py — the nesting guard shared by decorator AND capability paths:
def should_evaluate(self):
    return self.enabled and not _EVALUATION_DISABLED.get() and _task_run.CURRENT_TASK_RUN.get() is None
```

**Flow:** `run_task()` sets the ContextVar, opens `context_subtree()` (in-memory OTel exporter; when opentelemetry-sdk/logfire is absent the fallback yields a `SpanTreeRecordingError` with a teaching message instead of a tree), yields the kwargs closure for the duration of the evaluated body, then in finally measures duration and RESETS the ContextVar BEFORE `extract_span_tree_metrics` walks the tree — nodes carrying `gen_ai.request.model` count `requests` when `gen_ai.operation.name == 'chat'`, accumulate `operation.cost` → `cost`, and strip `gen_ai.usage.details.` / `gen_ai.usage.` prefixes into metric names. User calls to `set_eval_attribute`/`increment_eval_metric` read the ContextVar and no-op silently when it is unset. Because extraction runs after user code finishes, span-derived and user-recorded metrics land in the SAME dicts the evaluator sees.
**Invariant:** Unguarded user instrumentation must NEVER crash outside an evaluated context (silent no-op, not exception). The zero-suppression rule keeps phantom metrics absent (`increment('phantom', 0)` creates no key) while `record_metric` has no such gate. The nesting guard is the third clause of `should_evaluate()` — online evaluation inside `Dataset.evaluate()` (which itself runs under `run_task`) must be suppressed, or every dataset case would be double-evaluated by its own decorators. A porter who resets the ContextVar before measuring duration, or extracts metrics before the subtree closes, gets empty trees.
**Probe:** `tests/evals/test_online.py::test_set_eval_attribute_in_async_function` (:1958-1976) pins `ctx.attributes == {'model': 'gpt-4o', 'region': 'us-east-1'}`; `test_increment_eval_metric_in_async_function` (:1980-1999) pins merged increments `{'tokens': 200, 'requests': 1}`; `test_attributes_and_metrics_empty_by_default` (:2045-2060) pins empty dicts; `test_online_eval_suppressed_inside_task_run` (:2064-2086) pins the nesting guard (0 sink calls with `CURRENT_TASK_RUN` set); `tests/evals/test_dataset.py::test_increment_eval_metric` (:725-740) pins the same API on the dataset path including `increment_eval_metric('phantom', 0)` creating no key; `tests/evals/test_online_capability.py::test_usage_metrics` (:137-156) pins span-extracted `requests > 0` from instrumentation alone.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "CURRENT_TASK_RUN run_task extract_span_tree_metrics should_evaluate", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session; anchors confirmed by direct read of _task_run.py whole, dataset.py :1263-1284, online.py :597-600, otel/_context_subtree.py whole at pin `a5b5fb7a`.

## Verdict
Adopt the ContextVar-accumulator-with-yielded-closure shape (the closure captures duration/span_tree by reference so post-body enrichment works), the silent no-op public API, the zero-suppression increment, and the three-clause `should_evaluate` nesting guard. Adopt the fallback-error-object pattern for missing optional dependencies (yield an error that teaches, not a crash). Adapt the `gen_ai.*` prefix table to your host's semconv. Omit nothing else — the plane is 77 lines plus two 12-line functions. Coverage caveat: none — all cited files read whole this pass.
