<!-- capsule-v2 -->
# Token bucket rate limiter — one DB table, many budgets, and an S3 circuit breaker for free

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How does a stateless-web multi-node app rate-limit logins, TOTP guesses, and outbound integrations without Redis — and how does the same primitive become a failure-rate circuit breaker?

## TokenBucket.authorize + s3_is_healthy
**Path/Symbol:** `hc/api/models.py:TokenBucket.authorize` (:1439-1462), `s3_is_healthy` (:1567-1578), `record_s3_get_object_error` (:1580-1584), per-surface wrappers `authorize_login_email` (:1478-1490), `authorize_totp_code` (:1558-1565), `Ping.get_body_bytes` (:749-764).
**Signature:** `authorize(value: str, capacity: int, refill_time_secs: int, force: bool = False) -> bool`; `s3_is_healthy() -> bool`.
**Data Shape:** Columns `value: str (unique)`, `tokens: float default 1.0`, `updated: datetime`. Key namespaces: `auth-ip-<addr>`, `em-<sha1(email+SECRET_KEY)>`, `pw-<hash>`, `invite-<id>`, `sudo-<id>`, `totp-<id>`, `totpc-<id>-<code>`, `tg-/signal-/po-/ntfy-<hash>`, sentinel row `s3_get_object_error`.

### Decisive source
```python
# hc/api/models.py — top-up-on-read, debit-on-write
obj, created = TokenBucket.objects.get_or_create(value=value)
if not created:
    duration_secs = (frozen_now - obj.updated).total_seconds()
    obj.tokens = min(1.0, obj.tokens + duration_secs / refill_time_secs)
obj.tokens -= 1.0 / capacity
if obj.tokens < 0 and not force:
    return False            # denied: nothing persisted → free retry later
obj.updated = frozen_now
obj.save()                  # upstream comments the race: "OK to be a little inexact"

# The twist: the SAME table is an outage circuit breaker.
def s3_is_healthy():
    """Return True if fewer than 3 GetObject errors in the last minute."""
    try:
        obj = TokenBucket.objects.get(value="s3_get_object_error")
    except TokenBucket.DoesNotExist:
        return True
    duration_secs = (now() - obj.updated).total_seconds()
    tokens = min(1.0, obj.tokens + duration_secs / 60)
    return tokens >= 1.0 / 3

# Ping.get_body_bytes gates S3 reads on it:
if not TokenBucket.s3_is_healthy():
    raise self.GetBodyError()
```

**Flow:** authorize(): get-or-create row → top-up proportional to elapsed time (capped at 1.0) → debit 1/capacity → deny-and-discard if negative (unless force) else persist. Wrappers pre-hash PII with SECRET_KEY so the shared table never stores raw emails. Circuit path: every GetObject failure records via `authorize("s3_get_object_error", 3, 60, force=True)`; readers compute would-be tokens and fail fast with GetBodyError→HTTP 503 when under ⅓.
**Invariant:** Tokens cap at 1.0 (a burst equals capacity, not capacity×idle-time); denial writes NOTHING so hammering doesn't resurrect the row or skew accounting; email keys must be normalized BEFORE hashing (strip dots/plus-alias — test_it_normalizes_email proves alice+alias ≡ a.li.ce). TOTP uses TWO buckets: attempts-per-day (`totp-`) AND one-use-per-90s per code (`totpc-`, capacity=1) because pyotp's window means a stolen verified code replays. The circuit-breaker reuse works only because record_s3_get_object_error passes force=True — recording an error after the fact must succeed even at negative tokens.
**Probe:** `hc/api/tests/test_tokenbucket.py::test_it_works` (tokens==0.9 after one em-debit), `test_it_tops_up` (30 idle minutes → 0.5), `test_it_normalizes_email`, `test_s3_get_object_healthy_works` (threshold ⅓), `hc/accounts/tests/test_login_totp.py::test_it_rejects_used_code`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "tokenbucket authorize tokens refill", limit: 10 });
```
Resolves line-exact: TokenBucket.authorize :1440-1462.

## Verdict
Adopt the single-table token-bucket with hashed key namespaces, deny-writes-nothing semantics, and the error-recorder-as-circuit-breaker pattern. Adapt capacities/refill constants to your traffic; swap the get_or_create+save for Redis INCR/EXPIRE when you actually have Redis (the contract, not the storage, is the portable part). Omit per-wrapper key formats; keep the "PII never hits the bucket table" rule.
