<!-- capsule-v2 -->
# OpenSandboxExecutor — per-thread remote sandbox cache with double-checked async locks and config-fingerprint invalidation

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Remote sandboxes are expensive to create and skills/config can change between turns. How do you cache one sandbox per thread so concurrent tool calls don't double-provision, while a stale-skills config change invalidates the cached instance instead of silently serving old state?

## The caching executor
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/opensandbox/opensandbox_executor.py` (`_sandboxes` dict :97, `_locks` :103-113, `_get_or_create_interpreter` :125-185, `release_sandbox` :242-248, stale-config warning :301).
**Signature:** `_get_or_create_interpreter(thread_id=None) -> interpreter`; `release_sandbox(thread_id=None) -> None`.
**Data Shape:** class-level dicts keyed by thread-derived key: `_sandboxes[key] = interpreter`, `_locks[key] = asyncio.Lock`.

### Decisive source
```python
# opensandbox_executor.py:110-144 (shape) — lock-per-key + re-check inside the lock
def _lock_for(self, key):
    if key not in self._locks:
        self._locks[key] = asyncio.Lock()
    return self._locks[key]

async def _get_or_create_interpreter(self, thread_id=None):
    key = ...
    async with self._lock_for(key):        # serialize creators per thread
        existing = self._sandboxes.get(key)
        if existing is not None:           # double-checked: someone may have
            ...                            # created while we awaited the lock
            return existing
        interpreter = await create(...)    # only ONE creator runs create()
        self._sandboxes[key] = interpreter

# :301 — config drift detected against the ACTIVE sandbox's fingerprint
if key in self._sandboxes and active is not None and requested != active:
    logger.warning("[OpenSandbox] stale skills config ...")   # warn, don't silently reuse
```

**Flow:** every tool call resolves the thread key → acquires that key's asyncio.Lock → re-checks the cache INSIDE the lock (the outer check alone races two first-calls) → creates/uploads once → caches even when upload fails (a broken-upload sandbox is still an instance; retry happens at tool level, test-pinned). `release_sandbox` pops both the interpreter and its lock so a released thread doesn't retain a hot lock object. A skills-config fingerprint comparison against the live instance logs a stale-config warning without force-recreating.
**Invariant:** creation must be idempotent under concurrency — exactly one `create()` per key even when N coroutines race (pinned by test), and each distinct thread gets its OWN sandbox (never shared keys across threads). Cache survives upload failure by design so subsequent tool calls reuse the session rather than re-provisioning.

**Probe:** direct tests `tests/unit/test_opensandbox_executor.py::test_concurrent_creation_calls_sandbox_create_exactly_once` (:110), `::test_different_thread_ids_each_get_own_sandbox` (:141), `::test_sandbox_cached_even_when_upload_fails` (:187), `::test_upload_failure_does_not_prevent_subsequent_tool_use` (:226), `::test_stale_skills_config_logs_warning` (:251), `::test_release_sandbox_clears_all_state` (:321).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "OpenSandboxExecutor _get_or_create_interpreter release_sandbox _sandboxes", limit: 10 });
```

## Verdict
Adopt per-key double-checked locking over expensive session resources (create exactly once under concurrency; release clears the lock too) and fingerprint-based staleness warning over silent reuse. Adapt provisioning calls and fingerprint inputs to your sandbox provider. Omit the skills-upload step unless you run skill flows.
