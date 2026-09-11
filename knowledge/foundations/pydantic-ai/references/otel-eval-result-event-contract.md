<!-- capsule-v2 -->
# OTel evaluation-result event contract — what exactly does each result/failure emit, and how does emission stay free when no SDK is configured?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter adding a default observability surface to an eval dispatch kernel must define the per-outcome event shape, the attribute table (standard vs extension names), how failures differ from results in a machine-readable way, and how the whole plane costs nothing when the telemetry SDK is absent.

## One event per outcome; lazy logger; failure asymmetry
**Path/Symbol:** `pydantic_evals/pydantic_evals/_otel_emit.py` module docstring (:1-15), attribute constants (:39-54), `_get_logger` (:59-66), `emit_otel_events` (:69-102), `_emit_result` (:135-144), `_emit_failure` (:147-165), `_serialize_evaluator_source` (:235-243).
**Signature:** `emit_otel_events(*, results: Sequence[EvaluationResult], failures: Sequence[EvaluatorFailure], target: str, include_baggage: bool = True) -> None`.
**Data Shape:** One OTel `LogRecord` per `EvaluationResult` AND per `EvaluatorFailure`, all sharing `event_name='gen_ai.evaluation.result'`, scope `'pydantic-evals'`. Attribute table: STANDARD semconv — `gen_ai.evaluation.name`, `gen_ai.evaluation.score.value`, `gen_ai.evaluation.score.label`, `gen_ai.evaluation.explanation`, `error.type`; EXTENSIONS placed in `gen_ai.*` on the assumption upstream will land there — `gen_ai.evaluation.target`, `gen_ai.evaluation.evaluator.source`, `gen_ai.evaluation.evaluator.version`.

### Decisive source
```python
def emit_otel_events(*, results, failures, target, include_baggage=True):
    if not results and not failures:
        return                                  # nothing to deliver → no events at all
    baggage_attrs = _baggage_attrs() if include_baggage else None
    for result in results:
        _emit_result(result, target, baggage_attrs)
    for failure in failures:
        _emit_failure(failure, target, baggage_attrs)

def _emit_failure(failure, target, baggage_attrs):
    attrs = _base_attrs(target, failure.name, failure.source, failure.evaluator_version, baggage_attrs)
    # Prefer the actual raising exception class when available; fall back to the
    # generic marker for legacy EvaluatorFailure instances constructed without it.
    attrs[_ATTR_ERROR_TYPE] = failure.error_type or 'pydantic_evals.EvaluatorFailure'
    if failure.error_message:
        attrs[_ATTR_EXPLANATION] = failure.error_message
    _get_logger().emit(LogRecord(event_name=_EVENT_NAME, body=_format_failure_body(failure),
                                 attributes=attrs, severity_number=SeverityNumber.WARN))

def _get_logger():
    global _logger
    if _logger is None:
        _logger = get_logger(_OTEL_SCOPE)       # lazy: test fixtures that replace the
    return _logger                              # global provider work predictably
```

**Flow:** Dispatch calls this unconditionally per evaluator run; with no OTel SDK configured, `get_logger()` returns a proxy and every emit is a cheap no-op — the default surface is free by construction. The logger is acquired lazily on first call (not import time) so provider-swapping test fixtures behave. `evaluator.source` is stored as a JSON STRING (`source.model_dump_json()`) because OTel log attributes are scalar/sequence typed while the spec's `arguments` can be an arbitrary kwargs dict; downstream materialized views JSON-parse the column. `evaluator.version` is written only when not None. Failures get `error.type` (actual exception class preferred, generic marker for legacy instances), optional `explanation`, `SeverityNumber.WARN`, and NO score attributes.
**Invariant:** The result-vs-failure discriminator is machine-readable and threefold: presence of `error.type`, WARN severity, and ABSENCE of both score attributes — a query must not need the body string to tell them apart. Absence (not an empty value) signals an unversioned evaluator. Extension attributes live in the same `gen_ai.*` namespace deliberately, with a comment binding them to downstream queries so renames happen atomically.
**Probe:** `tests/evals/test_otel_emit.py::test_emits_event_with_parent_span` (:49-80) pins event name, body `'evaluation: Correctness=True'`, full attribute set, and trace/span ids from the parent reference; `test_failure_emits_error_type_and_no_score` (:119-141) pins the generic marker + WARN + no score attrs; `test_empty_results_and_failures_emits_nothing` (:185-192) pins the early return; `test_failure_error_type_surfaces_actual_exception_class` (:195-211) pins `error.type == 'ValueError'`; `test_no_version_attribute_when_none` (:155-164) pins absence-not-emptiness.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "emit_otel_events _emit_failure error.type SeverityNumber.WARN gen_ai.evaluation.result", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of _otel_emit.py whole (243L) at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt the whole contract: one event per outcome under one stable event name; standard-vs-extension attribute split with extensions namespaced where upstream will likely land them; failure discrimination via error.type + severity + score-absence rather than body parsing; lazy logger acquisition; and the empty-inputs early return. Adapt the JSON-string spec serialization to your host's scalar-only attribute constraint. Omit the logfire-specific body rendering niceties unless your viewer shows inline bodies. Coverage caveat: none — _otel_emit.py read whole this pass.
