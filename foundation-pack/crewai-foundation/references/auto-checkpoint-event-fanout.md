<!-- capsule-v2 -->
# Auto-checkpoint event fan-out — how does checkpointing hook into EVERY entity event without each entity opting in, and how are recursion and replays excluded?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** How do I snapshot full program state on selected events with zero per-entity boilerplate?

## Subclass-walk registration + replay/lifecycle gates
**Path/Symbol:** `lib/crewai/src/crewai/state/checkpoint_listener.py` (`_register_all_handlers` :247–270, `_on_any_event` :229–244, `_do_checkpoint` :113–193); trigger config `state/checkpoint_config.py:158–234`.
**Signature:** `_should_checkpoint(source: Any, event: BaseEvent) -> CheckpointConfig | None`; `_do_checkpoint(state: RuntimeState, cfg: CheckpointConfig, event: BaseEvent | None) -> None`.
**Data Shape:** `on_events: list[CheckpointEventType | "*"]` (default `["task_completed"]`), ~100-type Literal union; providers discriminated by `provider_type` (json|sqlite).

### Decisive source
```python
def _collect(cls: type[BaseEvent]) -> None:
    subclasses: list[type[BaseEvent]] = cls.__subclasses__()
    for sub in subclasses:
        if sub not in seen:
            seen.add(sub)
            type_field = sub.model_fields.get("type")
            if (
                type_field
                and type_field.default
                and type_field.default != "base_event"
            ):
                event_bus.register_handler(sub, _on_any_event)
            _collect(sub)
```
```python
def _on_any_event(source, event, state):
    if is_replaying():
        return
    if isinstance(event, (CheckpointBaseEvent, CheckpointForkBaseEvent,
                          CheckpointRestoreBaseEvent)):
        return
    cfg = _should_checkpoint(source, event)
    ...
# Only the sync handler is registered. The event bus runs sync handlers
# in a ``ThreadPoolExecutor``, so blocking I/O is safe and we avoid
# writing duplicate checkpoints from both sync and async dispatch.
```

**Flow:** first CheckpointConfig construction walks the FULL BaseEvent subclass tree and registers ONE shared sync handler on every concrete event type → on any matching event, resolve the nearest config from source (entity or parents), gate on trigger set / `"*"`, snapshot ALL live entities via `RuntimeState.model_dump` (private runtime attrs synced onto public checkpoint fields first), write through provider, chain lineage, prune.
**Invariant:** Registration is idempotent (`seen` set) and lazy (first config touch). Sync-only registration is load-bearing: dual sync+async handlers would double-write every checkpoint. Replays and checkpoint-lifecycle events are hard-excluded; failures log a warning and never break the emitting run.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/events/test_event_replay.py::TestCheckpointNotReplayed::test_checkpoint_not_written_on_replay" -q` (expect 1 passed); static anchor: `grep -c "if is_replaying():" lib/crewai/src/crewai/state/checkpoint_listener.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "checkpoint listener auto checkpoint on event register all subclasses", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt tree-walk bulk registration + sync-only dispatch + replay/lifecycle exclusion; adapt the trigger Literal to your event taxonomy; omit provider discrimination for single-backend products. Direct tests executed green at pin.
