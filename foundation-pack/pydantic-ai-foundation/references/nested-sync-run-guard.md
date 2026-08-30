<!-- capsule-v2 -->
# Nested sync-run guard — how do you fail fast when a sync agent run is started from inside a run's callback?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you detect and reject nested sync event-loop entry before it deadlocks?

## nested-sync-run-guard
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_utils.py:` `_in_sync_callback` ContextVar (:75), `check_no_nested_sync_run` (:82–97), flag set/reset wrapper in `run_in_executor` (:183–192); consumer: every `Agent.run_sync`/`run_stream_sync` entry calls the check.
**Signature:** `check_no_nested_sync_run() -> None` raising `UserError` when flagged; wrapper sets `_in_sync_callback=True` around ANY callback dispatched via `run_in_executor` — whether it lands on a worker thread or runs inline under `disable_threads`.
**Data Shape:** ContextVar default False; scoped strictly to callback execution (`try/finally reset`).

### Decisive source
```python
# _utils.py docstring (load-bearing):
# Sync tools, output functions, and similar callbacks are dispatched through run_in_executor,
# which flags the callback's context — whether the callback runs on a worker thread or inline
# under disable_threads. On a worker thread, a nested sync run starts a second event loop that
# can deadlock against an async resource bound to the parent run's loop; inline, it would drive
# the already-running loop and fail anyway. Either way we fail fast with guidance instead.

if _in_sync_callback.get():
    raise UserError(
        '`Agent.run_sync()` and `Agent.run_stream_sync()` cannot be used inside a synchronous '
        'tool, output function, or other function called during an agent run, as they can '
        'deadlock the run. Make the function `async def` and use `await agent.run(...)` instead.')
```

**Flow:** agent run dispatches a sync tool → `run_in_executor` flips the ContextVar for the callback's context (worker thread gets a COPIED context, so the flag rides along) → callback tries `inner_agent.run_sync(...)` → guard raises UserError with the fix in the message → regular application code (flag False) still runs sync agents freely.
**Invariant:** three rules:
1. Flag at DISPATCH time, not detection time — you cannot reliably introspect "am I inside a run" later; the dispatcher knows.
2. ContextVar is the right carrier because worker threads inherit copied contexts AND inline disable_threads execution shares the caller's context — one mechanism covers both dispatch modes.
3. The error message prescribes the exact migration (`async def` + `await agent.run`); a guard without guidance just moves the confusion. Scope check happens BEFORE any loop construction so nothing leaks (verified by the test's post-assert that normal sync runs still work after the raised guard).
**Probe:** `tests/test_nested_sync_agent.py::test_run_sync_from_sync_tool_is_rejected` (:11–29, incl. the scoped-recovery assert) + dbos/prefect twins.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "check_no_nested_sync_run _in_sync_callback run_sync UserError deadlock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dispatch-time ContextVar flagging for any "no re-entry" rule around event loops; adapt message text; omit nothing — the pattern is four lines plus the wrapper.
