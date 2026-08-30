<!-- capsule-v2 -->
# Router dispatch loop — how do router outcomes chain into further routers and eventually reach listeners and conditional starts?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What is the correct order for draining cascaded routers, passing payloads, and re-triggering conditional starts?

## Sequential router drain, parallel listener wave
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`Flow._execute_listeners` :3048–3179; start-side router handling `_execute_start_method` :2722–2756).
**Signature:** `_execute_listeners(self, trigger_method: FlowMethodName, result: Any, triggering_event_id: str | None = None) -> None`.
**Data Shape:** `router_results: list[FlowMethodName]` (all emitted outcome events in drain order); `router_result_payloads: dict[str, Any]`; `router_result_to_feedback: dict[str, Any]` (outcome → `HumanFeedbackResult`).

### Decisive source
```python
while True:
    routers_triggered = self._find_triggered_methods(
        current_trigger, router_only=True
    )
    if not routers_triggered:
        break
    for router_name in routers_triggered:
        # For routers triggered by a router outcome, pass the HumanFeedbackResult
        router_input = router_result_to_feedback.get(
            str(current_trigger), current_result
        )
        ...
        if router_result is None:
            current_trigger = FlowMethodName("")
            continue
        current_trigger = router_result_event

all_triggers = [trigger_method, *router_results]
```
```python
# conditional-start re-entry after a router outcome
if current_trigger in router_results:
    for method_name in self._start_method_names():
        if self._start_condition_triggered_by(method_name, current_trigger):
            if method_name in self._completed_methods:
                was_resuming = self._is_execution_resuming
                self._is_execution_resuming = False
                await self._execute_start_method(method_name)
                self._is_execution_resuming = was_resuming
```

**Flow:** routers triggered by the current event run SEQUENTIALLY until none fire → each router's return value becomes the next event name (Enum members unwrapped via `.value`, falsy/None outcome ends that branch with empty-string trigger) → listeners for ALL accumulated triggers then run in PARALLEL → router outcomes additionally test conditional `@start("label")` methods, temporarily clearing the resumption flag so completed starts re-execute in cycles.
**Invariant:** Routers are flow-control and must stay sequential (order determines which branch wins); listeners are data-flow and may be parallel. A router returning None/falsy emits NO event — it terminates its arm silently rather than erroring. Human-feedback outcomes ride `router_result_to_feedback` so downstream routers receive the structured review result, not the bare label string.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow.py::test_router_cascade_chain" "lib/crewai/tests/test_flow.py::test_multiple_routers_from_same_trigger" "lib/crewai/tests/test_flow.py::test_start_runtime_uses_flow_definition_without_legacy_start_metadata" -q` (expect 3 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_execute_listeners routers sequential parallel trigger router outcome", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase drain (routers first sequentially, then listeners in parallel) and the resumption-flag save/clear/restore around cyclic start re-execution; adapt payload plumbing if you lack human-feedback results; omit Enum unwrapping if your routers return plain strings. Direct tests executed green at pin.
