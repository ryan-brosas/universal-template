<!-- capsule-v2 -->
# Flow event-driven runtime — how do @start/@listen/@router methods become an executed DAG with cyclic re-entry and resume?

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** What is the execution algorithm that turns listener conditions into method executions — and how must a porter preserve cyclic re-execution vs resumption suppression?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` — `_execute_start_method` (:2722), `_execute_method` (:2812), `_execute_listeners` (:3048), `_find_triggered_methods` (:3194).
**Signature:** `async _execute_start_method(start_method_name: FlowMethodName) -> None`; `async _execute_method(method_name, method, *args, **kwargs) -> tuple[Any, str | None]` (returns result + finished-event id); `async _execute_listeners(trigger_method, result, triggering_event_id=None) -> None`.
**Data Shape:** `_completed_methods: set`, `_method_outputs: list[{"method", "output"}]`, `_fired_or_listeners: set` guarded by `_or_listeners_lock`. Conditions are recursive dicts: `{"and": [...]}` / `{"or": [...]}` or plain event-name strings (`_condition_branches` :170).

### Decisive source
```python
# :2738 — completed-start gate flips meaning by mode
if start_method_name in self._completed_methods:
    if self._is_execution_resuming:
        # During resumption, skip execution but continue listeners
        ...
        return
    # For cyclic flows, clear from completed to allow re-execution
    self._completed_methods.discard(start_method_name)
    self._clear_or_listeners()
...
# :3072 router cascade runs to fixpoint BEFORE any parallel listeners
while True:
    routers_triggered = self._find_triggered_methods(current_trigger, router_only=True)
    if not routers_triggered:
        break
    ...  # each router's result becomes the next trigger; None result -> FlowMethodName("")
# :3157 normal listeners fan out in parallel per trigger
tasks = [self._execute_single_listener(n, listener_result,
          current_triggering_event_id) for n in listeners_triggered]
await asyncio.gather(*tasks)
# :3167 router outcomes can re-trigger conditional @start("event") methods
if current_trigger in router_results:
    for method_name in self._start_method_names():
        if self._start_condition_triggered_by(method_name, current_trigger):
            if method_name in self._completed_methods:
                was_resuming = self._is_execution_resuming   # :3174 cyclic re-run
                self._is_execution_resuming = False          # temporarily clears flag
                await self._execute_start_method(method_name)
                self._is_execution_resuming = was_resuming
```

**Flow:** kickoff → start method(s) → `_execute_method` (emit Started → PRE_STEP hook → run sync via `asyncio.to_thread(ctx.run, ...)` so contextvars propagate → auto-await returned coroutines → POST_STEP hook → append output → mark completed → persist → emit Finished returning its event_id) → `_execute_listeners`: routers first in a while-loop cascade until no new trigger, then non-router listeners per trigger via `asyncio.gather`, then router-outcome-triggered conditional starts.
**Invariant:** Resumption (`kickoff(inputs={"id": ...})`) replays/skips completed methods but STILL executes their listener chains (:2739-2744); cyclic re-entry is only possible because the completed-set entry is discarded (or the resume flag temporarily cleared at :3175). A porter who makes "completed" globally sticky breaks every loop; one who drops the resume gate double-runs on restart. Sync flow methods MUST run through `contextvars.copy_context()` + thread pool — `ask()`/context reads depend on it.
**Probe:** `grep -c 'def test_or_listener' lib/crewai/tests/test_flow.py` → `3`; `grep -c '_is_execution_resuming' lib/crewai/src/crewai/flow/runtime/__init__.py` → `11`.
**Direct test:** `tests/test_flow.py::test_cyclic_flow` (:73) loops a start→router cycle 3×; `tests/test_flow_resumability_regression.py::test_hitl_resumption_skips_completed_listeners` (:14) proves resume skips step_1/step_2 but still fires step_3's chain.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_execute_start_method executes a flow's start method and its triggered listeners", limit: 5 });
// → ext-crewAI.lib.crewai.src.crewai.flow.runtime.Flow._execute_start_method Method flow/runtime/__init__.py 2722-2774
```

## Verdict
Adopt the condition-tree evaluator, router-cascade-then-parallel-listener ordering, and the dual-mode completed-gate (resume skips / cycles discard). Adapt event names and persistence calls. Omit crewai's OpenTelemetry baggage plumbing and trace finalization — host-specific observability.
