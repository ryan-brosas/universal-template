<!-- capsule-v2 -->
# Workforce event bus — How do structured callbacks turn every lifecycle transition into observable, typed events?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What is the WorkforceCallback surface and the emit discipline at each transition site?

## Fan-out loop per typed event
**Path/Symbol:** `camel/societies/workforce/events.py` (models :22-168), emission sites in workforce.py `_post_task` (:4154), `_handle_failed_task` (:4679-4691), `_apply_recovery_strategy` (:1877-1948), `_listen_to_channel` (:5589-5611).
**Signature:** `WorkforceCallback` protocol methods: `log_message(LogEvent)`, `log_worker_created(WorkerCreatedEvent)`, `log_task_assigned(TaskAssignedEvent)`, `log_task_started(TaskStartedEvent)`, `log_task_updated(TaskUpdatedEvent)`, `log_task_decomposed(TaskDecomposedEvent)`, `log_task_created(TaskCreatedEvent)`, `log_task_failed(TaskFailedEvent)`, `log_task_completed(TaskCompletedEvent)`, `log_all_tasks_completed(AllTasksCompletedEvent)`; plus StreamChunkEvent path.
**Data Shape:** All models extend `WorkforceEventBase(BaseModel)` with timestamp + event type fields; TaskFailedEvent carries `metadata: {failure_count, task_content, result_length}`.

### Decisive source
```python
task_failed_event = TaskFailedEvent(
    task_id=task.id,
    worker_id=worker_id,
    parent_task_id=task.parent.id if task.parent else None,
    error_message=detailed_error,
    metadata={'failure_count': task.failure_count,
              'task_content': task.content,
              'result_length': len(task.result) if task.result else 0},
)
for cb in self._callbacks:
    cb.log_task_failed(task_failed_event)
```

**Flow:** every transition constructs a pydantic event THEN fans out over `self._callbacks` — assignment (with dependency list), started (on post, not on claim), updated (replan content diffs / reassign old→new worker ids with quality metadata), decomposed (parent + subtask id list), created (per subtask during decomposition), failed (attempt N/max + result-length telemetry), completed (processing time from `_task_start_times` + token usage), all-completed (once, at IDLE). Free-text `LogEvent(message, level, color)` covers human-readable narration alongside structured events. Emission is inline at the transition site — never a middleware hook — so porters must replicate call sites or lose observability.
**Invariant:** Events are constructed BEFORE fan-out (consistent snapshot even if a callback mutates nothing) and callback exceptions are NOT caught here — reliability contract lives at stream-callback layer only.
**Probe:** `grep -c 'for cb in self._callbacks' camel/societies/workforce/workforce.py` → 36.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "WorkforceCallback TaskFailedEvent log_task_failed callbacks", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt typed-event construction + explicit fan-out for orchestration audit trails. Adapt model fields to your telemetry schema. Omit colorama styling.
