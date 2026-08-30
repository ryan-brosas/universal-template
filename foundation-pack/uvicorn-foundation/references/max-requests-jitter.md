<!-- capsule-v2 -->
# Max-requests jitter — why does each worker pick a private request limit at startup?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** How is `limit_max_requests` turned into a per-worker randomized budget, and when is it computed?

## cached_property draws the jitter once per Server instance
**Path/Symbol:** `uvicorn/server.py:Server.limit_max_requests` (:80–83), consumed in `Server.on_tick` (:262–281).
**Signature:** `@functools.cached_property def limit_max_requests(self) -> int | None`.
**Data Shape:** `config.limit_max_requests:int|None`, `config.limit_max_requests_jitter:int=0`; result memoized on the instance.

### Decisive source
```python
@functools.cached_property
def limit_max_requests(self) -> int | None:
    if self.config.limit_max_requests is None:
        return None
    return self.config.limit_max_requests + random.randint(0, self.config.limit_max_requests_jitter)
```
```python
# on_tick :272-277 — checked once per second against the SHARED counter
max_requests = self.limit_max_requests
if max_requests is not None and self.server_state.total_requests >= max_requests:
    logger.info("Maximum request limit of %d exceeded. Terminating process.", max_requests)
    return True
```

**Flow:** `Config(limit_max_requests=N, limit_max_requests_jitter=J)` → first `on_tick` touch computes the worker's private budget `N + uniform[0..J]` ONCE (cached_property never recomputes) → the 0.1s main-loop tick compares the shared `server_state.total_requests` counter (incremented by every protocol's `on_response_complete`) against it → tripping sets `should_exit` via the tick returning True → normal graceful shutdown ladder runs.
**Invariant:** The draw happens once per worker PROCESS (each Multiprocess child builds its own Server), which staggers restart times so N workers don't all recycle in the same second; re-drawing per request would destroy that property. The counter is shared across all connections of the process, not per-connection.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'limit_max_requests + random.randint' uvicorn/uvicorn/server.py"` → 1. Behavioral pin: `tests/test_server.py:test_limit_max_requests_jitter` (:153) — asserts the exit threshold lands inside `[N, N+J]`.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"maximum request limit exceeded terminating process jitter","limit":5,"detail":"ids"}` → resolves `tests.test_server.test_limit_max_requests_jitter` line-exact.
**Verdict:** Adopt the cached one-draw-per-worker pattern verbatim whenever porting self-recycling workers behind a shared socket. Adapt the distribution (uniform here). Omit the log phrasing.

