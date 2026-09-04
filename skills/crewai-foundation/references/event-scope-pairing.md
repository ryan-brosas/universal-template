<!-- capsule-v2 -->
# Event scope pairing — how does the bus know which started-event a finished-event closes, and what happens on mismatched or missing pairs?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** How do I port parent/child + started/completed event linkage that survives nesting without corrupting the chain?

## ContextVar scope stack with pair validation
**Path/Symbol:** `lib/crewai/src/crewai/events/event_bus.py` (`_prepare_event` :537–570); `lib/crewai/src/crewai/events/event_context.py` (stack push/pop :168–191, config :17–31).
**Signature:** `_prepare_event(self, source: Any, event: BaseEvent) -> None` — sync-only ("must only be called from synchronous emit paths").
**Data Shape:** `_event_id_stack: ContextVar[tuple[tuple[str, str], ...]]` of (event_id, type) frames; `EventContextConfig(max_stack_depth=100, mismatch_behavior=WARN, empty_pop_behavior=WARN)`.

### Decisive source
```python
if event.parent_event_id is None:
    if event_type_name in SCOPE_ENDING_EVENTS:
        event.parent_event_id = get_enclosing_parent_id()
        popped = pop_event_scope()
        if popped is None:
            handle_empty_pop(event_type_name)
        else:
            popped_event_id, popped_type = popped
            event.started_event_id = popped_event_id
            expected_start = VALID_EVENT_PAIRS.get(event_type_name)
            if expected_start and popped_type and popped_type != expected_start:
                handle_mismatch(event_type_name, popped_type, expected_start)
    elif event_type_name in SCOPE_STARTING_EVENTS:
        event.parent_event_id = get_current_parent_id()
        push_event_scope(event.event_id, event_type_name)
```
```python
# event_context.push_event_scope
if 0 < config.max_stack_depth <= len(stack):
    raise StackDepthExceededError(
        f"Event stack depth limit ({config.max_stack_depth}) exceeded. "
        f"This usually indicates missing ending events."
    )
```

**Flow:** every emitted event gets `previous_event_id` (linear chain), `triggered_by_event_id` (causal listener chain via `triggered_by_scope`), and a monotonically increasing `emission_sequence` → scope-STARTING types push their id onto the ContextVar stack → scope-ENDING types pop and stamp `started_event_id`, validating the popped type against `VALID_EVENT_PAIRS` → plain events just inherit current parent. Depth > 100 raises (runaway starts), empty pops / wrong-type pairs warn by default (configurable to RAISE/SILENT).
**Invariant:** The stack is per-context (ContextVar), so concurrent flows in different tasks keep independent scopes. Ending events link to the ENCLOSING parent (`stack[-2]`) because they replace their own start frame. Replay bypasses all of this (`replay()` skips `_prepare_event`) so stored ids stay stable.
**Probe:** `.venv/bin/python -m pytest lib/crewai/tests/events/test_event_context.py -q` (expect 27 passed covering pairing/mismatch/depth); static anchors: `handle_empty_pop(` ×1 call site :553–555, `expected_start = VALID_EVENT_PAIRS.get(...)` :558.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "event bus emit prepare_event scope stack replay is_replaying flush", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt tuple-frame ContextVar stacks with pair-table validation; adapt WARN-defaults to RAISE in strict environments; omit triggered-by threading if you don't reconstruct causal chains. Direct tests executed green at pin.
