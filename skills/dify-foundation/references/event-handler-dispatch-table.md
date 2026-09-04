<!-- capsule-v2 -->
# event-handler-dispatch-table — How should 20+ event types map to handlers without a 44-branch if-chain?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What is the dispatch order that keeps terminal events authoritative?

## Exact-type dict lookup, then isinstance fallbacks, then silent drop
**Path/Symbol:** `api/core/app/apps/workflow/generate_task_pipeline.py:WorkflowAppGenerateTaskPipeline._get_event_handlers` (:614-643) + `_dispatch_event` (:645-694); hot path `_process_stream_response` (:696-746).
**Signature:** `_get_event_handlers() -> dict[type, Callable]`; `_dispatch_event(event, *, tts_publisher=None, trace_manager=None, queue_message=None)` yields StreamResponse.
**Data Shape:** Handler map keyed by exact event class (19 entries); two isinstance groups: node failures (`QueueNodeFailedEvent|QueueNodeExceptionEvent`) and workflow terminators (`QueueWorkflowFailedEvent|QueueStopEvent`).

### Decisive source
```python
def _dispatch_event(self, event, *, tts_publisher=None, trace_manager=None, queue_message=None):
    """Dispatch events using elegant pattern matching."""
    handlers = self._get_event_handlers()
    event_type = type(event)

    # Direct handler lookup
    if handler := handlers.get(event_type):
        yield from handler(event, tts_publisher=tts_publisher, trace_manager=trace_manager, queue_message=queue_message)
        return

    # Handle node failure events with isinstance check
    if isinstance(event, (QueueNodeFailedEvent, QueueNodeExceptionEvent)):
        yield from self._handle_node_failed_events(event, ...)
        return

    # Handle workflow failed and stop events with isinstance check
    if isinstance(event, (QueueWorkflowFailedEvent, QueueStopEvent)):
        yield from self._handle_workflow_failed_and_stop_events(event, ...)
        return

    # For unhandled events, we continue (original behavior)
    return
```

**Flow:** queue message → exact-type lookup (fastest, most specific wins) → grouped isinstance fallback for unions sharing a handler → anything else is DROPPED silently. The outer loop breaks the stream itself on QueueError/WorkflowFailed/Pause/Stop — dispatch never decides termination.
**Invariant:** `type(event)` (not isinstance) for the table so subclasses don't shadow their parents' entries; unhandled ⇒ no-op, never an error — forward compatibility with newer engine events; terminal handling (break) lives in `_process_stream_response`'s match, keeping "what renders" separate from "when the stream ends".
**Probe:** `grep -c 'handlers.get(event_type)' core/app/apps/workflow/generate_task_pipeline.py` → 1; direct test `tests/unit_tests/core/app/apps/workflow/test_generate_task_pipeline_core.py::test_dispatch_event_direct_failed_and_unhandled_paths`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "_dispatch_event unhandled events continue handler lookup", limit: 10 });
```

## Verdict
Adopt exact-type-then-union dispatch with silent unknown-event tolerance. Adapt handler sets to your protocol. Omit the TTS publisher plumbing unless porting audio autoplay.
