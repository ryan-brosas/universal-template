<!-- capsule-v2 -->
# Audit trail append-only plane — what does "one row per task transition" have to store, who may read it back, and why do rows outlive hard deletes?

**Source:** awaithumans (Apache-2.0) `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do I shape an append-only audit model and its read surface so the trail survives task deletion without leaking to non-assignees?

## AuditEntry model + GET /{task_id}/audit
**Path/Symbol:** `packages/python/awaithumans/server/db/models/audit.py:AuditEntry` (:13–50); read route `server/routes/tasks.py:get_audit_trail_route` (:590–609); service `services/task_service.py:get_audit_trail` (:577–584); response schema `server/schemas/audit.py:AuditEntryResponse` (:13–29).
**Signature:** `get_audit_trail(session, task_id) -> list[AuditEntry]` ordered `created_at ASC`; route returns `list[AuditEntryResponse]`.
**Data Shape:** columns: nullable `from_status` (None = creation or no-status-change events), `to_status`, `action`, `actor_type` ∈ {system, human, agent}, nullable `actor_email`, nullable `channel`, JSON `extra_data`, embed attribution pair `embed_sub`(:256)/`embed_jti`(:64) populated only on /embed/* JWT-authenticated actions, tz-aware `created_at`.

### Decisive source
```python
task = await get_task(session, task_id)  # raises TaskNotFoundError
require_task_read(request, task)
entries = await get_audit_trail(session, task.id)
return [AuditEntryResponse.model_validate(e) for e in entries]
```
```python
# delete_task docstring — the deliberate orphaning:
"""Hard delete a task row. Operator-only surface.

Unlike `cancel_task` (which moves the task to a terminal CANCELLED
state but keeps the row for history), this actually removes the row
from the table. Audit entries are left in place, orphaned — they're
a historical record of what happened to a task that no longer exists,
and dropping them would erase evidence the operator may later need."""
```

**Flow:** every lifecycle mutation (create/claim/complete/cancel/timeout/notification-failure) appends one AuditEntry inside its own service commit → dashboard fetches `GET /api/tasks/{id}/audit` alongside the task → authorization reuses the SAME `require_task_read` gate as `GET /tasks/{id}` → rows serialized oldest-first with `created_at` through the `utc_iso` field serializer (naive-datetime boundary twin).
**Invariant:** The audit read allow-list equals the parent-task read allow-list (admin/operator/assignee): the assignee already sees payload/response/verifier_result on the task itself, so an operator-only audit 403 just blanked the dashboard /task page while protecting nothing; cross-assignee enumeration stays blocked because `require_task_read` only passes when `assigned_to_user_id == claims.user_id` for non-operators. Rows are never mutated or deleted by lifecycle code; only hard `delete_task` orphans them, on purpose.
**Probe:** `packages/python/tests/tasks/test_route_authorization.py:test_audit_visible_to_assignee` (:151–163, 200 for own task as reviewer-assignee) and `test_audit_blocked_for_non_assignee` (:166–174, 403 for another's task). Write-path twin already cited in notification-failure-audit.md (own-commit after parent transaction).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "task audit trail route", limit: 10 });
// −32.33 get_audit_trail_route 590-609; −12.13 db/models/audit.AuditEntry 13-50;
// −16.21 schemas/audit.AuditEntryResponse._ser_dt 28-29
```

## Verdict
Adopt the append-only row shape (nullable from_status, actor/channel/embed attribution), the read-gate-equals-parent-gate rule, and the deliberate orphan-on-hard-delete posture; adapt column vocabulary to your domain events; omit the Slack/embed-specific channel strings. Tests were read at :151–174; pytest execution BLOCKED in-lane (no sqlmodel/fastapi venv) — deterministic source probes substitute.
