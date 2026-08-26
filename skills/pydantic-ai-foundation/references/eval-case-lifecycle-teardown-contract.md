<!-- capsule-v2 -->
# Case lifecycle teardown contract — setup failures become case failures, teardown always runs, and its OWN exceptions abort the run. Why the asymmetry?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What is the exact ordering and failure semantics of per-case setup / prepare_context / teardown hooks?

## Hook lattice with deliberately propagating teardown
**Path/Symbol:** `pydantic_evals/pydantic_evals/lifecycle.py:CaseLifecycle` (:25-113, whole file); dispatch in `dataset.py:_run_task_and_evaluators` (:1083-1219, esp. :1135-1216).
**Signature:** `setup() -> None`; `prepare_context(ctx) -> ctx`; `teardown(result: ReportCase | ReportCaseFailure | None) -> None`; instance built per case via `type[CaseLifecycle] | Callable[[Case], CaseLifecycle] | None` (partial-config supported).
**Data Shape:** One instance per case (`lifecycle(case)`), state isolated per row; `self.case` exposed read-only.

### Decisive source
```python
# dataset.py — inside `with logfire_span('case: ...')`
if lc is not None: await lc.setup()                    # exception → ReportCaseFailure (caught below)
scoring_context = await _run_task(task, case, retry_task)
if lc is not None: scoring_context = await lc.prepare_context(scoring_context)
... evaluators ...
except Exception as exc:
    result = ReportCaseFailure(..., error_stacktrace=traceback.format_exc(), ...)
finally:
    # Teardown exceptions are intentionally not caught here — they propagate
    if lc is not None:
        await lc.teardown(result)                       # ReportCase OR ReportCaseFailure OR None
...
result.total_duration = _get_span_duration(case_span, time.time() - t0)   # AFTER finally
```

**Flow:** setup → task → prepare_context → evaluator fan-out → ReportCase/ReportCaseFailure → finally-teardown → span-based total_duration rewrite. Setup/prepare_context exceptions land in the SAME except that catches task failures, so they produce a ReportCaseFailure AND teardown still receives it. Teardown exceptions are never caught — they surface as a TaskGroup ExceptionGroup and abort the whole evaluation. total_duration is recomputed from the span after teardown, so mutations to it inside teardown don't stick.
**Invariant:** Teardown is guaranteed-once with the final result object (or None on cancellation), but its own errors are fatal BY CONTRACT (documented in-source: "If your teardown may raise… handle exceptions within your teardown()"). The duration rewrite makes the span authoritative for timing over wall-clock accumulation.
**Probe:** `tests/evals/test_dataset.py::test_lifecycle_setup_failure_produces_case_failure_and_calls_teardown` (:2425-2451); `test_lifecycle_teardown_on_task_failure` (:2291-2320) asserts teardown saw BOTH ReportCase and ReportCaseFailure types; `test_lifecycle_teardown_exception_propagates` (:2408-2422) matches `ExceptionGroup.*'unhandled errors in a TaskGroup'`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "CaseLifecycle teardown prepare_context", limit: 8 });
```
Live check this pass: search_graph resolved lifecycle module map + test classes; lifecycle.py read whole; coverage clean.

## Verdict
Adopt the hook lattice and the propagate-by-default teardown rule. Adapt hook names/nouns to your host's vocabulary; keep the guaranteed-once-with-result guarantee and post-teardown timing authority.
