<!-- capsule-v2 -->
# node-exception-output-preservation — Which failure events still persist their node outputs?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** Where is the line between a failed node whose partial outputs matter and one they don't?

## Exception events save outputs; plain failures do not
**Path/Symbol:** `api/core/app/apps/workflow/generate_task_pipeline.py:_handle_node_failed_events` (:381-396), `_handle_node_succeeded_event` (:367-379), `_save_output_for_event` (:793-801).
**Signature:** `_save_output_for_event(event: QueueNodeSucceededEvent | QueueNodeExceptionEvent, node_execution_id: str)`.
**Data Shape:** Draft-variable saver factory receives app_id/node_id/node_type/node_execution_id and `enclosing_node_id = event.in_loop_id or event.in_iteration_id`; saves `(process_data, outputs)`.

### Decisive source
```python
def _handle_node_failed_events(self, event, **kwargs):
    """Handle various node failure events."""
    node_failed_response = self._workflow_response_converter.workflow_node_finish_to_stream_response(
        event=event, task_id=self._application_generate_entity.task_id)
    if isinstance(event, QueueNodeExceptionEvent):        # exception ≠ failure
        self._save_output_for_event(event, event.node_execution_id)
    if node_failed_response:
        yield node_failed_response

# success handler saves unconditionally:
self._save_output_for_event(event, event.node_execution_id)
```

**Flow:** node succeeds → outputs saved + streamed. Node raises but the engine caught it as an ERROR-CONTINUATION (error branch / fail-allowed node) → QueueNodeExceptionEvent → outputs saved so downstream/debug views see what was produced before the error. Node hard-fails → QueueNodeFailedEvent → streamed for UI only, no persistence of outputs.
**Invariant:** Exactly two events carry savable payloads (Succeeded, Exception) — adding a third means touching both the isinstance gate AND `_save_output_for_event`'s union; enclosing_node_id prefers loop over iteration when both are set; saving uses the draft-saver port which no-ops outside debugger runs.
**Probe:** `grep -c 'if isinstance(event, QueueNodeExceptionEvent):' core/app/apps/workflow/generate_task_pipeline.py` → 1; `grep -c '_save_output_for_event(event' …` → 2 call sites.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "QueueNodeExceptionEvent _save_output_for_event draft saver", limit: 10 });
```

## Verdict
Adopt the succeeded/exception-only persistence split. Adapt what "exception" means in your engine (here: engine-handled error branches). Omit the debugger-only draft saver if you have no equivalent debug surface.
