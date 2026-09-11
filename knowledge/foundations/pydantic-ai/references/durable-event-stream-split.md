<!-- capsule-v2 -->
# Durable event-stream split — ModelResponseStreamEvents were delivered live in-boundary; workflow-side replays dispatch only the rest

## Source / Question
`pydantic_ai_slim/pydantic_ai/durable_exec/_base.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** An agent's event stream crosses a durable boundary — some events were already delivered live inside the engine's model-request unit, and workflow-side they arrive as REPLAY. How do you avoid double-delivering text deltas to the handler while still delivering everything else? A porter will re-dispatch the whole stream and duplicate every token.

## Path / Symbol
`_base.py` — `wrap_run_event_stream` (:191–214), `_effective_event_stream_handler` (:177–185), `has_wrap_run_event_stream` (:187–189), `_MODEL_RESPONSE_STREAM_EVENT_TYPES` (:37), `_single_event_stream` (:342–346).

## Signature
```python
async def wrap_run_event_stream(self, ctx, *, stream: AsyncIterable[AgentStreamEvent])
    -> AsyncIterator[AgentStreamEvent]
def _effective_event_stream_handler(self) -> EventStreamHandler | None   # engines override for per-run state
```

## Data Shape
Two delivery regimes keyed on `in_durable_context` + handler presence: outside a durable container, the handler wraps via `ProcessEventStream` as normal; inside one, `dispatch_events = True` and only NON-`ModelResponseStreamEvent`s are dispatched. DBOS overrides `_effective_event_stream_handler` to honor the handler recorded in a wrapper-era workflow's inputs so recovery replays the recorded step sequence exactly.

### Decisive source — replay-aware filtering with guaranteed stream closure (:198–214)
```python
if event_stream_handler is not None and not self.in_durable_context:
    stream = self._process_event_stream.wrap_run_event_stream(ctx, stream=stream)
elif event_stream_handler is not None:
    dispatch_events = True
try:
    async for event in stream:
        # ModelResponseStreamEvents were already delivered live to the handler inside the
        # model-request boundary; workflow-side they're the replay, so only HandleResponseEvents
        # are dispatched to the handler here.
        if dispatch_events and not isinstance(event, _MODEL_RESPONSE_STREAM_EVENT_TYPES):
            await self._dispatch_event_stream_event(ctx, event)
        yield event
finally:
    await aclose_if_supported(stream)
```
The union-type set is precomputed once at import via `get_union_args(ModelResponseStreamEvent)` — isinstance checks against a tuple of concrete event classes.

**Flow:** handler present? → outside container: delegate to the standard processor wrapper → inside: filter per-event → every event is still yielded downstream regardless of dispatch (the consumer's view is complete either way) → `finally` closes the underlying stream so abandoned iterations don't leak generators.

**Invariant:** Text deltas must reach the handler exactly once across both sides of the boundary; the yield path is never filtered. Engine-specific event delivery happens inside each engine's own durable unit (`_dispatch_event_stream_event`, abstract).

**Probe:** `tests/test_dbos.py::test_dbos_agent_run_in_workflow_with_event_stream_handler` (:1227), `test_dbos_agent_iter_in_workflow_fires_event_stream_handler` (:739), `test_dbos_agent_run_in_workflow_with_runtime_event_stream_handler` (:710); `tests/test_temporal.py` wrapper-agent replay tests (:749).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'wrap_run_event_stream _MODEL_RESPONSE_STREAM_EVENT_TYPES dispatch_events'
```

## Verdict
**Adopt** the live-vs-replay event taxonomy, filtered-dispatch/always-yield shape, precomputed union set, and aclose-in-finally. **Adapt** what counts as an "already-delivered-live" event class in your host. **Omit** per-engine input-recorded handler recovery unless you have wrapper-era workflows.
