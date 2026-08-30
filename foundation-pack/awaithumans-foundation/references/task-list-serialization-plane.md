<!-- capsule-v2 -->
# Task List Serialization Plane — how do you serialize up to 200 task rows without 2N user lookups, and what does the list endpoint deliberately hide that the detail endpoint shows?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** When one route serializes a page of tasks and five others serialize single tasks, where does the N+1 boundary live and which fields differ between list and detail?

## Connected graph-selected seam
**Path/Symbol:** `packages/python/awaithumans/server/routes/tasks.py` — `_build_user_index` (:79-94), `_task_to_response` (:97-119), `_task_to_response_with_lookup` (:122-135), `list_tasks_route` (:222-306).
**Signature:** `async def _build_user_index(session: AsyncSession, tasks: Iterable[Task]) -> dict[str, User]` / `_task_to_response(task, *, redact=False, assignee=None, completer=None)` / `async def _task_to_response_with_lookup(session, task, *, redact=False)`.
**Data Shape:** index collects `assigned_to_user_id ∪ completed_by_user_id` into a set → one `select(User).where(User.id.in_(user_ids))` → `{u.id: u}`; empty set short-circuits to `{}` (no query at all).

### Decisive source
```python
async def _build_user_index(session: AsyncSession, tasks: Iterable[Task]) -> dict[str, User]:
    """Bulk-load Users referenced by the tasks (assignee + completer).

    One query per request instead of 2N — list_tasks_route in
    particular can return up to 200 rows. Empty when no task has
    either field set."""
    ...
    result = await session.execute(select(User).where(User.id.in_(user_ids)))
    return {u.id: u for u in result.scalars().all()}
```
And in the list route — note the unconditional redaction:
```python
    users_by_id = await _build_user_index(session, tasks)
    return [
        _task_to_response(
            t,
            redact=True,
            assignee=users_by_id.get(t.assigned_to_user_id or ""),
            ...
```

**Flow:** embed ctx present ⇒ 403 `embed_token_cannot_list_tasks` BEFORE any scoping → operator session or admin bearer ⇒ unscoped; otherwise scope FORCED to `caller_user_id(request)` with `assigned_to`/`unassigned` params stripped → `list_tasks(...)` → `_build_user_index` once → map rows through `_task_to_response(redact=True)`. Single-task routes (`get/create/complete/claim/cancel`) instead call `_task_to_response_with_lookup`, which does its own two per-task lookups.
**Invariant:** LIST responses always redact payload when `task.redact_payload` is set (`redact=True` even for operators — the queue view never needs payloads); DETAIL responses return full payload to whoever passed `require_task_read`. A non-operator's client-supplied `assigned_to=` filter must be discarded, not honored — honoring it would let any dashboard account enumerate another person's tasks.
**Probe:** `packages/python/tests/tasks/test_route_authorization.py` — `test_list_scoped_to_assignee_for_non_operator` (:180), `test_list_unscoped_for_operator` (:196), `test_list_assigned_to_filter_ignored_for_non_operator` (:208, reviewer passing `assigned_to=other@…` still sees only their own).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "task to response lookup eager load list tasks", limit: 5, fields: ["signature", "lines"] });
```
Live rank-1 `_task_to_response_with_lookup` −38.73 (:122-135); rank-3 `list_tasks` −25.84; snippets for `_build_user_index`/`list_tasks_route` retrieved via get_code_snippet at pin.

## Verdict
Adopt the cardinality-keyed split: bulk index for lists, per-task lookup helper for detail routes; adopt list-always-redacts + server-forced scoping as security posture. Adapt the limit ceiling and field names to your surface. Omit nothing silently — if your list DOES need payloads, make that an explicit authorization decision, not a default. Caveat: no dedicated test pins the redact-on-list behavior itself (redaction unit tests live in test_response_redaction.py against single-task responses).
