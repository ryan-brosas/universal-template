<!-- capsule-v2 -->
# Retry-After wait strategy — how should a retry backoff honor the server's own retry deadline?

**Source:** pydantic-ai Apache-2.0 @ `a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you parse HTTP `Retry-After` into a tenacity wait without a malformed header wrecking the backoff?

## retry-after-wait-ladder
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/retries.py:` `wait_retry_after` factory + inner `wait_func` (:514–590).
**Signature:** `wait_retry_after(fallback_strategy: Callable[[RetryCallState], float] | None = None, max_wait: float = 300) -> Callable[[RetryCallState], float]`; default fallback `wait_exponential(multiplier=1, max=60)`.
**Data Shape:** reads `state.outcome.exception()`; recognizes BOTH `httpx.HTTPStatusError | httpx2.HTTPStatusError` (union isinstance, legacy arm marked TODO(v3)).

### Decisive source
```python
def wait_func(state):
    exc = state.outcome.exception() if state.outcome else None
    if isinstance(exc, HTTPStatusError | httpx2.HTTPStatusError):
        retry_after = exc.response.headers.get('retry-after')
        if retry_after:
            try:
                wait_seconds = int(retry_after)          # format 1: integer seconds
                if wait_seconds >= 0:
                    return float(min(wait_seconds, max_wait))
            except ValueError:
                try:
                    retry_time = parsedate_to_datetime(retry_after)   # format 2: HTTP date
                    # asctime-date (RFC 9110 §5.6.7, e.g. `Sun Nov  6 08:49:37 2095`)
                    # carries NO timezone — pin it to UTC or the subtraction raises TypeError:
                    if retry_time.tzinfo is None:
                        retry_time = retry_time.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    wait_seconds = (retry_time - now).total_seconds()
                    if wait_seconds > 0:
                        return min(wait_seconds, max_wait)
                except (ValueError, TypeError, AssertionError):
                    pass                                   # date parse fails → fall through
    return fallback_strategy(state)
```

**Flow:** exception is a status error? → read header → try integer seconds FIRST (negative falls through!) → else parse as HTTP date via `email.utils.parsedate_to_datetime` → **naive datetimes pinned to UTC (#7711)** → delta vs UTC now → clamp to `max_wait` at BOTH branches → any failure degrades to the fallback strategy, never raises.
**Invariant:** five rules:
1. Seconds-parse precedes date-parse (`int('Wed, 21 Oct...')` raising ValueError IS the discriminator between the two legal formats).
2. Clamp EVERY returned wait to `max_wait` — a hostile/misconfigured server must not command a multi-hour sleep.
3. Negative seconds and past-dated headers are treated as "no usable hint" (fall through), not clamped to zero-sleep-and-hammer.
4. Total-failure path is the fallback strategy — the wait function itself never raises.
5. `parsedate_to_datetime` returns tz-AWARE datetimes for RFC-7231 IMF-fixdate but NAIVE ones for asctime (`Sun Nov  6 08:49:37 2095`); an aware-minus-naive subtraction raises `TypeError` and would silently degrade EVERY asctime header to the fallback — normalize naive results to UTC immediately after parsing (#7711). The except-clause must keep catching `TypeError` as the last-resort guard.
**Probe:** `tests/test_tenacity.py::TestWaitRetryAfter::test_retry_after_asctime_date_format` (:618–638; asserts the returned wait equals the true delta to a fixed UTC instant parsed from `.ctime()` — impossible if naive/aware mix) plus the ladder pins in `TestWaitRetryAfter` (:479+); mem0's independent `api_error_handler` (Retry-After int-parse + X-RateLimit intelligence) is the same seam family in another codebase. Both asctime + ladder tests EXECUTED GREEN in repo `.venv` this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "wait_retry_after RetryCallState parsedate_to_datetime max_wait fallback exponential", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-format ladder + double clamp + never-raise degradation verbatim for any client honoring Retry-After; adapt exception types and default fallback; nothing to omit.
