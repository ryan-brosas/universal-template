<!-- capsule-v2 -->
# run_evaluator failure envelope — why does a crashing evaluator become report data instead of an exception?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When porting an eval harness, how do you run one evaluator so that neither invalid output types nor raised exceptions abort the whole experiment?

## try/except → EvaluationResult[] | EvaluatorFailure funnel
**Path/Symbol:** `pydantic_evals/pydantic_evals/evaluators/_run_evaluator.py:run_evaluator` (:35-107); mapping helper `_convert_to_mapping` (:117-131); always-revalidating adapter (:110-114).
**Signature:** `async def run_evaluator(evaluator, ctx, retry: RetryConfig | None = None) -> list[EvaluationResult] | EvaluatorFailure`.
**Data Shape:** success = list of `EvaluationResult{name, value, reason, source: EvaluatorSpec, evaluator_version}`; failure = `EvaluatorFailure{name, error_message='Type: msg', error_stacktrace, source, error_type, evaluator_version}`.

### Decisive source
```python
with logfire_span('Calling evaluator: {evaluator_name}', evaluator_name=evaluator_name,
                  _span_name='evaluator: {evaluator_name}'):
    raw_results = await evaluate(ctx)
    try:
        results = _EVALUATOR_OUTPUT_ADAPTER.validate_python(raw_results)
    except ValidationError as e:
        raise ValueError(f'{evaluator!r}.evaluate returned a value of an invalid type: {raw_results!r}.') from e
    results = _convert_to_mapping(results, scalar_name=evaluator_name)
    ...
except Exception as e:
    return EvaluatorFailure(name=evaluator_name, error_message=f'{type(e).__name__}: {e}',
                            error_stacktrace=traceback.format_exc(), source=source,
                            error_type=type(e).__name__, evaluator_version=evaluator_version)
```
```python
_EVALUATOR_OUTPUT_ADAPTER = TypeAdapter[EvaluatorOutput](EvaluatorOutput, config=ConfigDict(revalidate_instances='always'))
```

**Flow:** optional tenacity wrap of `evaluate_async` when `retry` given → name/version/source captured BEFORE execution → span-wrapped execution → strict validation (scalar / `EvaluationReason` / mapping thereof; `float` must be finite via `allow_inf_nan=False`) → non-mapping outputs keyed by the evaluator's default name (`_convert_to_mapping`) → one `EvaluationResult` per entry → ANY exception inside the `try` (including the ValueError re-raise from bad output types and tenacity's exhausted retries) returns an `EvaluatorFailure` instead of propagating.
**Invariant:** Two traps for a porter. (1) The adapter is built with `revalidate_instances='always'` — the comment explains pydantic would otherwise TRUST existing `EvaluationReason` instances and skip validating `value` against the finite-float constraint; reusing a plain TypeAdapter silently admits NaN scores. (2) `_span_name` is pinned separately from the user-visible template because existing logfire queries filter on `'evaluator: {name}'` — renaming the span breaks downstream dashboards even when the message changes safely.
**Probe:** `tests/evals/test_evaluator_base.py::test_run_evaluator` (:308-388) — sync bool / reason-carrying / multi-key dict / async evaluators each produce the snapshotted result rows with `source` spec embedded.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-pydantic-ai","query":"run_evaluator","limit":3,"detail":"compact"}'
```
Live check this pass: rank-1 line-exact `_run_evaluator.py 35-107`, plus direct test at rank-2.

## Verdict
Adopt the failure-as-data envelope and the always-revalidate adapter config — both are what let one broken evaluator degrade to a red row instead of killing a 500-case run. Adapt the RetryConfig wiring to your host's retry primitive. Omit the logfire-specific span kwargs only if your host has no span-name-stable consumers (then keep the single-template form). Direct test executed GREEN at pin.
