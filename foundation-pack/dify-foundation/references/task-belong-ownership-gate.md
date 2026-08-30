<!-- capsule-v2 -->
# task-belong-ownership-gate — Who is allowed to stop a running task?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** How do you prevent one user from cancelling another user's generation task?

## Redis ownership key written at queue creation, checked before stop-flag arming
**Path/Symbol:** `api/core/app/apps/base_app_queue_manager.py:AppQueueManager.__init__` (:39-50), `set_stop_flag` (:176-191); key builders `_generate_task_belong_cache_key` (:217-224) / `_generate_stopped_cache_key` (:226-233).
**Signature:** `set_stop_flag(cls, task_id, invoke_from, user_id)` (classmethod); `set_stop_flag_no_user_check(cls, task_id)` for system-initiated stops.
**Data Shape:** `task_belong:{task_id}` = `{account|end-user}-{user_id}` with 1800s TTL; `task_stopped:{task_id}` = 1 with 600s TTL; account vs end-user decided by `invoke_from.runs_as_account()`.

### Decisive source
```python
# __init__: claim ownership
user_prefix = "account" if self._invoke_from.runs_as_account() else "end-user"
self._task_belong_cache_key = AppQueueManager._generate_task_belong_cache_key(self._task_id)
redis_client.setex(self._task_belong_cache_key, 1800, f"{user_prefix}-{self._user_id}")

# set_stop_flag: verify ownership BEFORE arming the stopped flag
result: Any | None = redis_client.get(cls._generate_task_belong_cache_key(task_id))
if result is None:
    return
user_prefix = "account" if invoke_from in {InvokeFrom.EXPLORE, InvokeFrom.DEBUGGER} else "end-user"
if result.decode("utf-8") != f"{user_prefix}-{user_id}":
    return
stopped_cache_key = cls._generate_stopped_cache_key(task_id)
redis_client.setex(stopped_cache_key, 600, 1)
```

**Flow:** task starts → belong key written (30-min window covers any reasonable run) → stop request arrives → caller's prefix+id compared against stored owner → mismatch silently ignored → match arms the 10-min stopped flag the listen loop polls. On listener completion `_clear_task_belong_cache` removes the key.
**Invariant:** The comparison string embeds BOTH the identity kind (`account`/`end-user`) and id — an Account and an EndUser sharing a UUID could not collide because prefixes differ; a missing belong key means "not yours" (fail-closed: no flag). System paths that must bypass this use `set_stop_flag_no_user_check`, which routes through the coordinator's raw flag setter instead.
**Probe:** `grep -c '_generate_task_belong_cache_key' core/app/apps/base_app_queue_manager.py` → 3; direct test `tests/unit_tests/core/app/apps/test_base_app_queue_manager.py::TestBaseAppQueueManager` suite (executed green; 26 passed in its battery).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "AppQueueManager set_stop_flag invoke_from EXPLORE DEBUGGER account prefix", limit: 10 });
```

## Verdict
Adopt the ownership-claim/verify pair as the authorization shape for task cancellation. Adapt key names, TTLs, and the identity-kind enumeration to your auth model. Omit the EXPLORE/DEBUGGER special-casing unless you have equivalent console surfaces.
