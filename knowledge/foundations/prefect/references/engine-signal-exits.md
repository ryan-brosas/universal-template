<!-- capsule-v2 -->

# Engine-signal process exits — When must a supervised child exit 0 versus re-raise?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** What exit-code contract keeps an orchestrator from misreading controlled termination as a crash?

## Abort/Pause/intent/outcome all exit(0); raw signals propagate

**Path/Symbol:** `src/prefect/engine.py:handle_engine_signals (44-105)`; module entrypoint `__main__` block (107-155) wiring load→run→`_drive_run_flow_result`; deferred-consumer helper `_drive_run_flow_result (24-41)`.

**Signature:** `handle_engine_signals(flow_run_id: UUID | None = None)` contextmanager wrapping the whole subprocess body.

**Data Shape:** Evidence consulted at except-time: `get_intent()` (committed control intent) and `engine_outcome_is_handled()` (engine already concluded the attempt via receipt).

### Decisive source
```python
except TerminationSignal:
    intent = get_intent()
    if intent is not None or engine_outcome_is_handled():
        ...
        if intent is not None:
            clear_intent()
        exit(0)
    raise
except Exception:
    if engine_outcome_is_handled():
        exit(0)
    ... exit(1)
except BaseException:
    if engine_outcome_is_handled():
        exit(0)
    # Let the exit code be determined by the base exception type
    raise
```

**Flow:** orchestrator-aborted (Abort) or paused (Pause) runs log info + `exit(0)` — NOT errors · TerminationSignal with intent or handled-outcome ⇒ clean 0 (intent consumed exactly once via clear_intent) · RAW TerminationSignal with neither evidence ⇒ RE-RAISE (crash-style, nonzero by signal semantics) · ordinary Exception after a handled outcome ⇒ 0, otherwise log + `exit(1)` · BaseException ⇒ 0 only if outcome handled, else propagate preserving interpreter exit code. Entrypoint note: async flows run on a MAIN-thread loop in the child so the SIGTERM bridge can fire ("moves execution off the main thread prevents graceful cancellation from ever becoming ready").

**Invariant:** (1) A zero exit for owned terminations is load-bearing: supervisors treat nonzero as infrastructure failure and may requeue/reschedule incorrectly. (2) Raw external kills must PROPAGATE — exiting 0 there would hide genuine SIGKILL-class incidents. (3) Intent clearing happens exactly once at consumption; double-clear races are avoided by consuming inside the same lock-free window the reader thread committed under.

**Probe:** `grep -c 'exit(0)' src/prefect/engine.py` → 5; `grep -cF 'engine_outcome_is_handled():' src/prefect/engine.py` → 3. Direct tests: `tests/test_flow_engine.py:2586 test_intent_exits_zero_on_termination_signal` (parametrized ×3 intents), `:2601 test_raw_termination_signal_still_bubbles_without_intent`, `:2611 test_handled_engine_outcome_exits_zero_on_exception`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "handle_engine_signals abort pause termination", "limit": 4}'
```

## Verdict
Adopt the exit-code contract table for any supervised worker process; adapt signal plumbing; omit Prefect's RunMetrics/migration shims around it.
