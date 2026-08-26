<!-- capsule-v2 -->

# Transaction-keyed caching seam — How does a task decide its transaction key from cache_policy vs result_storage_key, and what isolation does SERIALIZABLE require?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** Where is the single point where cache policies become transaction keys, and how must failures degrade?

## compute_transaction_key: policy key or formatted storage key, exceptions → None

**Path/Symbol:** `src/prefect/task_engine.py:BaseTaskRunEngine.compute_transaction_key (271-297)` + `transaction_context (963-988)` (async twin `1594-1618`); policy base `src/prefect/cache_policies.py:CachePolicy.compute_key (103-110)`.

**Signature:** `compute_transaction_key() -> Optional[str]`; `transaction_context() -> Generator[Transaction, None, None]` wiring key/store/overwrite/logger/write_on_commit/isolation_level into `transaction(...)`.

**Data Shape:** Key precedence: CachePolicy instance ⇒ `policy.compute_key(task_ctx, inputs, flow_parameters)`; else `task.result_storage_key` ⇒ `_format_user_supplied_storage_key(...)`; else None (no persistence). Overwrite flag comes from repurposed `refresh_cache` task field or `PREFECT_TASKS_REFRESH_CACHE` setting. Isolation level read off the policy (`policy.isolation_level`) else inherited/default READ_COMMITTED.

### Decisive source
```python
try:
    if not task_run_context:
        raise ValueError("Task run context is not set")
    key = self.task.cache_policy.compute_key(
        task_ctx=task_run_context,
        inputs=self.parameters or {},
        flow_parameters=parameters or {},
    )
except Exception:
    self.logger.exception(
        "Error encountered when computing cache key - result will not be persisted.",
    )
    key = None
```

**Flow:** engine enters transaction_context → compute key (any policy exception logs + degrades to key=None ⇒ transaction runs unkeyed, never crashes the task) → open txn with store=get_result_store(), overwrite from refresh_cache, write_on_commit=should_persist_result(), isolation from policy → begin(): SERIALIZABLE demands store lock capability — unsupported configuration raises ConfigurationError BEFORE any user code (`store.supports_isolation_level`) → committed-at-begin acts as cache hit (see transaction-commit-tree).

**Invariant:** (1) Key-computation failure degrades to "no caching", NEVER to "reuse stale key" or an exception — porting this as a raise turns every malformed policy input into a task failure. (2) Flow parameters feed policy computation only from FlowRunContext (None outside flows). (3) SERIALIZABLE without a lock file directory/lock manager is a CONFIGURATION error surfaced eagerly, not a runtime race discovered mid-run.

**Probe:** `grep -c 'supports_isolation_level' src/prefect/transactions.py` → 1; `grep -cF 'key = None' src/prefect/task_engine.py` → 2 (sync+async degrade arms). Direct tests: `tests/test_tasks.py:2243 TestTaskCaching.test_cache_policy_serializable_isolation_level_with_no_manager` (ConfigurationError path) and `tests/test_task_engine.py:599 test_task_runs_respect_cache_key`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "compute_transaction_key cache policy", "limit": 4}'
```

## Verdict
Adopt policy→key→transaction plumbing with fail-open key computation for any result-cache layer; adapt policy DSL; omit Prefect's specific CachePolicy subclasses (Inputs/Runs/AllParameters etc.).
