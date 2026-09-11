<!-- capsule-v2 -->
# CodeMode sandbox-limit markers: table-driven exhaustion classification with test-enforced coverage

## Source / Question
`pydantic_ai_harness/code_mode/_toolset.py` (drift +299L) @ `main@f971198` — Monty reports resource exhaustion as untyped error MESSAGES ("time limit exceeded", "memory limit exceeded"). How do you map those to your typed limit set without a per-limit if-chain rotting when either side adds entries?

## Path / Symbol
`code_mode/_toolset.py` — `_SANDBOX_LIMIT_MARKERS: dict[str, str]` mapping limit-name→Monty phrasing, `_exhausted_sandbox_limit(error)` table scan, `_is_duration_exhausted` (strict twin for restart guidance), `_RETRY_VALUE_PREVIEW_CHARS=120`/`_RETRY_PREVIEW_ITEMS=5`/`_RETRY_SUMMARY_MAX_CHARS=2000` bounds for nested-call summaries, `_in_temporal_workflow` runtime_checkable-protocol detection avoiding the optional extra import.

## Signature
```python
_SANDBOX_LIMIT_MARKERS = {
    'max_duration_secs': 'time limit exceeded',
    'max_memory':        'memory limit exceeded',
}
def _exhausted_sandbox_limit(error: MontyRuntimeError) -> str | None:
    message = error.display(format='msg')
    for limit, marker in _SANDBOX_LIMIT_MARKERS.items():
        if marker in message: return limit
    return None
```

## Data Shape
Nested-call summary appended to budget-exhaustion retries uses SEPARATE small bounds because "Monty caps printed output at 10 MiB by raising, which suits a stream the model asked for but not a summary the host adds to an error — the summary exists to identify calls, not to redeliver their payloads."

### Decisive source
Table rationale (:docstring): "Monty offers no typed marker for either, so its phrasing is load-bearing here and nowhere else. `test_every_resource_limit_reports_started_calls_when_exhausted` exhausts each option the type declares and checks the summary survives, so a limit added without an entry here fails there rather than silently losing its summary, and a Monty reword fails it rather than quietly disabling recognition." Deliberate asymmetry between classifiers: `_exhausted_sandbox_limit` "gates the started-call summary, so it deliberately errs toward inclusion and matches on Monty's wording alone. A nested tool that fails with one of these phrases in its own message is misread, and that costs nothing: the summary only states which calls really started… The restart guidance cannot afford the same looseness and uses `_is_duration_exhausted` instead." Temporal detection walks `ctx.capabilities` MROs for `pydantic_ai.durable_exec.temporal` modules + duck-typed `in_durable_context`, dodging the optional import.

**Flow:** snippet exceeds limit → Monty raises phrased error → table classifies → retry text gains bounded started-calls summary → restart guidance only on the STRICT duration match.
**Invariant:** adding a `CodeModeResourceLimits` field without a marker row fails CI (not silence); loose classifier feeds diagnostics only, strict one gates behavior.

## Probe (direct test)
`tests/code_mode/test_code_mode.py::test_every_resource_limit_reports_started_calls_when_exhausted` (declared-limits × marker-table completeness pin), exhaustion-matrix tests for duration/memory summaries; suite green at HEAD within the drift battery.

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern '_SANDBOX_LIMIT_MARKERS _exhausted_sandbox_limit'
```

## Verdict
**Adopt** marker tables ONLY with the exhaust-every-declared-option test that makes omissions loud. **Adopt** loose-for-diagnostics/strict-for-behavior classifier split. **Adapt** markers to your sandbox vendor's wording.
