<!-- capsule-v2 -->
# Racing OR-listeners first-wins — when several alternative events are already pending, how does the flow run them in parallel and keep only the winner?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** How do I port "first of these alternatives to finish wins, cancel the rest" without killing AND-branch members?

## Exclusive-event race groups
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`Flow._build_racing_groups` :1074–1120, `_get_racing_group_for_listeners` :1122–1145, `_execute_racing_listeners` :1147–1196; `_racing_groups_cache` :724–726).
**Signature:** `_build_racing_groups(self) -> dict[frozenset[FlowMethodName], FlowMethodName]`; `_execute_racing_listeners(self, racing_listeners: frozenset[FlowMethodName], other_listeners: list[FlowMethodName], result: Any, triggering_event_id: str | None = None) -> None`.
**Data Shape:** cache maps `{frozenset(member method names): or_listener}`; members are METHOD names (leaf events re-enter method space), built lazily once per instance.

### Decisive source
```python
exclusive_events = {
    event
    for event in alternatives
    if listeners_by_event[event] == {listener_name}
}
if len(exclusive_events) > 1:
    racing_groups[
        frozenset(FlowMethodName(event) for event in exclusive_events)
    ] = listener_name
```
```python
for coro in asyncio.as_completed(racing_tasks):
    try:
        await coro
    except Exception as e:
        logger.debug(f"Racing listener failed: {e}")
        continue
    break

for task in racing_tasks:
    if not task.done():
        task.cancel()
...
await asyncio.gather(*other_tasks, return_exceptions=True)
```

**Flow:** listener batch arrives → intersect batch with each racing group → ≥2 members present ⇒ split into racing vs other → racing tasks run under `as_completed`; the FIRST task that completes *without raising* breaks the loop → remaining unfinished racing tasks cancelled → a failed racer is logged at debug and skipped (the next completion wins) → non-racing listeners always gather with `return_exceptions=True`.
**Invariant:** Only EXCLUSIVELY-owned alternatives race — an event also feeding another listener (e.g. an AND branch) is excluded (`listeners_by_event[event] == {listener_name}`), so cancelling it could never make an AND unsatisfiable. Events nested under `and_()` inside `or_(and_(a,b), c)` are never alternatives. Exceptions do NOT win the race.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow.py::test_and_branch_inside_or_does_not_race" "lib/crewai/tests/test_flow.py::test_or_branch_does_not_leave_stale_and_state" -q` (expect 2 passed; pins that AND-inside-OR members still execute and the OR join fires exactly once).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "racing listeners first-wins as_completed cancel", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt exclusive-membership gating plus as_completed/cancel-first-wins semantics; adapt the debug-log-and-skip failure policy to your error surface; omit the frozenset caching if flows are short-lived. Direct tests executed green at pin.
