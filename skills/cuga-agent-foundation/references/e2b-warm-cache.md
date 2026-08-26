<!-- capsule-v2 -->
# E2B warm-sandbox cache — why idle-TTL instead of creation-TTL, and why recover from stale errors reactively instead of health-checking proactively?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Remote sandboxes cost seconds to boot and money per second alive — how do you keep one warm sandbox per conversation thread without leaks, and what happens when the cloud kills it mid-task?

## Thread-keyed singleton cache + last-used expiry + string-matched stale recovery
**Path/Symbol:** `src/cuga/backend/tools_env/code_sandbox/e2b_sandbox.py` — entry `SandboxCacheEntry` :41-72 (`mark_used` bumps `last_used`+`use_count`; `is_expired_idle` measures from LAST USED not created; `is_expired_age` disabled when max_age==0); singleton `E2BSandboxCache` :87-414 (`__new__` pattern :96-101, modes `'per-session'`|`'single'`, `_idle_ttl=600`, `_max_age=86400`, `_ttl_buffer=60`); `get_or_create` :138-176 (lazy cleanup of THE REQUESTED thread only); `_create_sandbox` :191-266 (`timeout=idle_ttl+buffer`, 2 attempts, `sleep(0.5*(attempt+1))` backoff, periodic cleanup on create or every Nth create); `_lazy_cleanup` :272-297 + `_periodic_cleanup_all` :299-318 (ALL checks local timestamps — zero E2B API calls during cleanup); recovery `execute_with_recovery` :336-366 + `_is_sandbox_stale_error` :368-388 (10 lowercase substring indicators: `"sandbox not found"`, `"sandbox expired"`, `"sandbox killed"`, `"connection timeout/refused"`, `"session expired/not found"`, etc. — on match: remove+recreate+retry ONCE); lazy settings-configured global `get_sandbox_cache` :417-441.
**Signature:** `execute_with_recovery(thread_id, code, **kwargs) -> run_code result`; `get_or_create(thread_id) -> Sandbox`.
**Data Shape:** `Dict[thread_id -> SandboxCacheEntry{sandbox, created_at, last_used, use_count}]`; `'single'` mode keys everything under constant `GLOBAL_THREAD_ID = "__global__"` (:35) for shared-state benchmarks.

### Decisive source
```python
# e2b_sandbox.py:53-56 — the "KEY FIX" comment marks the design decision
def is_expired_idle(self, idle_ttl: int) -> bool:
    """Check if expired based on idle time - KEY FIX."""
    idle_time = time.time() - self.last_used  # Use last_used, not created_at
    return idle_time > idle_ttl
```
Creation-based TTL evicts LONG-RUNNING ACTIVE conversations; idle-based keeps a hot thread's sandbox warm indefinitely while sweeping genuinely abandoned ones. The class docstring names the full philosophy: *"Idle-based TTL … Local timestamp checks (no E2B calls during cleanup) … Reactive error handling instead of proactive health checks"* — every cleanup decision reads local clocks only; cloud truth is consulted only when an actual execution fails.
```python
# e2b_sandbox.py:347-360 — reactive replacement, one retry
if self._is_sandbox_stale_error(e):
    logger.info(f"Sandbox {thread_id} is stale/expired, replacing and retrying... (error: {e})")
    self._remove_sandbox(thread_id)
    sandbox = self.get_or_create(thread_id)
    result = sandbox.run_code(code, **kwargs)
    return result
else:
    raise
```
**Flow:** execute → get_or_create (local TTL check → reuse+mark_used OR create with buffered timeout) → run → stale-looking error? kill+recreate+retry once : re-raise. Create path optionally sweeps ALL threads on create (or every Nth creation) to prevent cross-thread leak accumulation.
**Invariant:** The TTL buffer exists because the CLOUD-side sandbox timeout must outlive YOUR idle policy — if your idle_ttl exceeded E2B's server-side timeout you'd hand out dead sandboxes that pass local checks. Never trust a cached sandbox to be alive; trust the error strings. Removal must `kill()` then delete under try/finally so map entries never outlive their sandbox object.
**Probe:** coverage caveat — this module has NO direct test file in-repo (the sibling `code_sandbox/tests/test_sandbox.py` covers only `run_local`); behavior pins are the source ranges above plus live-gated executor tests elsewhere. Verify by reading :41-72 and :336-388 before porting.
**Retrieve:** `await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "E2BSandboxCache SandboxCacheEntry execute_with_recovery _is_sandbox_stale_error get_or_create", limit: 10 });`

## Verdict
Adopt idle-based expiry keyed per thread, local-clock-only cleanup, buffered remote timeouts, and single-retry stale-error recovery. Adapt indicator strings to your provider's error vocabulary. Omit 'single'/global mode unless you need benchmark-shared state.
