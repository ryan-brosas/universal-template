<!-- capsule-v2 -->
# trigger-log-status-map-layer — How does an async trigger learn its run's outcome?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** How do you map engine lifecycle events onto external job-bookkeeping rows without coupling the engine?

## ClassVar status map + accumulate-on-resume elapsed time
**Path/Symbol:** `api/core/app/layers/trigger_post_layer.py:TriggerPostLayer` (:24-98).
**Signature:** `__init__(cfs_plan_scheduler_entity, start_time: datetime, trigger_log_id: str)`; hooks on_graph_start/on_event/on_graph_end.
**Data Shape:** `_STATUS_MAP: dict[type[GraphEngineEvent], WorkflowTriggerStatus]` = Succeeded→SUCCEEDED, Failed→FAILED, **Aborted→FAILED**, Paused→PAUSED; log row updated with workflow_run_id (read from system variable), outputs JSON, total_tokens, finished_at; elapsed ACCUMULATES when already set.

### Decisive source
```python
_STATUS_MAP: ClassVar[dict[type[GraphEngineEvent], WorkflowTriggerStatus]] = {
    GraphRunSucceededEvent: WorkflowTriggerStatus.SUCCEEDED,
    GraphRunFailedEvent: WorkflowTriggerStatus.FAILED,
    GraphRunAbortedEvent: WorkflowTriggerStatus.FAILED,
    GraphRunPausedEvent: WorkflowTriggerStatus.PAUSED,
}

def on_event(self, event: GraphEngineEvent):
    """Update trigger log with success or failure."""
    if isinstance(event, tuple(self._STATUS_MAP.keys())):
        with session_factory.create_session() as session:
            repo = SQLAlchemyWorkflowTriggerLogRepository(session)
            trigger_log = repo.get_by_id(self.trigger_log_id)
            if not trigger_log:
                logger.exception("Trigger log not found: %s", self.trigger_log_id)
                return
            elapsed_time = (datetime.now(UTC) - self.start_time).total_seconds()
            ...
            trigger_log.status = self._STATUS_MAP[type(event)]     # exact type, not isinstance
            trigger_log.workflow_run_id = workflow_run_id
            trigger_log.outputs = TypeAdapter(dict[str, Any]).dump_json(outputs).decode()
            if isinstance(event, GraphRunAbortedEvent):
                trigger_log.error = event.reason or "Workflow execution aborted"
            if trigger_log.elapsed_time is None:
                trigger_log.elapsed_time = elapsed_time
            else:
                trigger_log.elapsed_time += elapsed_time          # pause/resume segments sum
            trigger_log.total_tokens = total_tokens
            trigger_log.finished_at = datetime.now(UTC)
            repo.update(trigger_log)
            session.commit()
```

**Flow:** layer attached by the async-trigger runner → terminal/pause engine event arrives → exact-type lookup → one transaction updates the trigger row → aborted runs carry the abort reason as their error text. Paused writes PAUSED with a finished_at stamp; the RESUMED run's layer instance adds its segment's elapsed time.
**Invariant:** Aborted maps to FAILED (a user cancel is still a non-success outcome for the waiter) while Paused is distinct — collapsing either is wrong for consumers polling status; `type(event)` in the map lookup avoids subclass surprises; missing log row is logged-and-ignored, never raised from an event hook.
**Probe:** `grep -c '_STATUS_MAP' core/app/layers/trigger_post_layer.py` → 3; `grep -c 'trigger_log.elapsed_time is None' …` → 1; direct tests `tests/unit_tests/core/app/layers/test_trigger_post_layer.py::test_on_event_updates_trigger_log`, `::test_on_event_handles_missing_trigger_log`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "TriggerPostLayer on_event trigger log status", limit: 10 });
```

## Verdict
Adopt the declarative status map and additive elapsed semantics. Adapt statuses to your job model. Omit the CFS-plan entity reference — only start_time/log_id are load-bearing.
