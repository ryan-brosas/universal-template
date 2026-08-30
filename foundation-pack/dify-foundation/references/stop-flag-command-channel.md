<!-- capsule-v2 -->
# stop-flag-command-channel — How does the legacy Redis stop flag reach a GraphEngine that only understands abort commands?

**Source:** dify Apache-2.0 `main@44aec257`; Codebase Memory `ext-dify`. **Question:** A pre-engine Redis flag (`generate_task_stopped:{task_id}`) and a command-pulling engine must meet somewhere — where, and with what exactly-once discipline?

## Third command channel translating one flag read into one AbortCommand
**Path/Symbol:** `api/core/app/apps/workflow/command_channels.py:StopFlagCommandChannel` (:72-99); reader `api/core/app/apps/execution_coordinator.py:is_app_task_stop_flag_set` (:41-46); wired in both runners (`app_runner.py:168`, `advanced_chat/app_runner.py:238`) inside `CombinedCommandChannel((RedisChannel, StopFlagCommandChannel, celery_signal_channel))`.
**Signature:** `StopFlagCommandChannel(*, task_id: str, abort_reason: str = "User requested stop")`; `fetch_commands() -> list[GraphEngineCommand]`; `send_command(_)` = no-op.
**Data Shape:** Same `_abort_emitted` instance latch as `CelerySignalCommandChannel` (:41-69) — at most ONE `AbortCommand(reason=...)` per channel instance; empty task_id reads as never-stopped; the flag is the SAME key the coordinator sets on abort (`app_task_stop_flag_key`, SETEX 600s).

### Decisive source
```python
def fetch_commands(self) -> list[GraphEngineCommand]:
    if self._abort_emitted or not is_app_task_stop_flag_set(self._task_id):
        return []
    self._abort_emitted = True
    return [AbortCommand(reason=self._abort_reason)]
```

**Flow:** engine's listen loop periodically pulls `CombinedCommandChannel.fetch_commands()` → per-channel try/except fan-in (a failing channel logs and is skipped, others still answer) → flag set ⇒ this channel emits exactly one AbortCommand then goes quiet via its latch → engine aborts; queue side stops accepting successors (see stop-aware-ready-queue-enqueue-gate).
**Invariant:** EXACTLY-ONCE emission per instance (latch checked BEFORE the Redis read, so post-latch the channel costs zero Redis round-trips); translation is READ-ONLY — send_command is an explicit no-op so this channel can never be the primary sink; the flag is deliberately NOT cleared here (the coordinator's reset ladder owns deletion); three-channel tuple ordering matters: sends route to `_command_channels[0]` only.
**Probe:** `cd api && .venv/bin/pytest -p no:cacheprovider -o addopts= tests/unit_tests/core/app/apps/workflow/test_command_channels.py -q` → 9 passed (includes emits-once-per-instance: first fetch 1 command, second []; send-noop; combined fan-in). EXECUTED GREEN at `44aec257`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "StopFlagCommandChannel AbortCommand is_app_task_stop_flag_set", limit: 10 });
```

## Verdict
Adopt the poll-to-command adapter with its emit-once latch whenever a legacy boolean signal must drive a command protocol — it keeps the engine unaware of storage details. Adapt the signal source (any KV/flag) and the reason string. Omit nothing; the class is self-contained. Direct tests cover emit/no-emit/once/noop paths; no coverage caveat.
