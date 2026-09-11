<!-- capsule-v2 -->
# Three-Caller Task Authorization — how do admin, operator, and assignee compose into route guards?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you layer per-task authorization over middleware authentication without ballooning every route handler?

## Small orthogonal predicates + two require_* gates
**Path/Symbol:** `packages/python/awaithumans/server/core/task_auth.py` — `_is_admin_bearer` (:30–32), `caller_is_operator` (:40–46), `caller_user_id` (:49–56), `require_task_read` (:59–76), `require_task_complete` (:79–85), `require_operator_or_admin` (:88–102).
**Signature:** all take `(request: Request[, task: Task]) -> None`, raising `HTTPException(403)` on denial; claims arrive via `request.state.auth_claims` (set by `core/auth.py` middleware), admin flag via `request.state.auth_admin_token`.
**Data Shape:** caller taxonomy = admin bearer (agent/ops/CI — bypasses everything) | operator session (`is_operator=True`) | assignee session (`claims.user_id == task.assigned_to_user_id`) | everyone else forbidden.

### Decisive source
```python
def caller_is_operator(request: Request) -> bool:
    # Admin bearer is intentionally NOT counted as operator here — use
    # `_is_admin_bearer` separately when the route should accept either.
    ...
def require_task_read(request: Request, task: Task) -> None:
    if _is_admin_bearer(request): return
    if caller_is_operator(request): return
    user_id = caller_user_id(request)
    if user_id is not None and task.assigned_to_user_id == user_id:
        return
    raise HTTPException(status_code=403, detail="You don't have access to this task.")
```

**Flow:** middleware authenticates and stamps request.state → route handlers call one gate: read/complete = admin∨operator∨assignee; cancel/poll/audit/list-all = `require_operator_or_admin`.
**Invariant:** `caller_user_id` returns None for admin-bearer callers (they have NO user identity — an admin bearer must never be treated as a directory user); `require_task_complete` is a separate function despite identical body "so future divergence doesn't require chasing callers"; the assigned_to check is "the single source of authorisation" for non-operators.
**Probe:** `packages/python/tests/tasks/test_route_authorization.py` (route-level 401/403 matrix); last-operator protection in `tests/users/test_security_guards.py` (:27 delete-last-operator refused, :81 guard ignores inactive operators).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "require_task_read caller_is_operator auth_admin_token", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-caller taxonomy, state-stamped claims handoff, identity-less-admin rule, and deliberate duplicate-gate-for-future-divergence. Adapt claim names to your session format. Omit nothing — the ordering (admin→operator→assignee→403) is the whole contract.
