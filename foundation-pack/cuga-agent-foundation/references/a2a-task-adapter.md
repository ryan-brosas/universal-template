<!-- capsule-v2 -->
# A2A task adapter — duck-typed event translation with a guaranteed terminal event

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** You expose an agent graph over a streaming task protocol (A2A). How do you translate internal graph events to protocol lifecycle events WITHOUT coupling the protocol layer to graph internals — and guarantee the client's task never hangs open when the graph dies mid-stream?

## The adapter
**Path/Symbol:** `src/cuga/backend/server/a2a/task_adapter.py` (`stream_events_to_a2a` :87-167, `_is_hitl` :29-32, `_is_final` :35-40, `_is_error` :43-51, `_event_text` :54-69).
**Signature:** `stream_events_to_a2a(events: Iterable[Any], *, task_id, context_id) -> Iterator[TaskStatusUpdateEvent]`.
**Data Shape:** input events are duck-typed (`name`, optional `data`, optional `final`) — CUGA's internal event types are deliberately NOT imported; output is A2A `TaskStatusUpdateEvent`s with states working / input_required / completed / failed.

### Decisive source
```python
# task_adapter.py:95-100 — the contract in the docstring
# Guarantees:
# - At least one terminal event is always emitted (completed or failed),
#   so an A2A client never hangs on an open task.
# - Unknown event names are coerced into a ``working`` update rather
#   than raising — protocol forward-compatibility.
# - ``context_id`` round-trips verbatim onto every emitted event.

# :158-167 — the guarantee, mechanically enforced at generator exit
if not saw_terminal:
    yield TaskStatusUpdateEvent(... final=True, state=TaskState.completed ...)
```

**Flow:** per event, three-way dispatch: HITL names (substring hints: approval/input_required/user_input/interrupt/hitl) → `input_required` with `final=` the event's own flag (a HITL pause can be terminal when the runner marks it so) and an `action_id` carried in message metadata for approval correlation; terminal names (final_answer/task_complete/completed/done) or `final=True` → completed UNLESS `_is_error` (error/failed/failure/exception) → **failed** — without this error-terminals silently mapped to success; anything else (including unknown names) → `working`. Text extraction probes data-as-string then dict keys text/message/prompt/content, falling back to the event name so frames are never empty.
**Invariant:** substring matching on lowercased names is deliberate forward-compat (new HITL variants keep mapping); the terminal-guarantee check lives AFTER the loop so even an empty or crashed stream yields exactly one closing event; context_id is echoed verbatim for client-side correlation.

**Probe:** direct tests `tests/unit/a2a/test_task_adapter.py::test_full_lifecycle_progresses_working_then_completed` (:73), `::test_hitl_event_maps_to_input_required` (:92), `::test_error_terminal_event_maps_to_failed_not_completed` (:146), `::test_named_error_event_without_final_flag_still_terminates` (:163), `::test_empty_stream_emits_at_least_terminal_state` (:136), `::test_unknown_event_name_does_not_raise` (:124), `::test_context_id_round_trips_to_thread` (:106).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "stream_events_to_a2a TaskStatusUpdateEvent _is_hitl _is_final TaskState", limit: 10 });
```

## Verdict
Adopt the duck-typed narrow event surface (protocol layer never imports graph internals) and the mechanical guaranteed-terminal-event pattern for any streaming task protocol. Adapt the hint/name lists and metadata key (action_id) to your HITL vocabulary. Omit SDK type construction if your protocol differs — the invariant transfers regardless.
