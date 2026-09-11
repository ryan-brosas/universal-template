<!-- capsule-v2 -->

# Attempt-outcome receipts — How does an engine prove to its supervisor that a terminal state was committed?

**Path/Symbol:** `src/prefect/flow_engine.py:BaseFlowRunEngine._capture_state_report (461-473)`, `_report_attempt_conclusion (475-480)`; receipt type `src/prefect/_internal/attempt_control.py:EngineOutcomeReceipt`; session protocol docstring in `src/prefect/_internal/control_listener.py:1-45`.

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** What handshake distinguishes "engine wrote the terminal state" from "process died before writing"?

**Signature:** `EngineOutcomeReceipt.state_reported(state_id, state_type, state_name)` / `.orchestration_aborted()`; `report_engine_outcome(receipt)` sends it over the control channel.

**Data Shape:** `_attempt_conclusion: EngineOutcomeReceipt | None` latched on EVERY set_state — final or paused states WITH id+name produce a receipt, anything else resets to None. Abort carries `orchestration_aborted()` instead of a state report.

### Decisive source
```python
def _report_attempt_conclusion(self) -> None:
    if (
        not self._started_with_in_process_parent_flow_run_context
        and self._attempt_conclusion is not None
    ):
        report_engine_outcome(self._attempt_conclusion)

# initialize_run finally:
finally:
    self._report_attempt_conclusion()
```

**Flow:** every set_state refreshes/clears the pending receipt → run body exits through initialize_run's finally → if this process is a supervised top-level run (no in-process parent context) and a terminal/paused state was reached, the receipt goes to the supervisor which ACKs over the loopback channel ("Keep the control session open until the terminal outcome receipt has been acknowledged") → supervisor's `engine_outcome_is_handled()` then routes exits (see engine-signal-exits). Same-process subflows skip reporting — their parent engine observes outcomes directly.

**Invariant:** (1) The receipt reflects the LATEST set_state, so a crash AFTER a terminal write doesn't misreport; conversely clearing on non-final states prevents stale receipts claiming completion after a later deferral. (2) Reporting is skipped for nested same-process engines because two writers would double-report one attempt.

**Probe:** `grep -cF 'report_engine_outcome(self._attempt_conclusion)' src/prefect/flow_engine.py` → 1. Direct tests: heartbeat/receipt behavior exercised via `tests/test_flow_engine.py:2584+ TestHandleEngineSignals` outcome branches and control-listener protocol tests under `tests/` (negotiation/ack coverage in `src/prefect/_internal/control_listener.py` module contract).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "_capture_state_report EngineOutcomeReceipt", "limit": 3}'
```

## Verdict
Adopt latest-writer-wins receipts + ack-before-exit for supervisor/worker trust; adapt wire format; omit version-one byte protocol details.
