<!-- capsule-v2 -->

# Flow-run watch single subscriber — How do you watch ONE remote run to completion without polling?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** What is the per-run alternative to a shared completion bus, and how does it avoid missing an already-finished run?

## Subscribe first, read once, then trust only final-state events; re-read authoritative state before returning

**Path/Symbol:** `src/prefect/flow_runs.py:wait_for_flow_run (57-158)` (snippet-resolved). Retrieve anchor: `wait_for_flow_run Function 57-158` (`^wait_for_flow_run$` returns this row plus the waiter twin).

**Signature:** `async wait_for_flow_run(flow_run_id: UUID, timeout: int | None = 10800, poll_interval: int | None = None, client=None, log_states: bool = False) -> FlowRun` — raises `FlowRunWaitTimeout`.

**Data Shape:** filter narrows BOTH by event-name prefix AND resource id: `EventFilter(event=EventNameFilter(prefix=["prefect.flow-run"]), resource=EventResourceFilter(id=[f"prefect.flow-run.{flow_run_id}"]))`; terminal detection via `StateType(event.resource["prefect.state-type"])` → `State(type=...).is_final()`.

### Decisive source
```python
with anyio.move_on_after(timeout):
    async with get_events_subscriber(filter=event_filter) as subscriber:
        flow_run = await client.read_flow_run(flow_run_id)   # AFTER subscribing
        if flow_run.state and flow_run.state.is_final():
            return flow_run                                  # already done
        async for event in subscriber:
            if not (state_type := event.resource.get("prefect.state-type")):
                continue                # heartbeats etc. carry no state-type
            state_type = StateType(state_type)
            state = State(type=state_type)
            if log_states:
                logger.info(f"Flow run is in state {state.name!r}")
            if state.is_final():
                return await client.read_flow_run(flow_run_id)  # re-read
raise FlowRunWaitTimeout(
    f"Flow run with ID {flow_run_id} exceeded watch timeout of {timeout} seconds")
```

**Flow:** the subscription is opened BEFORE the initial read so there is no gap in which a completion could slip between "read says running" and "listening starts" — worst case the first events are redundant, never missed. Heartbeat events pass through harmlessly because they lack the `prefect.state-type` resource attribute. A final-state event triggers one authoritative `read_flow_run` rather than trusting the event payload, and that re-read FlowRun is the return value. Timeout raises a typed `FlowRunWaitTimeout`. `poll_interval` remains only as a deprecated no-op — events fully replaced polling here.

**Invariant:** (1) Subscribe-then-read ordering eliminates the check-then-listen race at the source (contrast the register-recheck ladder needed when a SHARED consumer exists: `waiter-completion-event-race-ladder`). (2) Events signal; API reads decide — the event only says "go look". (3) Non-state events are skipped structurally (missing attribute), not by name enumeration. (4) Timeout is a typed failure, not a silent return.

**Probe:** direct tests `tests/test_flow_runs.py`: `:26-38 test_create_then_wait_for_flow_run` (already-final run returns immediately with equal FlowRun), `:41-52 test_create_then_wait_timeout` (FlowRunWaitTimeout at timeout=0), `:55-94 test_wait_for_flow_run_handles_heartbeats` — regression test for issue #17930 emitting `prefect.flow-run.heartbeat` mid-watch; watch completes with `is_completed()`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^wait_for_flow_run$", "limit": 5}'
```
(observed: 2 rows — `flow_runs.wait_for_flow_run Function src/prefect/flow_runs.py 57-158` rank-2 beside the waiter method; this capsule covers the Function row.)

## Verdict
Adopt subscribe-before-read + signal-vs-decide split for single-target watches; adapt the terminal predicate to your state model; prefer the shared-bus shape (`terminal-event-waiter-singleton`) once watcher count grows.
