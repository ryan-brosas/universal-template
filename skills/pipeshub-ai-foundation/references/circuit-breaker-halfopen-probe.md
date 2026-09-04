<!-- capsule-v2 -->
# Half-open probe circuit breaker — how do you recover a failed downstream WITHOUT capping real requests at the cooldown?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** When the breaker's cooldown elapses, why must recovery probe with health_check() instead of letting one real request through — and how do stuck probes and client-side bugs stay out of the state machine?

## Probe-based HALF_OPEN with a single claimed slot and a 30s stuck-probe escape
**Path/Symbol:** `backend/python/app/services/base_client.py:CircuitBreaker.is_open/should_attempt_probe/record_success/record_failure/_reset_stuck_probe` (L78–218); retry driver `BaseServiceClient._request_with_retry` (L285–427).
**Signature:** `is_open -> bool` (property, may lazily repair); `should_attempt_probe() -> bool` (claims the slot); `record_success()/record_failure()`; `_request_with_retry(method, url, *, json=None, content=None, headers=None, files=None, data=None, operation="request") -> httpx.Response`.
**Data Shape:** States CLOSED/OPEN/HALF_OPEN; fields `failure_threshold=5`, `cooldown_seconds=30.0`, `_half_open_probe_in_flight`, `_half_open_probe_started_at`; transient set = `(500..599) − {501}` ∪ `{429}`.

### Decisive source
```python
# Docstring, the design core: "OPEN rejects all calls until cooldown_seconds
# elapse, then lets a SINGLE caller run a health_check() PROBE instead of a
# real workload request — a real request (e.g. a multi-minute document parse)
# would otherwise have to be capped at cooldown_seconds, aborting a
# legitimately slow-but-healthy call."
_PROBE_STUCK_TIMEOUT = 30.0   # claimed-but-never-reported probe can't wedge the
                              # breaker past its cooldown (health_check ~10s bounded)

def is_open(self):
    if self._state == HALF_OPEN:
        if self._probe_timed_out(now): self._reset_stuck_probe(now); return False
        return True
    if self._state != OPEN: return False
    if cooldown elapsed: return False        # probe MAY proceed; transition happens
    return True                              # in should_attempt_probe (no double-probe)

def should_attempt_probe(self):
    if not OPEN or cooldown not elapsed or self._half_open_probe_in_flight: return False
    self._state = HALF_OPEN; self._half_open_probe_in_flight = True; ...; return True

except httpx.RequestError as exc:
    # InvalidURL/UnsupportedProtocol/... are CLIENT-SIDE bugs, not downstream
    # unhealthiness — raise immediately WITHOUT retrying or counting against the
    # breaker "which would otherwise open on our own bug".
    raise ServiceCallError(...) from exc
```
Retry ladder: per-attempt transport tuple `(TimeoutError, httpx.TimeoutException, ConnectError, WriteError)` retries with `delay * 2**(attempt-1)`; any non-transient response records SUCCESS ("even a 4xx means it's reachable") and returns. Exhaustion raises exactly once with a summary WARNING: transport failure → `ServiceUnavailableError`; status failure → `ServiceCallError(status_code, details={"error_message"})`.

**Flow:** call entry first offers the probe slot (`should_attempt_probe` → `await health_check()` → success closes / failure re-opens for a FULL cooldown) → `is_open` short-circuits to `ServiceUnavailableError(503)` with no connection attempt and no retry sleeps (an outage must not tie up parsing/indexing concurrency slots) → normal attempts run inside ONE freshly-made client → transient statuses/errors consume attempts with exponential backoff → exhaustion emits a single summary warning + `record_failure`.
**Invariant:** (1) Recovery NEVER rides a workload request — half-open admits only the health-check probe, so long-but-healthy calls aren't capped by cooldown. (2) Exactly one probe per cooldown window: the slot flag plus the timed-out reset (`_opened_at = now - cooldown`) keep a cancelled probe from wedging the breaker open forever. (3) Client-side request errors bypass both retry AND the breaker — your own bug must not open someone else's circuit. (4) Any reachable response (even 4xx/501) counts as healthy. (5) Not thread-safe BY DESIGN: each client owns one breaker on a single worker-loop event loop — adding locks would be cargo cult.
**Probe:** `tests/unit/services/test_base_client.py` (353L): request_retries_on_503 :45 / _500 :71; exhausted→ServiceUnavailable :90; persistent_5xx→ServiceCallError :107; error_message_from_5xx_body :124; no_retry_on_4xx :154; **allows_only_one_half_open_probe** :177; recovery_probe_uses_health_check_not_real_request :203; slow_probe_longer_than_cooldown_still_closes :234; failed_probe_reopens_without_real_request :271; **client_side_error_bypasses_circuit_breaker** :297.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "CircuitBreaker should_attempt_probe _request_with_retry TRANSIENT_STATUS_CODES" --detail ids
```

## Verdict
Adopt probe-based half-open recovery with the single-slot claim + stuck-prove timeout, client-side-bug bypass, even-4xx-is-healthy rule, and open-circuit fail-fast before sleeps. Adapt thresholds/cooldowns and the transient set to host traffic. Omit the indexing-worker event-loop assumptions if the host runs multi-loop.
