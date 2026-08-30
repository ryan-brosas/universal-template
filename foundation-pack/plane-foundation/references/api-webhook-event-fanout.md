<!-- capsule-v2 -->
# Webhook event fan-out topology — how does one model mutation reach every subscribed webhook exactly once per field change?

**Source:** Plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** where should the diff happen, where the subscription filter, and how do deleted rows and mid-flight deletions avoid crashing or double-fetching?

## model_activity → webhook_activity → webhook_send_task
**Path/Symbol:** `apps/api/plane/bgtasks/webhook_task.py`:`model_activity` (:479–521), `webhook_activity` (:393–475), `get_model_data` (:125–168).
**Signature:** `model_activity(model_name, model_id, requested_data, current_instance, actor_id, slug, origin=None)`; `webhook_activity(event, verb, field, old_value, new_value, actor_id, slug, current_site, event_id, old_identifier, new_identifier)`.
**Data Shape:** three Celery stages chained by `.delay()` (no CALLS edges in a static graph — fan-in lives at 24 REST-view call sites). `current_instance` arrives as a JSON string snapshot taken before the write.

### Decisive source
```python
# model_activity: diff per key against the pre-write snapshot
for key in requested_data:
    if key in current_instance:
        current_value = current_instance.get(key, None)
        requested_value = requested_data.get(key, None)
        if current_value != requested_value:
            webhook_activity.delay(event=model_name, verb="updated", field=key,
                                   old_value=current_value, new_value=requested_value, ...)

# webhook_activity: subscription filter + per-webhook delivery task
webhooks = Webhook.objects.filter(workspace__slug=slug, is_active=True)
if event == "issue":
    webhooks = webhooks.filter(issue=True)
...
event_data=({"id": event_id} if verb == "deleted" else get_model_data(event=event, event_id=event_id)),
```

**Flow:** view writes → enqueues `model_activity` with requested vs pre-write JSON → one `webhook_activity` per CHANGED field (or a single `verb="created"` when no prior instance) → filter active webhooks by event-flag columns (`module_issue`→module flag, `cycle_issue`→cycle flag) → one `webhook_send_task.delay` per webhook with serialized row data; deleted events send only `{"id": event_id}` instead of refetching a gone row; `ObjectDoesNotExist` races are swallowed silently by design.
**Invariant:** fan-out happens only after the transaction commits (contract test `tests/contract/api/test_projects.py::test_model_activity_not_called_on_rollback` :146–184 pins no task on rollback); a deletion never re-reads the deleted row; per-field granularity is preserved end-to-end (`field/old_value/new_value` ride into the delivery payload's `activity`).
**Probe:** contract test named above (read directly this pass via its graph row + file citation; not executed — lane lacks Django test deps). Delivery-side consumption of the envelope is pinned in `api-webhook-delivery-envelope`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "model activity diff fields webhook activity fanout workspace webhooks", limit: 10, fields: ["signature", "name", "file"] });
```
Observed live at pass 2: ranks `model_activity` :479–521 #1, `webhook_activity` :393–475 #2, plus the rollback contract test #3.

## Verdict
Adopt the three-stage split (diff at enqueue time / filter+fan-out / per-subscriber delivery), the deleted-row stub, and the swallow-ObjectDoesNotExist race posture; adapt serializer expansion (`IssueExpandSerializer` labels+assignees prefetches) to your ORM; omit Plane's specific event-flag column set.
