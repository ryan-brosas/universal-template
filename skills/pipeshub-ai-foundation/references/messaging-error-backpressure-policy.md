<!-- capsule-v2 -->
|# Message failure policy — when a consumed message fails, what decides retry-vs-drop, and who pauses the consumer from claiming more work?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** For an event-driven indexing pipeline on Kafka/Redis Streams: which failure taxonomy routes a message to capped-retry vs immediate-ACK, and how does a downstream service's 429 stop the *reader* (not just the failing call) from admitting more work?

## Chain-walking TERMINAL/TRANSIENT classifier + per-service max()-deadline BackpressureCoordinator
**Path/Symbol:** `backend/python/app/services/messaging/error_classifier.py:MessageErrorClassifier` (whole file, L1–485); companion `app/services/messaging/backpressure.py:BackpressureCoordinator` (whole file, L1–105); consumers call these from `services/messaging/{kafka/consumer/indexing_consumer.py,redis_streams/indexing_consumer.py}`.
**Signature:** `classify_by_exception(exc) -> "terminal"|"transient"` (never raises), `classify_by_http_status(int) -> str`; coordinator `signal(service_name, retry_after)`, `is_paused()`, `pause_remaining() -> float`, `paused_services: frozenset[str]`.
**Data Shape:** two string constants (`MessageErrorType.TERMINAL/TRANSIENT`); status frozensets `_NON_RETRYABLE_HTTP_STATUSES = {400,401,403,404,413,422}` vs `_RETRYABLE_HTTP_STATUSES = {408,429,500,502,503,504,520}` plus open-ended `>= 500`; coordinator keeps `_pause_until: dict[service_name, monotonic_deadline]`.

### Decisive source
```python
# Classification ORDER is the invariant — every rule fires before the next:
root_exc = _get_root_cause(exc)          # walk __cause__/__context__ chain
chain = list(_iter_exception_chain(exc)) # cycle-guarded (visited id set)
# 0b. aiohttp transport errors scanned across the FULL CHAIN first —
#     ClientPayloadError may wrap TransferEncodingError whose .code is NOT
#     an HTTP status; type-truth beats incidental status attrs deeper in.
# 0c. ParsingClientError: code == PARSE_BACKPRESSURE ⇒ TRANSIENT (saturated,
#     not failed — never bubble to open a circuit breaker); every OTHER
#     ParseErrorCode ⇒ TERMINAL.
# 0d. Terminal CONTENT types scanned across the full chain BEFORE HTTP
#     status extraction: a wrapped DocumentProcessingError must beat an
#     ApiCallError carrying status 500.
# then: _extract_status_code(root_exc) → status ladder; then root-type
# checks (json/pydantic/subprocess/FileNotFound/content-errors=TERMINAL;
# timeout/connection/OSError/openai-rate-limit/httpx-transport=TRANSIENT;
# AWS credentials=TERMINAL, boto ClientError=status-or-TRANSIENT;
# other IndexingError=TRANSIENT); default TRANSIENT (safer to retry than
# to drop).

def signal(self, service_name, retry_after):
    if retry_after <= 0: return          # non-positive is a no-op
    until = self._clock() + retry_after
    if until > self._pause_until.get(service_name, 0.0):
        self._pause_until[service_name] = until   # extend, NEVER shorten

def pause_remaining(self):               # max over ALL signalled services;
    ...expired entries pruned here...    # resume only when the LAST
    return max(0.0, max(...))            # saturated service recovers
```

**Flow:** handler exception → `classify_by_exception` → TRANSIENT ⇒ `increment_retry_and_check` capped redelivery; TERMINAL ⇒ ACK/dead-letter immediately → IN BOTH CASES, if the failure was a downstream 429 the service client calls `coordinator.signal(name, retry_after)` (BaseServiceClient already retried on its own bounded schedule) and the consumer's poll loop checks `is_paused()` BEFORE claiming the next batch — leaving messages on the broker instead of growing MAX_PENDING_INDEXING_TASKS worth of stuck records.
**Invariant:** (1) Classification is TYPE/STATUS-based ONLY — never database state; processing failures are TERMINAL because retrying reproduces them. (2) `classify_by_exception` wraps its impl in try/except returning TRANSIENT — the classifier itself must never raise, consumers must always reach capped retry or ACK (:193 test pins an unexpected status shape). (3) Status extraction ladders through SIX vendor shapes (`status_code` attr, int-only `.status` — Google's string `"RESOURCE_EXHAUSTED"` must return None not TypeError :200/:208, 100–599-range `.code`, httpx `.response.status_code`, aiohttp isinstance-check ONLY (parser errors also carry `.code` — not HTTP), boto ResponseMetadata dict). (4) Coordinator deadlines are PER-SERVICE and max()-extended: a shorter later signal never shortens an active pause (:47), multiple services track independently and the consumer waits for whoever recovers LAST (:70). (5) Pruning expired entries inside `pause_remaining()` is load-bearing — `paused_services` would otherwise report stale names forever. (6) One coordinator per worker process/loop, single-event-loop like CircuitBreaker; the module-level `get_default_backpressure_coordinator()` exists ONLY because clients are constructed from too many DI sites to thread explicitly — tests override via `set_default_backpressure_coordinator(None)` (:100–113).
**Probe:** `tests/unit/services/messaging/test_error_classifier.py` :33–98 status matrix ×13, :114–169 extraction ladder incl. string-status traps, :179–221 wrapped/retryable/status-shape cases, :237+ JSON/pydantic/subprocess/content terminal cases; `tests/unit/services/messaging/test_backpressure.py` :18–77 (initial-clear, signal-pauses, no-op-non-positive, expiry, shorter-never-shortens, longer-extends, independent-max-wins), :100–113 singleton.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --query "MessageErrorClassifier BackpressureCoordinator" --detail ids
```

## Verdict
Adopt the ordered chain-walking classifier verbatim (transport-scan → structured-backpressure-code scan → terminal-content-chain-scan → status ladder → root-type ladder → TRANSIENT default) for any queue consumer that must distinguish "this message is poison" from "the world hiccuped"; adopt the per-service max-deadline coordinator for any fan-out caller whose READ loop can outrun a throttled dependency. Adapt the exception-type inventory to your stack. Omit nothing — ordering rules above are exactly what upstream tests pin; misordering any pair flips poison messages into infinite retries or transient outages into permanent drops.
