<!-- capsule-v2 -->
# OR-listener fire-once ledger — how do multi-event `or_()` listeners avoid double-firing across parallel starts and chained routers?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** When several events can satisfy one `or_(a, b)` listener, what exactly prevents the listener from running twice — and when is it allowed to run again?

## Fired-OR-listener ledger + re-arm sweep
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`Flow._find_triggered_methods` :3194–3215, `_rearm_or_listeners_for_trigger` :1043–1072, `_clear_or_listeners` :1023–1026, `_fired_or_listeners` PrivateAttr :723).
**Signature:** `_find_triggered_methods(self, trigger_method: FlowMethodName, router_only: bool) -> list[FlowMethodName]`; `_rearm_or_listeners_for_trigger(self, trigger: FlowMethodName, rearmable: set[FlowMethodName] | None = None) -> None`.
**Data Shape:** `_fired_or_listeners: set[FlowMethodName]` guarded by a per-instance `threading.Lock` (`_or_listeners_lock`, :729); `_pending_events: dict[PendingListenerKey, set[str]]`.

### Decisive source
```python
# _find_triggered_methods
should_check_fired = _is_multi_event_or(condition) and not is_router
if should_check_fired and listener_name in self._fired_or_listeners:
    continue
...
    triggered.append(listener_name)
    if should_check_fired:
        self._fired_or_listeners.add(listener_name)
```
```python
# _rearm_or_listeners_for_trigger (cyclic re-fire)
for listener_name in candidates:
    condition = self._listen_condition(listener_name)
    if condition is None: continue
    if trigger_str in _iter_condition_events(condition):
        to_discard.append(listener_name)
```

**Flow:** method completes → `_find_triggered_methods` walks listeners; multi-event OR conditions consult the fired-set first → satisfied AND unfired ⇒ execute once and add to fired-set → later router emissions call `_rearm_or_listeners_for_trigger(trigger)` which discards only listeners whose condition *mentions the new trigger*, letting cyclic flows re-fire them.
**Invariant:** A multi-event `or_()` listener fires AT MOST ONCE per dispatch wave; single-event listeners are never ledgered (`_is_multi_event_or` requires >1 alternative); routers never enter the fired-set (`and not is_router`). Re-arm removes ONLY listeners whose event list contains the current trigger — a chained-router wave (`SignalA→SignalB`) cannot double-fire because neither re-arm pass matches both events before the listener runs. Cycle restart clears ALL fired entries via `_clear_or_listeners()` (:1024), not per-listener discard.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow.py::test_or_listener_fires_once_across_parallel_starts" "lib/crewai/tests/test_flow.py::test_or_listener_re_arms_across_router_loop" "lib/crewai/tests/test_flow.py::test_or_listener_does_not_double_fire_across_chained_routers" -q` (expect 3 passed; pins fire_count==1 parallel, ==3 cyclic, ==1 chained).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_rearm_or_listeners_for_trigger fired or listeners cyclic", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fired-set ledger keyed by method name plus trigger-scoped re-arm; adapt lock granularity to your host runtime; omit CrewAI's `PendingListenerKey` start-condition namespace if you have no conditional starts. Direct tests executed green at pin.
