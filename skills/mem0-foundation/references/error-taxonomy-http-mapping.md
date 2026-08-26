<!-- capsule-v2 -->
# Structured error taxonomy — how do HTTP failures become typed exceptions a porter can dispatch on?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mem0`. **Question:** how does one exception base turn every API failure into a machine-actionable object with retry/quota/debug context — and what must a port preserve so callers can branch on type?

## Connected graph-selected seam
**Path/Symbol:** `mem0/exceptions.py`: `MemoryError` (:34-90), `HTTP_STATUS_TO_EXCEPTION` (:407-421), `create_exception_from_response` (:424-485); consumer `mem0/client/utils.py` `_handle_http_error` (:26-65); OSS raise sites `main.py` :969/:2630 (`LLMError(f"LLM extraction failed: {e}") from e`) and :392/:832/:2498 (`Mem0ValidationError`). Direct test `tests/test_client_utils.py` (:50-75).
**Signature:** `MemoryError(message, error_code, details=None, suggestion=None, debug_info=None)`; `create_exception_from_response(status_code, response_text, error_code=None, details=None, debug_info=None) -> MemoryError`.
**Data Shape:** five-field envelope: `message` (human text), `error_code` ("RATE_001"/"NET_CONNECT"), `details` (server JSON body), `suggestion` (user-facing fix), `debug_info` (status/url/method/retry_after/ratelimit headers). 13 concrete subclasses; three tiers: platform-generic (Authentication/RateLimit/Validation/MemoryNotFound/Network/Configuration/QuotaExceeded/Corruption/VectorSearch/Cache), OSS-constructor twins (VectorStoreError "VECTOR_001", EmbeddingError "EMBED_001", LLMError "LLM_001", DatabaseError "DB_001", DependencyError "DEPS_001").

### Decisive source
```python
HTTP_STATUS_TO_EXCEPTION = {
    400: ValidationError,   401: AuthenticationError, 403: AuthenticationError,
    404: MemoryNotFoundError, 408: NetworkError,     409: ValidationError,
    413: MemoryQuotaExceededError, 422: ValidationError,
    429: RateLimitError,    500: MemoryError,
    502: NetworkError, 503: NetworkError, 504: NetworkError,
}
exception_class = HTTP_STATUS_TO_EXCEPTION.get(status_code, MemoryError)  # unknown → BASE, never KeyError
if not error_code:
    error_code = f"HTTP_{status_code}"
```
```python
# client/utils.py — header intelligence folded into debug_info before the raise
if e.response.status_code == 429:
    retry_after = e.response.headers.get("Retry-After")          # int() parse, junk tolerated → skipped
    if retry_after:
        try: debug_info["retry_after"] = int(retry_after)
        except ValueError: pass
    for header in ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]:
        ...debug_info[header.lower().replace("-", "_")] = value  # x_ratelimit_limit / _remaining / _reset
# request-layer taxonomy: TimeoutException→NET_TIMEOUT, ConnectError→NET_CONNECT, else NET_GENERIC
```

**Flow:** transport raises `httpx.HTTPStatusError`/`RequestError` → `api_error_handler` (inspect.iscoroutinefunction picks async wrapper; @wraps preserves it — test-pinned) → `_handle_http_error` extracts response text + JSON-body `detail` + rate-limit headers → `create_exception_from_response` maps status via table (fallback = base `MemoryError`, code defaults to `HTTP_<status>`, suggestion from per-status copy table) → caller branches on TYPE and reads `debug_info["retry_after"]` for backoff. Request-layer errors skip the status table entirely: httpx.TimeoutException/ConnectError/generic map to the three NET_* codes.
**Invariant:** the mapping is TABLE-driven with an explicit base-class fallback — never a KeyError path; 500 deliberately maps to base `MemoryError` while all 3 gateway codes map to `NetworkError`; `raise ... from e` at OSS LLM extraction sites keeps the transport chain; docstring-only references in client/project.py mean the taxonomy lives in utils+exceptions ONLY — a porter who skips `_handle_http_error`'s header-intelligence loses retry_after silently.
**Probe:** `tests/test_client_utils.py::test_sync_http_error_raises_structured_exception` (401→AuthenticationError), `::test_async_http_error_raises_structured_exception` (429→RateLimitError), `::test_async_connect_error_raises_network_error` (asserts `.error_code == "NET_CONNECT"`); sync/async flag preservation tests (:20-35).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "create_exception_from_response HTTP_STATUS_TO_EXCEPTION api_error_handler retry_after", limit: 10, fields: ["signature", "name", "file"] });
```
(resolved: mnt-hdd-utopia-inspo-memory-mem0.mem0.exceptions.create_exception_from_response Function mem0/exceptions.py 424-485)

## Verdict
Adopt the status-table + base-fallback shape and the 5-field envelope verbatim; adapt subclass names/codes to your domain; omit the platform-tier classes if your port is OSS-only (keep the OSS constructor-default tier).
