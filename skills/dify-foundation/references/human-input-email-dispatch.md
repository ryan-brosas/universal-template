<!-- capsule-v2 -->
# human-input-email-dispatch — How does a paused workflow notify a human without blocking the run?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What happens when the engine pauses on a HITL (human-in-the-loop) form?

## Per-reason email task dispatch, best-effort, on the mail queue
**Path/Symbol:** `api/core/app/apps/workflow_app_runner.py:_enqueue_human_input_notifications` (:714-726) called from `_handle_event`'s `GraphRunPausedEvent` arm (:435-452); task at `api/tasks/mail_human_input_delivery_task.py:dispatch_human_input_email_task`.
**Signature:** `_enqueue_human_input_notifications(reasons: Sequence[object])`.
**Data Shape:** Iterates pause reasons; keeps only `HumanInputRequired` instances with a non-empty `form_id`; Celery `.apply_async(kwargs={"form_id", "node_title"}, queue="mail")`.

### Decisive source
```python
case GraphRunPausedEvent():
    runtime_state = workflow_entry.graph_engine.graph_runtime_state
    paused_nodes = list(
        dict.fromkeys(reason.node_id for reason in event.reasons if isinstance(reason, HitlRequired))
    )
    enriched_reasons = enrich_graph_pause_reasons(
        reasons=event.reasons,
        form_repository=HumanInputFormSubmissionRepository(),
        variable_pool=runtime_state.variable_pool,
    )
    self._enqueue_human_input_notifications(enriched_reasons)
    self._publish_event(QueueWorkflowPausedEvent(reasons=enriched_reasons, outputs=event.outputs,
                                                 paused_nodes=paused_nodes))
...
def _enqueue_human_input_notifications(self, reasons: Sequence[object]) -> None:
    for reason in reasons:
        if not isinstance(reason, HumanInputRequired):
            continue
        if not reason.form_id:
            continue
        try:
            dispatch_human_input_email_task.apply_async(kwargs={"form_id": reason.form_id, "node_title": reason.node_title},
                                                        queue="mail")
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to enqueue human input email task for form %s", reason.form_id)
```

**Flow:** engine pauses → runner dedupes paused node ids (order-preserving `dict.fromkeys`) → reasons enriched with Dify-owned form data from the repository → email tasks fanned out per form onto the dedicated mail queue → paused event published to the client. Broker failure logs and continues — the pause itself is already durable.
**Invariant:** Notification is best-effort and AFTER enrichment (emails carry resolved titles); missing form_id skips silently; dispatch is per-reason so multi-form pauses produce one mail each; the run's fate never depends on the broker succeeding.
**Probe:** `grep -c "queue=\"mail\"" core/app/apps/workflow_app_runner.py` → 1; `grep -c 'dispatch_human_input_email_task' core/app/apps/workflow_app_runner.py` → 2.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "_handle_event GraphRunPausedEvent human input notifications email", limit: 10 });
```

## Verdict
Adopt fire-and-forget side-channel notification on pause, ordered after state enrichment. Adapt broker/queue names. Omit the enrichment internals (human-input boundary plane is its own porting question).
