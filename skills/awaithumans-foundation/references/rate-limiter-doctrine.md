<!-- capsule-v2 -->
# Sliding-Window Rate Limiter — how do you cap brute force without locking out victims?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What is the minimal correct in-process rate limiter for unauthenticated login/setup endpoints — and which "features" must it NOT have?

## Counter-per-key with monotonic trim, no bans by design
**Path/Symbol:** `packages/python/awaithumans/server/core/rate_limit.py` — `RateLimiter` (:37–86), module singletons (:96–103), `client_ip` (:106–122).
**Signature:** `RateLimiter(*, limit: int, window_seconds: float)` (raises ValueError on non-positive); `check(key) -> bool`; `reset(key) -> None`.
**Data Shape:** `defaultdict(list)` of monotonic timestamps per key; `threading.Lock` held ONLY over dict mutation (no I/O inside); singletons LOGIN_PER_IP 10/300s, LOGIN_PER_EMAIL 20/300s, SETUP_PER_IP 30/300s.

### Decisive source
```python
now = time.monotonic()
cutoff = now - self.window
with self._lock:
    hits = self._hits[key]
    # In-place trim — keeps memory bounded by sum of active
    # keys' window-counts rather than ever-growing history.
    i = 0
    for t in hits:
        if t > cutoff: break
        i += 1
    if i: del hits[:i]
    if len(hits) >= self.limit:
        return False            # do NOT bump on rejection
    hits.append(now)
    return True
```

**Flow:** `check()` = the only side-effecting call; False ⇒ caller sends 429 and must NOT retry the bump. `reset(key)` fires on successful login so typo history doesn't throttle a legit user.
**Invariant:** NO lockouts/bans — module docstring: "lock the account after N failures lets an attacker trivially deny service to a known target"; operators recover from rate limits by waiting, from lockouts only by admin intervention. No bans + sliding window + success-reset is the triple. `client_ip` falls back to `"unknown"` (shared bucket) rather than raising — raising would soft-DOS unknowns. In-process only: swap behind the same `check()` contract when going multi-worker.
**Probe:** `packages/python/tests/core/test_rate_limit.py` (:17 under-limit True, :24 at-limit False, :41 reset clears, :49/:68 monkeypatched window/partial expiry, :88 init validation).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "RateLimiter check reset client_ip", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt monotonic-time sliding counter, reject-without-bump semantics, success-path reset, thread-lock-only-over-mutation, and the no-lockout doctrine. Adapt limits/windows to your endpoint costs (argon2id ~100ms/verify justifies looser email gate). Omit Redis backing until you actually run multiple workers.
