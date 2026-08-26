<!-- capsule-v2 -->

# Crash-state taxonomy — Which BaseExceptions become Crashed, and what message does each class carry?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** How do you classify out-of-user-code failures into a single terminal state with actionable messages?

## exception_to_crashed_state ladder

**Path/Symbol:** `src/prefect/states.py:exception_to_crashed_state (203-252)`; sync variant `src/prefect/_internal/states.py:exception_to_crashed_state_sync`; consumed by flow `handle_crash` (`flow_engine.py:892-899`, async shielded `1590-1601`) and task engines.

**Signature:** `exception_to_crashed_state(exc: BaseException, result_store=None) -> State`.

**Data Shape:** Message selected by isinstance ladder over the runtime cancellation class (`anyio.get_cancelled_exc_class()`), KeyboardInterrupt, TerminationSignal, SystemExit, httpx.TimeoutException/ConnectError, else generic. Optional result_store stores the exception as a result record under a fresh `uuid4().hex` key; otherwise the exception rides as state data for LOCAL inspection only.

### Decisive source
```python
if isinstance(exc, anyio.get_cancelled_exc_class()):
    state_message = "Execution was cancelled by the runtime environment."
elif isinstance(exc, KeyboardInterrupt):
    state_message = "Execution was aborted by an interrupt signal."
elif isinstance(exc, TerminationSignal):
    state_message = "Execution was aborted by a termination signal."
elif isinstance(exc, SystemExit):
    state_message = "Execution was aborted by Python system exit call."
elif isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
    try:
        request: httpx.Request = exc.request
    except RuntimeError:
        state_message = ("Request failed while attempting to contact the server:" ...)
    else:
        state_message = f"Request to {request.url} failed: ..."
```

**Flow:** engine catches BaseException outside user code → this ladder picks a human message → Crashed state built with that message (+ optionally stored exception) → proposed with force=True. The flow-engine async path wraps in `CancelScope(shield=True)` so the Crashed write survives the cancellation in flight; the sync path relies on run_coro_as_sync. Note the ladder checks anyio's cancelled-exc class FIRST — porting with `asyncio.CancelledError` hard-coded breaks under trio-backed anyio.

**Invariant:** (1) Crash ≠ Failed: crashes mean PREFECT-side interruption, so retries never apply and hooks differ (on_crashed). (2) The `exc.request` access is guarded by RuntimeError because httpx exceptions constructed without a request raise on attribute access — a naive f-string of exc.request crashes the crash handler itself. (3) Without a result store, the attached exception is explicitly documented as unavailable when retrieved from the API.

**Probe:** `grep -cF '"Execution was aborted by a termination signal."' src/prefect/states.py` → 1. Direct tests: `tests/test_states.py` parametrized raise-path suite (:56-131 covers Failed/Crashed/Cancelled exception extraction incl. base exceptions); flow-level crash propagation `tests/test_flow_engine.py:~2460` (pre-execution error ⇒ flow_run.state.is_crashed()).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "exception_to_crashed_state KeyboardInterrupt SystemExit", "limit": 3}'
```

## Verdict
Adopt the ladder + guarded-request pattern when converting infra failures to terminal states; adapt message wording/state names; omit the result-record storage branch if you always have a store.
