<!-- capsule-v2 -->
# Least-Recently-Assigned Routing — how does `assign_to` resolve fairly plus infer assignees from notify?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What is the exact resolution ladder for assign_to shapes, where does fairness state advance, and when may notify imply an assignee?

## Option-C router: trust-explicit-email, filter-round-robin, implicit-from-single-DM
**Path/Symbol:** `packages/python/awaithumans/server/services/task_router.py:resolve_assign_to/_pick_least_recently_assigned/derive_implicit_assignee` (:69–293); fairness bump consumed by `create_task` within the same transaction (`task_service.py:82–96`).
**Signature:** `resolve_assign_to(session, assign_to) -> RoutingResult(user_id, email, slack_team_id?, slack_user_id?)`; `derive_implicit_assignee(session, notify) -> RoutingResult`.
**Data Shape:** input shapes `{email}`, `{role?, access_level?, pool?}`, `None`/unroutable; router NEVER mutates the task row — returns a decision the service applies (testability boundary).

### Decisive source
```python
stmt = (select(User)
    .where(User.active == True)
    .order_by(User.last_assigned_at.asc().nulls_first(),   # pinned BOTH dialects:
              User.created_at.asc())                        # Postgres defaults NULLS LAST!
    .limit(1))
for f in (role, access_level, pool):
    if f is not None: stmt = stmt.where(...)
picked = (await session.execute(stmt)).scalar_one_or_none()
picked.last_assigned_at = datetime.now(timezone.utc)      # fairness advances ONLY on commit
session.add(picked)
```

**Flow:** explicit email ⇒ look up for stable user_id but UNKNOWN addresses still route via `assigned_to_email` alone (trust the developer) → filter shape ⇒ least-recently-assigned pick, bump in CALLER's transaction (rollback undoes fairness) → nothing routable ⇒ empty result; then create_task's second chance: exactly ONE notify entry that is a Slack DM/email resolving to an active directory user BECOMES the assignee (`notify=["slack:@alice"]` means "alice is responsible" — otherwise her dashboard column stays empty AND the channel auth check rejects her submission). Channel sigils (`#chan`, C/G ids), multiple entries, non-directory targets all stay unassigned — ambiguity drops, never guesses.
**Invariant:** NULLS FIRST pinned explicitly (dialect divergence trap); marketplace passthrough returns empty rather than routing to a nonexistent user; dedup happens BEFORE routing (`test_task_router_integration.py:108–129` idempotent create doesn't bump anyone).
**Probe:** `tests/users/test_task_router.py` (:31–180 incl. new-user-wins-first-task, bump-on-route, filters-compose, inactive-never-picked, slack-only-routable); implicit ladder `tests/users/test_implicit_assignee.py` (:98–250 handle/email/user-id match vs sigil/multi/inactive skips).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "resolve_assign_to last_assigned_at routing", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt decision-object routers, transaction-coupled fairness bumps, dialect-pinned nulls ordering, and conservative single-target implicit assignment. Adapt role/pool vocabulary. Omit Slack client resolution internals (covered as dependency of the implicit path).
