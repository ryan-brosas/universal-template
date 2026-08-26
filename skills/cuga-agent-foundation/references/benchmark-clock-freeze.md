<!-- capsule-v2 -->
# CodeWrapper — monotonic-safe benchmark clock freeze: freeze wall-clock time inside generated code without breaking asyncio

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Reproducible agent evals need the model's generated code to see a frozen task date (like AppWorld/freezegun), but off-the-shelf freezers patch `time.monotonic` too — and asyncio's event loop uses monotonic for every timer, so any `await` in user code hangs until the sandbox timeout. How do you freeze the clock the agent sees without freezing the loop?

## The wrapper
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/common/code_wrapper.py` (`CodeWrapper.build_async_main` :8-97, `wrap_code` :100-182).
**Signature:** `build_async_main(indented_body, fake_datetime=None) -> str`; `wrap_code(code, fake_datetime=None) -> str`.
**Data Shape:** emits `async def _async_main(): <body> return locals()`; under freeze mode an extra indent level wraps the body in try/finally; helper names `_cuga_*` are underscore-prefixed so `filter_new_variables` drops them from captured variables.

### Decisive source
```python
# code_wrapper.py:11-24 — the trade-off documented at the decision site
# Crucially it does NOT touch ``time.monotonic`` / ``perf_counter`` /
# ``sleep``. freezegun freezes those too, and asyncio's event loop uses
# ``monotonic`` for every timer — so freezing it makes any ``await`` inside
# the user code (e.g. the LLM-backed ``find_tools``) hang until the outer
# sandbox timeout. A monotonic-safe hand-rolled patch avoids that ...

# code_wrapper.py:86-96 — what IS frozen + scoped teardown
"    _cuga_tmod.time = lambda: _cuga_epoch\n"
"    _cuga_tmod.localtime = lambda secs=None: (_cuga_tt if secs is None else _cuga_otime[1](secs))\n"
...
"    try:\n{deeper}\n        return locals()\n"
"    finally:\n"
"        _cuga_dtmod.datetime = _cuga_odt\n"
"        _cuga_dtmod.date = _cuga_odate\n"
"        _cuga_tmod.time, ... = _cuga_otime\n"
```

**Flow:** `wrap_code` indents the user body one level, decides auto-print (append `print(last_line)` iff last line isn't print/return/comment/assignment/closing-bracket AND no other print exists — bracket-counting handles multi-line prints), then delegates to `build_async_main`. Freeze mode swaps `datetime.datetime`/`datetime.date` for shim classes (`now/today/utcnow → frozen instant`, everything else delegating to originals), pins `time.time` to the UTC timegm of the naive datetime, and makes `localtime/gmtime/strftime` read the frozen timetuple when called with no argument (explicit-arg calls pass through). Teardown restores every original in `finally` so nothing leaks into cuga's own clock.
**Invariant:** `time.monotonic`, `perf_counter`, and `sleep` are NEVER patched — asyncio correctness over freeze completeness (`isinstance(x, datetime)` is not preserved by the shim; accepted because agent code doesn't depend on it). The freeze exists only in benchmark mode (`fake_datetime` set from ActivityTracker); normal runs emit no patching code at all.

**Probe:** direct tests `executors/tests/test_code_wrapper_freeze.py::test_asyncio_sleep_survives_freeze` (:60) — THE monotonic-safety pin, `::test_freezes_datetime_date_and_time_module` (:73), `::test_freeze_is_torn_down_no_host_leak` (:88), `::test_helper_vars_are_underscore_prefixed_for_filtering` (:96), `::test_no_fake_datetime_injects_no_freeze` (:104); auto-print behavior pinned by `test_code_executor.py::test_expression_auto_print` (:539).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "CodeWrapper build_async_main wrap_code fake_datetime auto print", limit: 10 });
```

## Verdict
Adopt hand-rolled monotonic-safe clock freezing scoped by try/finally inside the generated function (never process-global freezer libraries around async code). Adapt which time sources you freeze to your eval harness. Omit auto-print inference if your execution contract requires explicit prints.
