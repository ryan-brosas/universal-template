<!-- capsule-v2 -->

# Termination-intent dispatch — When SIGTERM arrives, who decides whether this is cancel, crash, or someone else's problem?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** How does the engine distinguish a runner-requested cancellation from a raw external kill, and which next-states does it deliberately NOT propose?

## Intent read at exception time, not signal-handler time

**Path/Symbol:** `src/prefect/flow_engine.py:_termination_intent (193-208)`; dispatch inside both `initialize_run` blocks (sync `1211-1231`, async `1911-1969`); supervisor-owned set `_SUPERVISOR_OWNED_INTENTS (:214)`.

**Signature:** `_termination_intent() -> Intent | None`; intents today: `"cancel" | "reschedule" | "relinquish"`.

**Data Shape:** The single source of truth is the control listener's module-global committed under a lock (`prefect._internal.control_listener.get_intent()`), written by the reader thread when the supervisor sends a one-byte intent over the loopback channel. Reading it at EXCEPTION-HANDLING time avoids ContextVar token-reset races and works uniformly for nested subflows in the same process.

### Decisive source
```python
except TerminationSignal as exc:
    self.cancel_all_tasks()
    intent = _termination_intent()
    if intent == "cancel":
        self.handle_cancellation(exc)
    elif intent is None:
        self.handle_crash(exc)
    elif intent not in _SUPERVISOR_OWNED_INTENTS:
        # Defensive: ... Treat as crash so the flow run still reaches a
        # terminal state rather than silently hanging.
        self.logger.error("Unhandled termination intent %r; treating as crash...", intent)
        self.handle_crash(exc)
    raise
```

**Flow:** TerminationSignal raised by the captured SIGTERM bridge → cancel all child tasks first → look up committed intent → `cancel` drives Cancelling→Cancelled via `handle_cancellation` → `None` means nobody asked us: `handle_crash` (Crashed state, force=True) → unknown intent logs loudly and degrades to crash (never hang) → `reschedule`/`relinquish`: propose NOTHING and re-raise — the supervisor owns the run's next state. In ASYNC engines there is a second entry point: a runtime `asyncio.CancelledError` carrying an intent is converted (`raise TerminationSignal(SIGTERM) from exc`) so supervisor-driven kills that surface as cancellation get the same dispatch (:1945-1969).

**Invariant:** (1) An intent means SOMEONE ELSE owns the next state — proposing your own terminal state would fight the supervisor's orchestration; only the no-intent case proposes Crashed. (2) Extending `Intent` REQUIRES extending this dispatch (docstring says so); the defensive branch exists because forgetting it must degrade to a terminal state, not a hung run. (3) `cancel_all_tasks()` runs before any branch. (4) After handling, the signal is always re-raised — handling records state, swallowing would corrupt the caller's exit path.

**Probe:** `grep -c '_SUPERVISOR_OWNED_INTENTS' src/prefect/flow_engine.py` → 4. Direct tests: `tests/test_flow_engine.py:2586 TestHandleEngineSignals.test_intent_exits_zero_on_termination_signal` (parametrized cancel/reschedule/relinquish → SystemExit code 0, intent cleared once) and `tests/test_flow_engine.py:2491 test_async_runtime_cancellation_with_control_intent_routes_to_handle_cancellation` (CancelledError + intent="cancel" awaits handle_cancellation, never handle_crash, raises TerminationSignal with CancelledError as __cause__).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "handle_cancellation termination intent", "limit": 4}'
```

## Verdict
Adopt the intent-table dispatch with a defensive fallthrough-to-terminal for unknown intents whenever a supervised process receives external kill requests; adapt the transport (Prefect: loopback socket + ack byte) to your supervisor protocol; omit the version-one/version-two negotiation handshake details.
