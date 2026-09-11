<!-- capsule-v2 -->
|# Connector resilience policy — how do you give every connector (HTTP *and* vendor-SDK) one shared rate-limit + backoff-gate + retry budget without letting one 429 become N concurrent 429s?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** What is the minimal shared object that makes a fan-out of calls to one upstream account pace itself, absorb a throttle as ONE pause, and retry transient failures — when only some callers ride an httpx transport and the rest call vendor SDKs an interceptor can't see?

## One policy per connector instance; gate arms a deadline every caller waits behind
**Path/Symbol:** `backend/python/app/sources/client/resilience.py:ResiliencePolicy` (whole file, L1–291); HTTP twin `app/sources/client/http/http_resilient_transport.py` consumes it transport-side; SDK call sites use `.guard()`/`.run()` directly.
**Signature:** `ResiliencePolicy(*, rate_limit=None, max_retries=0, base_delay=1.0, max_delay=60.0, name, logger)` + `from_config(config) -> Self|None`; methods `acquire()`, `guard()` (async CM), `backoff(attempt, retry_after) -> float`, `note_retry(attempt, retry_after)`, `pause(seconds)`, `run(op, *, label) -> T`.
**Data Shape:** `_limiters: WeakKeyDictionary[loop, AsyncLimiter]` under a threading.Lock (double-checked per-loop construction — aiolimiter binds to its first loop); `_resume_at: float` monotonic gate deadline; module tuple `RETRYABLE_NETWORK_ERRORS = (TimeoutException, ConnectError, ReadError, WriteError, RemoteProtocolError)`.

### Decisive source
```python
async def acquire(self):                      # wait out backoff, take a token
    limiter = self._limiter()
    while True:
        await self._wait_for_gate()
        if limiter is None: return
        await limiter.acquire()
        # waiting in the token queue can outlast the pause that armed
        # meanwhile — checking ONLY before the queue would drain every
        # already-queued caller straight into a throttled API (one 429
        # becomes one PER QUEUED REQUEST). Loop instead:
        if not self._gate_is_closed(): return

def pause(self, seconds):
    ...
    self._resume_at = max(self._resume_at, now + min(seconds, self.max_delay))
    # max(), never overwrite: a long Retry-After is not undone by a later,
    # shorter backoff landing on the same connector

def backoff(self, attempt, retry_after=None):
    if retry_after is not None:               # numeric seconds only;
        spread = random.uniform(0, self.base_delay * _GATE_WAKE_JITTER)  # .25
        return min(retry_after, self.max_delay) + spread   # ADDED, never
        # subtracted: coming back early just earns another 429; the spread
        # de-syncs requests throttled in the same instant
    ceiling = min(self.max_delay, self.base_delay * 2**attempt)
    return random.uniform(0, ceiling)          # exponential w/ FULL jitter
```

**Flow:** `from_config` returns None for unconfigured/disabled (`enabled: False`) so "no resilience" is representable WITHOUT a null object that silently rate limits → each call awaits `acquire()` (gate → token → RE-CHECK gate after queueing) → on retryable failure the SDK path calls `note_retry` which computes the delay AND arms the gate so sibling callers hold back too → HTTP path gets identical behavior from the resilient transport hooking the same policy.
**Invariant:** (1) Scope is ONE policy per connector INSTANCE — two instances on the same account get independent budgets, and with `CONNECTOR_UVICORN_WORKERS > 1` the effective rate multiplies by worker count (per-process limiter, documented at L10–13). (2) Sub-1/s budgets must be spelled `AsyncLimiter(1, 1/rate)` not `AsyncLimiter(rate, 1)` — aiolimiter refuses `acquire(1)` when max_rate < 1 (test-pinned :59). (3) Closed loops are evicted when adding new ones because each AsyncLimiter strongly references its own weak key and would otherwise leak (:92 test). (4) Gate wake jitter `_GATE_WAKE_JITTER = 0.25 × base_delay`: waiters released together would hit upstream on the same tick. (5) Only NUMERIC Retry-After reaches backoff — HTTP-date parses as None and falls through to exponential (Notion sends seconds); negative seconds ⇒ None. (6) Validation ladder at construction rejects bool-as-int max_retries, max_delay < base_delay, non-positive rate_limit — loud, before any network happens.

**Probe:** `backend/python/tests/unit/sources/client/test_resilience.py` :18–296 — queued-callers-don't-drain-into-a-pause :129, pause-never-shortens :160, pause-capped-at-max-delay :171, cross-connector isolation :181, retry-after-wins-and-capped :196, jitter-spreads-simultaneous-throttles :202, http-date-fallback :207, no-retry-on-non-retryable-status :270, parse_retry_after case/negative/date matrix :287–295.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --query "ResiliencePolicy" --detail ids
```

## Verdict
Adopt the shape verbatim for any multi-source crawler/connector fleet: per-instance budget + monotonic max()-armed backoff gate + re-check-after-token-queue acquire loop + full-jitter capped exponential with additive Retry-After spread. Adapt the retryable-error set and config keys. Omit nothing — every branch above is test-pinned upstream. Coverage caveat: none material; dedicated suite covers all branches incl. the queue-drain race.
**Composition boundary vs `circuit-breaker-halfopen-probe`:** the breaker (base_client layer) is a per-ENDPOINT failure-state machine that STOPS calling an unhealthy upstream and recovers through a health-check probe; this policy is a per-CONNECTOR BUDGET that keeps calling but paces/throttles/retries. They stack — breaker decides WHETHER, policy decides HOW FAST — and a porter collapsing them loses either the fast-fail or the pacing.
