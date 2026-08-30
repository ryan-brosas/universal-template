<!-- capsule-v2 -->
# Listener cycle re-entry — how does the same listener method run again in cyclic flows without breaking resume-skip semantics?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** When a listener is already in `_completed_methods`, what decides "skip because resuming" vs "re-run because cycle iteration"?

## Completed-set discard + full OR-ledger reset
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`Flow._execute_single_listener` :3217–3321, start twin `_execute_start_method` :2722–2735; call-count guard :588–591, :3246–3254).
**Signature:** `_execute_single_listener(self, listener_name: FlowMethodName, result: Any, triggering_event_id: str | None = None) -> tuple[Any, str | None]`.
**Data Shape:** `_completed_methods: set[FlowMethodName]`; `_method_call_counts: dict[FlowMethodName, int]`; `max_method_calls: int = Field(default=100)`.

### Decisive source
```python
count = self._method_call_counts.get(listener_name, 0) + 1
if count > self.max_method_calls:
    raise RecursionError(
        f"Method '{listener_name}' has been called {self.max_method_calls} times in "
        f"this flow execution, which indicates an infinite loop. "
        ...
    )
...
if listener_name in self._completed_methods:
    if self._is_execution_resuming:
        # During resumption, skip execution but continue listeners
        await self._execute_listeners(listener_name, None)
        ...
        return (None, None)
    # For cyclic flows, clear from completed to allow re-execution
    self._completed_methods.discard(listener_name)
    # Clear ALL fired OR listeners so they can fire again in the new cycle.
    # This mirrors what _execute_start_method does for start-method cycles.
    self._clear_or_listeners()
```

**Flow:** per-listener call counter increments first and raises `RecursionError` past `max_method_calls` (the loop breaker; error text names the `@listen` label matching its own method name as the common cause) → already-completed listener: resuming ⇒ skip body but STILL walk downstream listeners with `None` result; cycling ⇒ discard from completed AND clear every fired OR entry → execute normally.
**Invariant:** Resume-skip wins over cycle re-entry while `_is_execution_resuming` is True — the flag is cleared only after initial execution completes (:2411–2412) or explicitly flipped around cyclic start re-runs. Discarding ONE listener is insufficient on cycles: downstream `or_()` listeners would stay suppressed across iterations, hence the wholesale `_clear_or_listeners()`. The error-logger stamps exceptions with `_flow_listener_logged` so one failure logs once despite recursive re-raise.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow.py::test_cyclic_flow" "lib/crewai/tests/test_flow_resumability_regression.py::test_hitl_resumption_skips_completed_listeners" "lib/crewai/tests/test_flow.py::test_cyclic_flow_or_listeners_fire_every_iteration" -q` (expect 3 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_execute_single_listener completed methods cyclic discard max_method_calls recursion", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tri-state gate (call cap → resume-skip-with-downstream-walk → cycle-discard-plus-ledger-reset); adapt `max_method_calls` default to your workload; omit the `_flow_listener_logged` stamp if your logging layer dedupes already.
