<!-- capsule-v2 -->
# Toolset token refresh hardening — what does the SECOND-generation refresher fix over the connector one (cooldowns, atomic scheduling, retry-backoff saves)?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** When porting per-config-path OAuth refresh (toolsets/MCP apps), which race-guards did the evolved service add that the naive version lacks?

## Schedule-lock atomics + 10 s cooldown + exponential credential-save retries
**Path/Symbol:** `backend/python/app/connectors/core/base/token_service/toolset_token_refresh_service.py:` `REFRESH_COOLDOWN = 10` (:34), `MIN_IMMEDIATE_RECHECK_DELAY = 1` (:35), `_get_toolset_lock/_get_schedule_lock` (:58-80), cooldown+immediate block (:1270-1300), credential save retries (:~800-840), `_delayed_refresh` finally (:1294-1319).
**Signature:** `async def _schedule_token_refresh(config_path, toolset_type, token)` holding `_schedule_locks[config_path]` across check-existing-task → cooldown-check → create-task; `time.time()` stamped into `_last_refresh_time` ONLY after a fully successful save.
**Data Shape:** Per-key dicts: `_toolset_locks` (serialize refreshes), `_schedule_locks` (atomic scheduling), `_last_refresh_time: dict[str, float]`, `_invalid_refresh_failures`.

### Decisive source
```python
async with self._get_schedule_lock(config_path):        # "check existing + create" atomic per path
    ...
    time_since_last_refresh = current_time - self._last_refresh_time.get(config_path, 0)
    if time_since_last_refresh < REFRESH_COOLDOWN:      # 10 s duplicate suppressor
        return
    if delay <= 0:
        delay = MIN_IMMEDIATE_RECHECK_DELAY             # 1 s recheck instead of instant refresh
        refresh_time = datetime.now() + timedelta(seconds=delay)
    self._create_refresh_task(...)                      # created WHILE lock held

# credential persistence: bounded retry with doubling delay, else hard raise
retry_delay *= 2  ... else: raise Exception(f"Failed to save refreshed credentials ... after {max_retries} attempts")
```
Cleanup also lock-guarded: delete the tracked task only under the same schedule lock AND only if `tracked_task is asyncio.current_task()`.

**Flow:** differences vs `token_refresh_service.py`: (1) scheduling decisions happen under a per-path lock so two concurrent triggers can't both create tasks; (2) a completed refresh installs a 10-second cooldown suppressing rapid duplicate schedule requests; (3) an at-threshold token schedules a 1 s RE-CHECK rather than refreshing inline (bounded recursion); (4) saving new credentials retries with exponential backoff because the config store may be mid-restart — losing a freshly rotated refresh_token would brick the toolset; (5) three-strikes ladder identical to connector service but keyed by config_path.
**Invariant:** A rotated-but-unsaved refresh token equals data loss — persistence deserves retries more than the refresh call itself. Schedule-time atomics belong on the SCHEDULER, not inside the refresh coroutine.
**Probe:** `grep -c 'REFRESH_COOLDOWN = 10' app/connectors/core/base/token_service/toolset_token_refresh_service.py` → `1`; suite `tests/unit/connectors/test_toolset_token_refresh_service.py` (139 tests) + `core/test_toolset_token_refresh.py` (2185L) GREEN in battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "ToolsetTokenRefreshService schedule lock cooldown", limit: 3 });
```
**Verdict:** Adopt all five hardenings as a checklist when porting any config-keyed refresher; adapt lock primitives/cooldown magnitude.
