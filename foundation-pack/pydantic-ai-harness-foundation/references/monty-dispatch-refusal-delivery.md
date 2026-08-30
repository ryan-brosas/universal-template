<!-- capsule-v2 -->
# Monty dispatch-refusal delivery: fail the call inside the sandbox, never abort the feed

## Source / Question
`pydantic_ai_harness/_monty_exec.py` (MontyExecutor, drift-hardened in #621) @ `main@f971198c` (Codebase Memory `pydantic-ai-harness`) — The host `dispatch` callback can REFUSE a sandbox tool call before building its coroutine (e.g. an exhausted per-snippet nested-call budget). If that refusal raises out of the executor, the whole REPL feed dies and every completed call's result is lost. How do you deliver host-side refusals without discarding work the snippet already paid for?

## Path / Symbol
`_monty_exec.py` — `MontyExecutor` (:82; single-use: per-run state in `_pending`/`_pre_resolved`), parallel-deferred path (`resume({'future': ...})` + eager `asyncio.Task`), sequential-inline path (:155–168), deferred path (:170–187), `_resolve_futures` (:190–209, gather with `return_exceptions=True` + `_wrap_gathered`), `_await_external` (:211+ wraps outcome as `{'return_value': …}` / `{'exception': …}`).

## Signature
```python
# BOTH the sequential-inline and deferred legs wrap refusal identically:
try:
    call = self.dispatch(name, snapshot.kwargs)
except Exception as exc:
    return snapshot.resume({'exception': exc})
return snapshot.resume(await _await_external(call))   # sequential leg only
```

## Data Shape
The refusal is delivered through the SAME settled-result channel as a failure raised INSIDE the dispatched coroutine, so the sandbox sees it at its `await`/call site as an ordinary raisable exception. Nothing was scheduled ⇒ no task to clean up and no further work admitted; calls that already completed keep their recorded results in `nested_returns`, and the snippet can still return them.

### Decisive source
In-source comment (:174–179): "`dispatch` refused the call before building its coroutine (e.g. an exhausted per-snippet budget). Deliver the error at the sandbox call site, the same way a failure raised inside the coroutine is delivered, rather than letting it abort the feed: calls that already completed keep the results the host recorded for them, and the snippet can still return them." Sequential-barrier ordering hazard documented at :157–159: the dispatch coroutine is created only AFTER the pending-parallel barrier because it is not in `_pending` — if it existed there while the barrier awaited and the run was cancelled, `run`'s cleanup would never close it. Direct tests: `tests/code_mode/test_code_mode.py::test_exhausted_budget_preserves_completed_calls` (:558, docstring "A refused call fails inside the sandbox, so work already done is not thrown away") and `test_exhausted_budget_on_sequential_tool_preserves_completed_calls` (:1025, "The budget refusal reaches the sandbox for inline-resolved tools too" — proving BOTH legs).

**Flow:** sandbox invokes external name → executor tries `dispatch(...)` → refusal exception caught BEFORE any coroutine exists → `resume({'exception': exc})` → Monty raises it at the script's call site → script's own try/except or uncaught-budget retry decides what survives.
**Invariant:** host-side policy failures are DATA to the sandbox (settled-result envelope), never executor-level aborts; the three execution modes (parallel/per-call-sequential/global-sequential) each keep their own delivery discipline; a fresh executor per run (state is single-use).

## Probe (direct test)
`tests/code_mode/test_code_mode.py::test_exhausted_budget_preserves_completed_calls` :558, `test_exhausted_budget_on_sequential_tool_preserves_completed_calls` :1025, `test_nested_call_budget_is_reserved_before_dispatch` :519.

## Retrieve
```
codebase-memory-mcp cli search_graph --project pydantic-ai-harness --name-pattern 'MontyExecutor|snapshot.resume|dispatch' --detail ids
```

## Verdict
Adopt whenever guest code calls host functions across a snapshot/resume boundary: classify refusals at the boundary and deliver them as call-site exceptions. Adapt the envelope shape to your VM's settled-result protocol. Omit Monty's specific execution-mode matrix unless porting the whole REPL driver.
