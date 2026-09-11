<!-- capsule-v2 -->
# EvaluatorContext lazy span-tree — how does an evaluator access telemetry that may not exist without a try/except at every call site?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How should a context object expose optional OTel data so missing instrumentation raises at USE time with full information, not construction time?

## error-as-field + raising property
**Path/Symbol:** `pydantic_evals/pydantic_evals/evaluators/context.py:EvaluatorContext` (:30-103, property `span_tree` :86-103); error carrier `SpanTreeRecordingError` from `..otel._errors`.
**Signature:** `_span_tree: SpanTree | SpanTreeRecordingError` (dataclass field, `repr=False`); `@property def span_tree(self) -> SpanTree`.
**Data Shape:** the field holds either a real `SpanTree` or a pre-built recording-error instance; attributes/metrics are plain dicts populated via `set_eval_attribute` / `increment_eval_metric` during task execution.

### Decisive source
```python
_span_tree: SpanTree | SpanTreeRecordingError = field(repr=False)
"""This will be a `SpanTreeRecordingError` if opentelemetry is not available, or if an incompatible
opentelemetry `TracerProvider` is in use."""
...
@property
def span_tree(self) -> SpanTree:
    if isinstance(self._span_tree, SpanTreeRecordingError):
        # In this case, there was a reason we couldn't record the SpanTree. We raise that now
        raise self._span_tree
    return self._span_tree
```

**Flow:** dataset runner constructs the context once per case, storing either the captured tree or the reason capture was impossible → evaluators that need telemetry read `ctx.span_tree`, catching `SpanTreeRecordingError`; evaluators that don't (Equals, Contains…) never touch it and work un-instrumented.
**Invariant:** Construction never fails and never logs — the failure mode is deferred into the value itself. This is why every span-based evaluator in `agentic.py` wraps its first `ctx.span_tree` access in `try: ... except SpanTreeRecordingError: return EvaluationReason(value=False, reason=_NO_SPAN_TREE_REASON)` — degrade to a failing score with an actionable message, don't crash the run. A porter who instead makes the field Optional-and-None loses the *reason* instrumentation was missing.
**Probe:** `tests/evals/test_agentic_evaluators.py` fixtures build contexts with `_span_tree=SpanTreeRecordingError(...)` directly (`_ctx()` helper :174-190) and assert graceful failing reasons; `tests/evals/test_evaluator_base.py::test_evaluator_sync` (:140-172) runs evaluators against an error-carrying context.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"EvaluatorContext span_tree","limit":3,"detail":"compact"}'
```
Live check this pass: rank-1 line-exact `context.py 31-103`.

## Verdict
Adopt the error-as-field pattern for any lazily-available capability (telemetry today; caches, feature flags tomorrow). Adapt the exception type name. Omit nothing. Direct tests executed GREEN at pin across both suites.
