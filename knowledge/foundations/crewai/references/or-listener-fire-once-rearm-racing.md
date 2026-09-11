<!-- capsule-v2 -->
# Multi-event or() listeners — fire-once latch, router-loop re-arm, and first-wins racing

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How does an `or_(a, b)` listener fire exactly once across parallel starts, re-fire each loop iteration, yet never double-fire within one dispatch wave — and when do its sources race?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` — `_find_triggered_methods` fired-latch (:3201-3211), `_rearm_or_listeners_for_trigger` (:1043), `_build_racing_groups` (:1074), `_execute_racing_listeners` (:1147).
**Signature:** `_rearm_or_listeners_for_trigger(trigger: FlowMethodName, rearmable: set | None = None) -> None`; `_build_racing_groups() -> dict[frozenset[FlowMethodName], FlowMethodName]`.
**Data Shape:** `_fired_or_listeners` mutated only under `_or_listeners_lock`; racing map keys are frozensets of EXCLUSIVELY-owned alternative events.

### Decisive source
```python
# :3201 — latch: multi-event or_ listeners are consumed on first fire
should_check_fired = _is_multi_event_or(condition) and not is_router
if should_check_fired and listener_name in self._fired_or_listeners:
    continue
...
if self._condition_met(condition, trigger_method, ...):
    triggered.append(listener_name)
    if should_check_fired:
        self._fired_or_listeners.add(listener_name)

# :3126 — snapshot of fired set taken ONCE per dispatch wave (pre-index >0 triggers)
with self._or_listeners_lock:
    rearmable: set[FlowMethodName] = set(self._fired_or_listeners)
for idx, current_trigger in enumerate(all_triggers):
    if idx > 0 and rearmable:
        self._rearm_or_listeners_for_trigger(current_trigger, rearmable)

# :1107 — racing applies ONLY to events exclusively feeding one or_ listener;
# events shared with another listener (e.g. an and_) never race; events nested
# under and_ branches are not alternatives ("cancelling one would make the AND
# unsatisfiable")
exclusive_events = {e for e in alternatives
                    if listeners_by_event[e] == {listener_name}}
```

**Flow:** Trigger → find_triggered adds matching or-listener to `_fired_or_listeners` (single fire even when both a and b complete in parallel) → wave's remaining triggers (router outcomes) re-arm any fired listener whose condition REFERENCES the trigger string → cyclic loops therefore re-fire per iteration. When >1 exclusive alternatives trigger together they run via `asyncio.as_completed`; first completion wins, siblings' tasks are cancelled; non-racing co-listeners still gather normally.
**Invariant:** The re-armable set is snapshotted BEFORE the fan-out loop so chained routers inside ONE wave cannot resurrect a just-fired listener (:239 test); re-arm matches by literal trigger membership in the condition tree (`trigger_str in _iter_condition_events`). Exclusive-ownership check is what keeps `or_(and_(a,b), c)` from cancelling the AND arm.
**Probe:** `grep -c 'def test_or_listener_re_arms_across_router_loop' lib/crewai/tests/test_flow.py` → `1` (regression for upstream #5972, asserts 3 fires over 3 iterations); `grep -c 'asyncio.as_completed(racing_tasks)' lib/crewai/src/crewai/flow/runtime/__init__.py` → `1`.
**Direct test:** `tests/test_flow.py::test_or_listener_fires_once_across_parallel_starts` (:185), `::test_or_listener_does_not_double_fire_across_chained_routers` (:239), `::test_and_branch_inside_or_does_not_race` (:1637), `::test_cyclic_flow_multiple_or_listeners_fire_every_iteration` (:2023).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_execute_racing_listeners first-wins cancel racing listeners", limit: 5 });
// → ext-crewAI.lib.crewai.src.crewai.flow.runtime.Flow._execute_racing_listeners Method flow/runtime/__init__.py 1147-1196
```

## Verdict
Adopt the fire-once latch + trigger-membership re-arm + exclusivity-gated racing trio as one inseparable contract — porting any piece alone reintroduces #5972-class double-fire bugs. Adapt method-name types to host enums. Omit the OpenTelemetry baggage reads around trigger payloads.
