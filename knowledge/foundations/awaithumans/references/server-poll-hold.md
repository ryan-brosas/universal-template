<!-- capsule-v2 -->
# Server-side long-poll hold — how does the server wait up to 30 s without exhausting the DB pool or re-authorizing every tick?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What must the server half of a long-poll endpoint do so the SDK's reconnect loop gets sub-second completion latency without pinning pool sessions?

## One request, many 1-second reads
**Path/Symbol:** `packages/python/awaithumans/server/routes/tasks.py:poll_task_route` (:524–586).
**Signature:** `async def poll_task_route(task_id: str, request: Request, timeout: int = Query(25, ge=1, le=30)) -> PollResponse`.
**Data Shape:** GET `/api/tasks/{task_id}/poll?timeout=≤30`; returns `PollResponse{status, response|None, completed_at|None, timed_out_at|None}`. Terminal answer carries the full payload; a timed-out hold carries the last observed non-terminal status and null payload fields so the client reconnects.

### Decisive source
```python
# Authorise once on the initial read; the assignee/operator
# status of the caller doesn't change inside the long-poll
# window, so re-checking each second would just be busywork.
require_task_read(request, task)
if task.status in TERMINAL_STATUSES_SET:
    return PollResponse(status=task.status.value, response=task.response, ...)

# Long-poll: check every 1 second with a fresh session each time
elapsed = 0
last_status = task.status.value
while elapsed < timeout:
    await asyncio.sleep(1)
    elapsed += 1
    async with factory() as session:
        task = await get_task(session, task_id)
        if task.status in TERMINAL_STATUSES_SET:
            return PollResponse(...)
        last_status = task.status.value
return PollResponse(status=last_status, response=None, completed_at=None, timed_out_at=None)
```

**Flow:** immediate read + one-time authorization → terminal? return full payload now : sleep 1 s → fresh short-lived session re-read → loop until elapsed ≥ timeout → return current status with null payload.
**Invariant:** never hold a DB session across the sleep (each tick opens its own `async with factory() as session`, so N parked polls cost zero pool slots between ticks); authorization happens exactly once on the initial read (caller claims are immutable inside the window); `timeout` is clamped to ≤30 s to stay under common gateway kill windows — the server never promises a longer hold than the infrastructure allows.
**Probe:** no test at this pin hits `/poll` directly (grep of `packages/python/tests/` finds only comment mentions) — coverage caveat recorded. Adjacent pins: `packages/python/tests/tasks/test_route_authorization.py` (the require_task_read ladder this route leans on) and the client-half contract in `references/await-human-poll-loop.md`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "poll_task_route long poll fresh session terminal", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fresh-session-per-tick sweep, authorize-once snapshot, and the ≤30 s Query clamp paired with a null-payload timeout answer. Adapt the 1 s fixed tick to an event-driven wakeup (LISTEN/NOTIFY, conditional variable) when your store supports it — the invariant is "no session held while waiting," not the polling cadence. Omit assumptions about push delivery; this contract deliberately keeps the client reconnecting.
