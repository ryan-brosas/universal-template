<!-- capsule-v2 -->
# publish-side-terminal-stop-listen — How does the listener learn that the run is over?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** Who ends the consumer loop — the producer publishing an event, or the event's content being consumed?

## Terminal-event publish doubles as listener shutdown
**Path/Symbol:** `api/core/app/apps/workflow/app_queue_manager.py:WorkflowAppQueueManager._publish` (:26-48).
**Signature:** `_publish(event: AppQueueEvent, pub_from: PublishFrom)`.
**Data Shape:** Wraps each event in `WorkflowQueueMessage(task_id, app_mode, event)`; after enqueue, inspects the event TYPE to decide whether to end the listening segment.

### Decisive source
```python
@override
def _publish(self, event: AppQueueEvent, pub_from: PublishFrom):
    message = WorkflowQueueMessage(task_id=self._task_id, app_mode=self._app_mode, event=event)
    self._q.put(message)

    if isinstance(event, QueueWorkflowPausedEvent):
        self.stop_listen(execution_state=AppExecutionState.PAUSED)
    elif isinstance(
        event,
        QueueStopEvent
        | QueueErrorEvent
        | QueueMessageEndEvent
        | QueueWorkflowSucceededEvent
        | QueueWorkflowFailedEvent
        | QueueWorkflowPartialSuccessEvent,
    ):
        self.stop_listen(execution_state=AppExecutionState.TERMINAL)

def stop_listen(self, *, execution_state: AppExecutionState) -> None:
    """Complete the current listener segment with an explicit execution state."""
    if execution_state is AppExecutionState.PAUSED:
        self._execution_coordinator.mark_paused()
    elif execution_state is AppExecutionState.TERMINAL:
        self._execution_coordinator.mark_terminal()
    else:
        raise ValueError(f"Unsupported listener completion state: {execution_state}")
    self._listener_segment_completed.set()
    self._clear_task_belong_cache()
    self._q.put(None)
```

**Flow:** publish → event enqueued FIRST (consumer must receive it) → same call classifies it: Paused ⇒ coordinator.mark_paused; any terminal ⇒ mark_terminal → segment latch set, belong cache cleared, `None` sentinel enqueued → listen loop drains the real event, then breaks on the sentinel.
**Invariant:** The event is enqueued BEFORE the sentinel so the client always receives the terminal payload; pause and terminal are distinct coordinator states (a paused run's watchdog must be cancelled, not fired); classification happens at PUBLISH time in the queue-manager subclass — the base class never decides.
**Probe:** `grep -c 'stop_listen(execution_state=' core/app/apps/workflow/app_queue_manager.py` → 2; direct tests `tests/unit_tests/core/app/apps/pipeline/test_pipeline_queue_manager.py::test_publish_stop_events_trigger_stop_listen` + `::test_publish_non_stop_event_no_stop_listen`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "WorkflowAppQueueManager _publish stop_listen paused terminal", limit: 10 });
```

## Verdict
Adopt "producer classifies terminal events and stops the stream" — consumers stay dumb. Adapt the event-type list to your protocol and which states count as pause vs terminal for your resumer. Omit the app_mode field if you have one channel per app kind.
