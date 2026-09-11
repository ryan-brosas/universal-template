<!-- capsule-v2 -->
# Replay-vs-emit duality — how are recorded events re-dispatched without re-numbering them or re-triggering side effects like checkpoint writes?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What mechanism lets the same handler treat a live event and a replayed historical event differently?

## is_replaying ContextVar + _prepare_event bypass
**Path/Symbol:** `lib/crewai/src/crewai/events/event_bus.py` (`is_replaying` :73–81, `replay` :673–732, `_replaying` ContextVar :68–71); consumer `lib/crewai/src/crewai/state/checkpoint_listener.py:229–232`.
**Signature:** `replay(self, source: Any, event: BaseEvent) -> Future[None] | None`.
**Data Shape:** module-level `_replaying: ContextVar[bool] = ContextVar(..., default=False)`; token set around the whole dispatch.

### Decisive source
```python
def replay(self, source, event):
    """Dispatch a previously-recorded event without mutating its fields.

    Unlike :meth:`emit`, this does not run ``_prepare_event`` (so stored
    event ids and ``emission_sequence`` are preserved) and does not
    re-record the event. Listeners can call :func:`is_replaying` to
    opt out of side-effectful processing.
    """
    ...
    token = _replaying.set(True)
    try:
        ...
    finally:
        _replaying.reset(token)
```
```python
# checkpoint_listener._on_any_event — side-effect gate
def _on_any_event(source, event, state):
    if is_replaying():
        return
```

**Flow:** resume-from-checkpoint replays the persisted event record → `replay()` skips scope-stack mutation, id stamping, and recording → handlers registered normally still fire (timeline reconstruction works) but side-effectful handlers early-return on `is_replaying()` → flag resets in finally.
**Invariant:** Replayed events keep their ORIGINAL ids/sequence/parent links — re-stamping would fork the causal graph. The opt-in/out contract is per-handler: timeline listeners (trace batch, console formatter) MUST process replays; state-mutating listeners MUST NOT. Checkpoints also skip their own lifecycle events (`Checkpoint*BaseEvent` filter) to prevent recursive checkpoint storms.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/events/test_event_replay.py" -q` (expect 6 passed incl. `test_checkpoint_not_written_on_replay` and the full resume-replays-completed scenario).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "replay recorded events without mutating is_replaying flag", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-axis split (metadata preservation + handler-visible boolean); adapt naming to your bus; omit the lifecycle-event recursion filter only if you have no self-triggering event families. Direct tests executed green at pin.
