<!-- capsule-v2 -->
# Assignee Directory Search Ladder — how does one broad-search needle match email, Slack ID, and display name without N round-trips, and why does a trailing email branch exist?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** When the operator types anything into an Assignee filter, how do you resolve it to tasks across three identity columns with one query — and what legacy shape must keep working?

## Connected graph-selected seam
**Path/Symbol:** `packages/python/awaithumans/server/services/task_service.py` — `list_tasks` (:162-225) + `_resolve_assignee_search` (:228-251).
**Signature:** `async def _resolve_assignee_search(session: AsyncSession, query: str) -> list[str]` / `async def list_tasks(session, *, status=None, assigned_to_query=None, assigned_to_user_id=None, unassigned=False, terminal=False, limit=50, offset=0) -> list[Task]`.
**Data Shape:** one `select(User.id).where(or_(email == needle, slack_user_id == needle, lower(display_name).LIKE '%lower(needle)%'))` → list of user ids; list_tasks then ORs `Task.assigned_to_email == query` with `Task.assigned_to_user_id.in_(matched)`.

### Decisive source
```python
async def _resolve_assignee_search(session: AsyncSession, query: str) -> list[str]:
    """...
    Runs a single query: `email == X OR slack_user_id == X OR
    lower(display_name) LIKE '%lower(X)%'`. Returns whatever set
    matches — possibly empty. We don't enforce a length floor on
    `query` because the caller already trimmed it to non-empty;
    operators who paste a single character get a wide match and
    that's their problem to refine."""
    needle = query.strip()
    if not needle:
        return []
    rows = await session.execute(
        select(User.id).where(
            or_(
                User.email == needle,
                User.slack_user_id == needle,
                func.lower(User.display_name).like(f"%{needle.lower()}%"),
            )
        )
    )
    return [r[0] for r in rows.all()]
```
And the consumption side (:218-221):
```python
conditions = [Task.assigned_to_email == assigned_to_query]
if matched_user_ids:
    conditions.append(Task.assigned_to_user_id.in_(matched_user_ids))
query = query.where(or_(*conditions))
```

**Flow:** dashboard sends `?assigned_to=<needle>` → route passes it as `assigned_to_query` (only for operators — non-operators get scope FORCED to their own id and the param stripped) → `_resolve_assignee_search` runs ONE directory query → conditions always include the raw-email branch; user-id IN-branch appended only when matched non-empty → rows ordered by `created_at.desc()`.
**Invariant:** the trailing `assigned_to_email == query` branch is NOT redundant — it catches tasks assigned BY EMAIL before the recipient was provisioned as a directory row (#73), where `assigned_to_user_id` is null so the id-IN branch can never see them. Explicit `status=` wins over `terminal=True` via `elif` (:204-209) so "filter within terminal" composes; `unassigned` (BOTH columns null, :210-212) lives in the if-arm so it structurally beats both assignee filters; empty/unknown needle ⇒ 200 `[]`, never an error.

**Probe:** `packages/python/tests/tasks/test_route_authorization.py` — `test_list_assigned_to_matches_display_name_substring` (:398-416, typing "op" finds the operator's task, pre-#73 returned []), `test_list_assigned_to_matches_slack_user_id_exact` (:419-442, patches `slack_user_id="U_TEST_OP"` then searches it), `test_list_assigned_to_matches_email_exact` (:387-395, pins the legacy shape), `test_list_assigned_to_unknown_returns_empty` (:445-454).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "assignee search resolve email slack user id display name substring", limit: 5 });
```
Live at pin: rank-1 `test_list_assigned_to_matches_display_name_substring` −35.85 (:398-416); rank-2 `_resolve_assignee_search` −35.71 (:228-251); also surfaced `test_list_assigned_to_matches_slack_user_id_exact` −23.15 (:419-442).

## Verdict
Adopt the two-stage ladder: exact-or-substring resolution against the DIRECTORY first, then task filtering that keeps a raw-column fallback for identities that predate provisioning. Adapt column names to your identity model. Omit nothing silently — if you drop the trailing email branch, document that pre-provisioned assignments become invisible to search.
