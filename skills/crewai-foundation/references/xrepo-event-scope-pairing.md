<!-- capsule-v2 -->
# Cross-repo pattern: event-scope pairing ledger — crewAI's ContextVar stack vs autogen's intervention pipeline bookkeeping

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744` (`events/event_context.py` stack :168–191 + `event_bus._prepare_event` pairing :549–565); cross-ref graph `ext-autogen` `python/packages/autogen-core/src/autogen_core/_single_threaded_agent_runtime.py` envelope/intervention dispatch. Codebase Memory projects `ext-crewAI`, `ext-autogen`. **Question:** How do two frameworks correlate a lifecycle START with its END across nested, concurrent executions?

## Pattern: per-context frame stack with validated pop
**Path/Symbol:** crewAI `_event_id_stack: ContextVar[tuple[tuple[str,str], ...]]`; autogen routes every message through intervention handler chains where response envelopes carry the originating context.
**Signature:** `push_event_scope(event_id: str, event_type: str)` / `pop_event_scope() -> tuple[str, str] | None`.
**Data Shape:** immutable tuple frames (event_id, type) — copy-on-write per ContextVar.set; `VALID_EVENT_PAIRS` maps ending→starting type.

### Decisive source
```python
# crewai — ending events pop and VALIDATE what they close
popped = pop_event_scope()
if popped is None:
    handle_empty_pop(event_type_name)          # warn/raise/silent
else:
    popped_event_id, popped_type = popped
    event.started_event_id = popped_event_id
    expected_start = VALID_EVENT_PAIRS.get(event_type_name)
    if expected_start and popped_type and popped_type != expected_start:
        handle_mismatch(event_type_name, popped_type, expected_start)
```

**Flow:** scope-starting events push their id → nested starts stack frames → ending events pop the innermost frame, stamping `started_event_id` and checking it against the pair table → plain events inherit current top as parent → depth cap (100) converts runaway starts into hard errors.
**Invariant:** Both frameworks make correlation CONTEXT-LOCAL (crewAI via ContextVars so concurrent flows/tasks never interleave scopes; autogen by threading envelopes through each actor's own invocation). Pop-time validation catches missing/mismatched endings at the source instead of corrupting downstream duration/pairing analytics. Configurable severity (WARN default, RAISE available) keeps strict hosts honest without breaking lenient ones.
**Probe:** `.venv/bin/python -m pytest lib/crewai/tests/events/test_event_context.py -q` (expect 27 passed); static anchors: `handle_empty_pop(event_type_name)` ×1 :553–555, `expected_start = VALID_EVENT_PAIRS.get(...)` ×1 :558.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "event scope stack push pop pair validation context", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt context-local frames + pop-validation for any start/end telemetry; adapt the pair table to your taxonomy; omit depth caps at your peril — they are the only guard against leaked-start loops.
