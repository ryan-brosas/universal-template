<!-- capsule-v2 -->
# Claim first-writer-wins — how does a broadcast task get assigned to exactly one human when many click "Claim" at once, and what does the loser see?

**Source:** awaithumans (Apache-2.0) `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What conditional-UPDATE shape assigns a shared task exactly once and names the winner to every loser?

## claim_task guarded UPDATE + loser-naming re-read
**Path/Symbol:** `packages/python/awaithumans/server/services/task_service.py:claim_task` (:254–326); route shells `routes/tasks.py:claim_task_route` (:425–469) and `cancel_task_route` (:472–500); cancel twin `cancel_task` (:523–558).
**Signature:** `claim_task(session, *, task_id, user_id, user_email=None, claimed_via_channel=None) -> Task` — raises `TaskNotFoundError | TaskAlreadyTerminalError | TaskAlreadyClaimedError`.
**Data Shape:** success = Task row with `assigned_to_user_id/assigned_to_email` set; audit row appended with `action="claimed"`, `from_status == to_status`, `channel=claimed_via_channel`, `extra_data={"user_id": ...}`.

### Decisive source
```python
result = await session.execute(
    update(Task)
    .where(Task.id == task_id)
    .where(Task.assigned_to_user_id.is_(None))
    .where(Task.status.notin_(list(TERMINAL_STATUSES_SET)))
    .values(assigned_to_user_id=user_id,
            assigned_to_email=user_email,
            updated_at=now)
)

if result.rowcount == 0:
    # Race: another claimer committed between our SELECT and UPDATE.
    # Re-read to tell the loser who actually won.
    await session.refresh(task)
    if task.assigned_to_user_id is not None:
        raise TaskAlreadyClaimedError(task_id, task.assigned_to_user_id)
    if task.status in TERMINAL_STATUSES_SET:
        raise TaskAlreadyTerminalError(task_id, task.status)
    # Shouldn't happen, but don't leave the caller guessing.
    raise TaskAlreadyClaimedError(task_id, None)
```

**Flow:** pre-checks (terminal? already-assigned fast-path with friendly error) → atomic conditional UPDATE whose WHERE re-encodes both guards → rowcount 0 means a racer won between SELECT and UPDATE → refresh and re-classify so the error NAMES the actual winner (or the actual terminal status) → append claim audit row (status unchanged: claiming changes assignment, not state) → commit → refresh → return.
**Invariant:** No SELECT-then-write assignment: the `WHERE assigned_to_user_id IS NULL AND status NOT IN terminal` predicate is the concurrency control (first commit wins; losers' UPDATE matches zero rows). The loser's error must identify the winner — the dashboard renders "already claimed by X" from it, and the Slack twin surfaces it as an ephemeral message. Route shell adds a human-identity guard the service cannot: admin bearer has no user_id, so claim requires an operator SESSION (400 otherwise); cancel mirrors the same conditional-UPDATE ladder against terminal statuses and its ROUTE rides `enqueue_completion_webhook` in the same request so a Temporal workflow never waits on a signal that never comes.
**Probe:** `packages/python/tests/tasks/test_route_authorization.py` — `test_claim_assigns_unassigned_task_to_caller` (:271–281, assignee pinned), `test_claim_with_admin_bearer_400` (:294–302), `test_claim_already_assigned_returns_409` (:305–315), `test_claim_terminal_task_returns_409` (:318–336); race-path itself untested upstream (single-process caveat); Slack e2e twin `tests/slack/test_claim_broadcast_e2e.py:test_second_claim_is_ephemeral_error` (:295–365).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "mnt-hdd-utopia-inspo-awaithumans", function_name: "claim_task", direction: "inbound", depth: 2 });
// callers: routes/tasks.claim_task_route, slack interactions claim button, email auto-claim
```

## Verdict
Adopt the guarded conditional UPDATE + loser-naming refresh re-read as THE assignment primitive across channels; adapt channel strings and error rendering; omit the Slack ephemeral plumbing (covered by slack-interactivity-entry.md). Distinct from partial-idempotency-index.md: that one protects concurrent CREATE via a DB index; this one protects concurrent ASSIGN via WHERE-rowcount. Tests read :271–336; pytest execution BLOCKED in-lane (no sqlmodel/fastapi venv) — deterministic source probes substitute.
