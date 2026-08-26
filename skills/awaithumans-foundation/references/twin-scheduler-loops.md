<!-- capsule-v2 -->
# Twin Scheduler Loops — how do background sweeps survive crashes without a job framework?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What shape must an asyncio background loop take so one bad tick never kills the sweep?

## while-True / try / fresh-session-per-tick / sleep-outside-try
**Path/Symbol:** `packages/python/awaithumans/server/services/timeout_scheduler.py` — `run_timeout_scheduler` (:23–38), `_check_and_timeout_expired_tasks` (:41–69); twin `webhook_scheduler.py:28–54`.
**Signature:** `run_timeout_scheduler() -> None` (never returns); `_check_and_timeout_expired_tasks() -> None`; `process_due_deliveries(session) -> int` (webhook tick body).
**Data Shape:** timeout sweep query = `select(Task.id).where(status.notin_(TERMINAL_STATUSES_SET)).where(timeout_at <= now)` — ids only, riding the indexed `timeout_at` column; intervals 5s/5s from `utils/constants.py`.

### Decisive source
```python
while True:
    try:
        await _check_and_timeout_expired_tasks()
    except Exception:
        logger.exception("Error in timeout scheduler")
    await asyncio.sleep(TIMEOUT_CHECK_INTERVAL_SECONDS)
```

**Flow:** every tick: fresh session per iteration ("so a long-running attempt can't starve the connection pool") → claim batch → do I/O → commit → sleep OUTSIDE the try (a sleeping exception can never be swallowed into a tight loop).
**Invariant:** the two schedulers are deliberately separate asyncio tasks with unrelated failure modes — "a flapping receiver shouldn't delay timeouts; a long DB lock during timeout sweep shouldn't pause deliveries." Timeout completion fan-out: `timeout_task()` (first-writer-wins conditional UPDATE) → `enqueue_completion_webhook(session, task)` → fire-and-forget `asyncio.create_task(update_slack_messages_for_task(task.id))` replacing dead Approve/Reject buttons with a Timed-out surface so recipients don't fill forms on dead tasks.
**Probe:** no dedicated upstream unit test for either loop body (their workers are thin over tested contracts: `test_webhook_dispatch.py`, conditional-update guards pinned in pass-1 capsules) — coverage caveat recorded in-capsule.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "run_timeout_scheduler run_webhook_scheduler process_due_deliveries", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the loop skeleton (catch-all-log, sleep outside try, fresh session per tick) and the one-scheduler-per-failure-domain split. Adapt intervals and fan-out actions. Omit Slack surface replacement if you have no channel notifications — but keep SOME terminal-state UX update, that's the load-bearing part of the fan-out.
