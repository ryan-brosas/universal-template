<!-- capsule-v2 -->
# Retry safety taxonomy — which failures may be retried, and what makes a retry safe?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** When is retrying a failed API write safe vs duplicating, and how are Retry-After headers honored without stalling the import?

## call_with_retries
**Path/Symbol:** `ingestion/src/zep_ingest/submitters/sequential.py:27` (`MAX_RETRY_WAIT_SECONDS = 60.0`), `:32` (`_UNSENT_TRANSPORT_ERRORS`), `:40` (`_retry_after_seconds`), `:62` (`_is_retryable`), `:69` (`call_with_retries`).
**Signature:** `call_with_retries(fn, *, max_retries=5, retry_server_errors=False) -> tuple[Any, SubmitError | None]` — returns `(result, None)` on success or `(None, last_error)`; NEVER raises.
**Data Shape:** `SubmitError = ApiError | httpx.TransportError`. Unsent-transport tuple = (ConnectError, ConnectTimeout, PoolTimeout, ProxyError).

### Decisive source
```python
def _is_retryable(error, *, retry_server_errors):
    if isinstance(error, httpx.TransportError):
        return isinstance(error, _UNSENT_TRANSPORT_ERRORS) or retry_server_errors
    return error.status_code == 429 or (retry_server_errors and (error.status_code or 0) >= 500)

# 429 safe to retry: the request was rejected BEFORE it could be processed.
# 5xx NOT retried by default: a non-idempotent write may have succeeded but its
# response was lost. Transport errors classified on the same axis: raised
# before the request went out → like 429; after (read timeout, dropped
# response) → like 5xx.
wait = _retry_after_seconds(error) if isinstance(error, ApiError) else None
if wait is None:
    wait = (2 ** (attempt - 1)) * (1 + random.random() * 0.25)
time.sleep(min(wait, MAX_RETRY_WAIT_SECONDS))
```

**Flow:** attempt fn → catch ApiError/TransportError → classify retryable → honor Retry-After (float seconds; HTTP-date parsed to delta; "nan"/non-finite treated as missing header; negative clamps to 0) else exponential backoff ×(1+U(0,.25)) jitter → cap every sleep at 60s ("a server is free to send Retry-After: 86400") → exhausted ⇒ return error to caller.
**Invariant:** The idempotency gate is the contract: only the caller who KNOWS the operation is idempotent passes `retry_server_errors=True` (batch.process does — re-processing a known batch cannot add items twice). A porter who retries 5xx graph.add blindly duplicates episodes whose responses were lost. Errors returned, never raised, so submit loops record-and-continue.
**Probe:** `grep -c 'def test' ingestion/tests/test_sequential_submitter.py` → 23 incl. `test_absurd_retry_after_is_capped`, `test_server_error_is_not_retried_without_idempotency`, `test_unsent_transport_error_is_retried`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "call_with_retries retry_after backoff transport", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-class retry taxonomy (429 / unsent-transport / post-send-transport≈5xx / other) + Retry-After parsing with cap + caller-established idempotency for server-error retries; adapt sleep caps to your SLA; omit Zep SDK-specific exception types.
