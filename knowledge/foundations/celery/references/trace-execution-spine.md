<!-- capsule-v2 -->
# Trace execution spine — how does one function turn every task outcome into a terminal state without leaking?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** Where does a task's return value / exception become SUCCESS/RETRY/FAILURE/REJECTED/IGNORED, and in what order do callbacks, backend writes, and signals fire?

## build_tracer → trace_task closure
**Path/Symbol:** `celery/app/trace.py:build_tracer` (:344) returning inner `trace_task` (:475-686); installed per-task via `trace_task()` (:689) caching on `task.__trace__`; worker fast path `fast_trace_task` (:757).
**Signature:** `build_tracer(name, task, loader=None, hostname=None, store_errors=True, Info=TraceInfo, eager=False, propagate=False, app=None, monotonic=time.monotonic, ...)`; inner `trace_task(uuid, args, kwargs, request=None)` returning `trace_ok_t(R, I, T, Rstr)`.
**Data Shape:** Returns a named tuple `(retval, Info, runtime, retval_str)` always — never raises for ordinary failures. Reads hot attributes into closure locals before defining the loop body (push/pop request+task stacks, signal receiver lists, `_does_info`, `resultrepr_maxsize`).

### Decisive source
```python
# celery/app/trace.py:560-583 — the exception→state ladder
except Reject as exc:
    I, R = Info(REJECTED, exc), ExceptionInfo(internal=True)
    state, retval = I.state, I.retval
    I.handle_reject(task, task_request)
    traceback_clear(exc)
except Ignore as exc:
    ... I.handle_ignore(task, task_request) ...
except Retry as exc:
    I, R, state, retval = on_error(
        task_request, exc, RETRY, call_errbacks=False)
    traceback_clear(exc)
except Exception as exc:
    I, R, state, retval = on_error(task_request, exc)
    traceback_clear(exc)
except BaseException:
    raise
else:
    # callback tasks must be applied before the result is
    # stored, so that result.children is populated.
    _dispatch_callbacks_and_chain(...)
    task.backend.mark_as_done(uuid, retval, task_request, publish_result)
```

**Flow:** validate kwargs mapping → build `Context(request, called_directly=False)` → optional dedup short-circuit for redeliveries (`deduplicate_successful_tasks and redelivered`: if id in in-process `successful_requests` set OR backend meta says SUCCESS → re-dispatch missing callbacks/chain from stored meta then return early; malformed signature during redispatch becomes `Reject(exc, requeue=True)` relying on broker dead-lettering) → push stacks → prerun signal + `loader.on_task_init` + optional STARTED store → run `fun` (task.run unless custom `__call__`) through the exception ladder above → post-run `after_return` when state not IGNORED → finally: postrun signal, pop stacks, `backend.process_cleanup()` + loader cleanup (exceptions logged not raised) → outermost guard converts any tracer bug into `report_internal_error` (eager re-raises).
**Invariant:** (1) `MemoryError` is NEVER converted to FAILURE — it propagates at every layer. (2) Callbacks/chain dispatch happens BEFORE `mark_as_done` so `result.children` is populated atomically with success; dispatch is non-atomic under Reject-redeliver and may re-send already-sent callbacks — accepted under at-least-once delivery. (3) `Retry` fires NO errbacks (`call_errbacks=False`). (4) Every exception path calls `traceback_clear(exc)` (#8882 memory leak fix). (5) `propagate=True` (eager) re-raises instead of storing.
**Probe:** `t/unit/tasks/test_trace.py::test_trace_retval` pins the tuple contract; `t/unit/tasks/test_tasks.py::test_autoretry_does_not_mutate_shared_base_class_retry_kwargs` (:836-879) exercises the Retry arm of the ladder end-to-end.
**Retrieve:**
```json
{"project":"ext-celery","query":"trace_task build_tracer handle_error_state","limit":5,"detail":"ids"}
```
## Verdict
Adopt the exception-ladder ordering and the callbacks-before-mark_as_done rule wholesale — they are the queue's correctness core. Adapt the dedup redelivery check to your backend's capabilities (requires persistent extended metadata, `result_extended=True`). Omit the CPython-specific `fast_trace_task` slot optimization and `__optimize__` module-import tricks.
