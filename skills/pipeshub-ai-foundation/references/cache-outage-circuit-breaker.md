<!-- capsule-v2 -->
|# Cache outage circuit-breaker — how does a dead Redis cost one timeout instead of three per search?

## Any operation error trips a 30s monotonic backoff; `enabled` consults it; create NEVER raises (failure ⇒ disabled cache)
**Path/Symbol:** `backend/python/app/services/cache/accessible_records_cache.py`: `OP_TIMEOUT_SECONDS=2.0` :77, `DOWN_BACKOFF_SECONDS=30.0` :78, `create()` :102–131 ("Never raises — a failure yields a disabled cache"), `enabled` property :133–138 (`time.monotonic() >= self._down_until`), `_mark_down` :287–295 (logs ONLY on first trip), env kill-switch `_cache_enabled_from_env` :55–57 (absent ⇒ ON; {"0","off","false","no"} ⇒ OFF).
**Signature:** `def _mark_down(self, op: str, error: Exception) -> None`; `@classmethod async def create(cls, logger, config_service) -> "AccessibleRecordsCache"`.
**Data Shape:** `_down_until: float` monotonic deadline; Redis client built with `socket_timeout=socket_connect_timeout=OP_TIMEOUT_SECONDS` and pinged at startup; TTL from env `PIPESHUB_ACCESSIBLE_RECORDS_CACHE_TTL` (`max(int(raw),1)`, ValueError ⇒ default 300).

### Decisive source
```python
@property
def enabled(self) -> bool:
    """False while disabled, unconfigured, or inside the post-failure backoff."""
    if not self._enabled:
        return False
    return time.monotonic() >= self._down_until

def _mark_down(self, op, error):
    first = time.monotonic() >= self._down_until   # log once per outage window
    self._down_until = time.monotonic() + self.DOWN_BACKOFF_SECONDS
    if first:
        self.logger.warning("Accessible-records cache %s failed (%s); bypassing cache for %ss", ...)
```

**Flow:** any of read/write/delete raising ⇒ `_mark_down(op, e)` + graceful fallback (read returns None ⇒ caller computes live; delete swallows) ⇒ subsequent calls skip Redis ENTIRELY until the backoff expires. Invalidation failures are swallowed by design — "dropping a cache entry must never fail a sync, a delete, or the indexing pipeline" (TTL is the staleness backstop).
**Invariant:** Redis can never break or STALL a search — worst case is one 2-second timeout per outage window, not per call. Loader exceptions propagate UNCHANGED (the cache adds no error wrapping around the authority). `close()` swaps the client out BEFORE awaiting aclose and is idempotent.
**Probe:** `backend/python/tests/unit/services/cache/test_accessible_records_cache.py::TestOutageCost::test_one_redis_op_per_call_when_down` (:324, asserts `dead.ops == ["get"]` EXACTLY) + `::test_breaker_still_skips_redis_on_later_calls` (:335); `TestKillSwitch::test_create_honours_the_env_kill_switch` (:366, config must NOT even be consulted); `TestRedisDown::test_loader_exceptions_propagate_unchanged` (:428).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "_mark_down DOWN_BACKOFF AccessibleRecordsCache create", limit: 10 });
```

## Verdict
Adopt monotonic-deadline breaker with first-failure logging, never-raising construction, env kill-switch semantics (default-on), and unchanged loader exception propagation; adapt timeouts/backoff constants; omit the ConfigurationService plumbing for your host's config layer. Direct tests ship upstream across all branches.
