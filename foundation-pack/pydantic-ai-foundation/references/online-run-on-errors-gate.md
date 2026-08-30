<!-- capsule-v2 -->
# Online-eval run_on_errors — how do you evaluate FAILURE modes (raised exceptions) without masking the original error?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter scoring production failure modes (exception types, tool errors) must decide which evaluators see a raised exception, what the evaluator's `output` becomes, and how the wrapper guarantees the original exception still reaches the caller.

## Opt-in gate with exception-as-output, re-raise after fire-and-forget
**Path/Symbol:** `pydantic_evals/pydantic_evals/online.py:_dispatch_on_error` (:612-645), `_wrap_async` except (:695-697), `_wrap_sync` except (:770-772); `pydantic_evals/pydantic_evals/online_capability.py:OnlineEvaluation.wrap_run` except (:152-166).
**Signature:** `_dispatch_on_error(exc, sampled, inputs, get_eval_context_kwargs, span, target, config) -> None`; `OnlineEvaluator.run_on_errors: bool = False`.
**Data Shape:** The raised exception object itself becomes `EvaluatorContext.output` (`expected_output=None`, inputs preserved); only evaluators with `run_on_errors=True` are dispatched; dispatch is fire-and-forget on the same loop-vs-thread ladder as the success path.

### Decisive source
```python
# _wrap_async / _wrap_sync — identical shape:
with _open_call_span(...) as span:
    try:
        with _task_run.run_task() as get_eval_context_kwargs:
            result = await func(*args, **kwargs)      # or func(...) for sync
    except Exception as e:
        _dispatch_on_error(e, sampled, inputs, get_eval_context_kwargs, span, target, config)
        raise                                          # original exception ALWAYS propagates

def _dispatch_on_error(exc, sampled, inputs, get_eval_context_kwargs, span, target, config):
    error_evaluators = [ev for ev in sampled if ev.run_on_errors]
    if not error_evaluators or get_eval_context_kwargs is None:
        return
    context = EvaluatorContext(name=None, inputs=inputs, output=exc, expected_output=None,
                               metadata=..., **get_eval_context_kwargs())
    coro = _online_internal.dispatch_evaluators(error_evaluators, context, span_reference, target, config)
    try: asyncio.get_running_loop()
    except RuntimeError: _online_internal.dispatch_in_background_thread(coro)
    else:                _online_internal.dispatch_async(coro)

# capability twin adds one guard:
except Exception as e:
    error_evaluators = [ev for ev in sampled if ev.run_on_errors]
    if error_evaluators and get_eval_context_kwargs is not None:   # pre-init None for pyright flow
        ...
        raise
```

**Flow:** wrapped call raises → filter sampled evaluators to `run_on_errors=True` → none opted in (or context kwargs unavailable) → return silently → else build a context whose `output` IS the exception, dispatch fire-and-forget (sync path picks caller-loop task vs background thread exactly like the success path) → wrapper RE-RAISES the original exception. Default (`run_on_errors=False`) means a raising call dispatches NOTHING — only successful outputs reach evaluators unless opted in.
**Invariant:** Error-path evaluation must never mask, swallow, or reorder the original exception — dispatch happens before `raise`, but dispatch is non-blocking and its own failures route to the on_error ladder, not to the caller. The gate is per-evaluator, so a cheap heuristic can score failures while an expensive judge stays success-only. A porter who awaits the error dispatch before re-raising changes latency semantics; one who catches-and-logs instead of raising breaks every upstream handler.
**Probe:** `tests/evals/test_online.py::test_evaluate_decorator_async_default_skips_dispatch_on_exception` (:388-401) pins default-skip; `test_evaluate_decorator_async_run_on_errors_dispatches` (:405-424) pins `isinstance(ctx.output, RuntimeError)` + `str(ctx.output) == 'boom: 42'` + inputs intact; `test_evaluate_decorator_async_run_on_errors_filters_evaluators` (:428-447) pins opt-in filtering; `test_evaluate_decorator_sync_run_on_errors_no_event_loop` (:471-494) pins the thread branch on the error path; capability twins at `tests/evals/test_online_capability.py` :287-358.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_dispatch_on_error run_on_errors EvaluatorContext output exception", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session; anchors confirmed by direct read of online.py :612-645/:695-697/:770-772 and online_capability.py :152-166 at pin `a5b5fb7a`.

## Verdict
Adopt the per-evaluator boolean gate with exception-as-output and the dispatch-then-re-raise ordering — it is the minimal contract that makes failure-mode scoring safe. Adopt the shared `_dispatch_on_error` helper so sync/async wrappers cannot drift apart. Adapt the capability's `get_eval_context_kwargs is not None` guard to your host's flow-analysis needs. Omit nothing else — the plane is small by design. Coverage caveat: none — files read whole this pass.
