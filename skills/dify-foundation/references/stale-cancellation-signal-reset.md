<!-- capsule-v2 -->
# stale-cancellation-signal-reset — Why does a resumed workflow abort itself the moment it starts?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What leftover state must be cleared before re-running a task whose previous attempt was cancelled or paused?

## Both cancellation channels outlive their attempt
**Path/Symbol:** `api/core/app/apps/execution_coordinator.py:clear_app_task_cancellation_signals` (:36-67); key builders `app_task_command_channel_key` (:24-26), `set_app_task_stop_flag` (:29-33).
**Signature:** `clear_app_task_cancellation_signals(task_id: str) -> None`.
**Data Shape:** Redis key `generate_task_stopped:{task_id}` (SETEX 600s); Redis-list command channel `workflow:{task_id}:commands` (queued AbortCommand TTL ~1h); both keyed by STABLE task id that a resume deliberately reuses.

### Decisive source
```python
def clear_app_task_cancellation_signals(task_id: str) -> None:
    """...A resumed workflow deliberately reuses the paused run's task ID, so without
    this reset it inherits those signals and aborts itself as soon as it starts.
    Call this only when starting a new attempt that is meant to run, never mid-execution."""
    if not task_id:
        return
    try:
        redis_client.delete(f"generate_task_stopped:{task_id}")
    except Exception:
        logger.exception("Failed to clear stop flag for app task %s", task_id)

    channel_key = app_task_command_channel_key(task_id)
    try:
        # fetch_commands() drains the queue and its pending marker together; the
        # explicit delete covers a queue whose marker was already consumed.
        discarded = RedisChannel(redis_client, channel_key).fetch_commands()
        redis_client.delete(channel_key)
        ...
```

**Flow:** resume request → clear stop flag FIRST → drain command queue via `fetch_commands()` (removes pending marker too) → belt-and-braces `delete(channel_key)` for a marker-less queue → start new attempt. Failures are logged, never raised.
**Invariant:** The stop-flag delete happens BEFORE the channel drain so a channel failure cannot leave the flag armed (test-pinned order); reset runs ONLY at attempt start — calling mid-execution would discard legitimate in-flight aborts; empty task_id is a silent no-op.
**Probe:** `api/tests/unit_tests/core/app/apps/test_execution_coordinator.py::test_clearing_cancellation_signals_drops_stop_flag_and_queued_commands` (delete call args == [("generate_task_stopped:task",), ("workflow:task:commands",)] in that exact order) and `::test_clearing_cancellation_signals_survives_command_channel_failure` (channel raise ⇒ flag still deleted + log line).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "clear_app_task_cancellation_signals stale signals resumed attempt", limit: 10 });
```

## Verdict
Adopt the two-channel reset ladder and its ordering guarantee. Adapt the storage (any durable KV/pub-sub pair works as long as both outlive the process). Omit nothing — this is the documented fix for the self-aborting-resume bug class; porters who skip it will reproduce the bug under any task-id-reuse scheme.
