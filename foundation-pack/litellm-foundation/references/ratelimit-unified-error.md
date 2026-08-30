<!-- capsule-v2 -->
# ratelimit-unified-error — How does one exception type carry vendor 429s AND proxy-side limits without breaking `except RateLimitError:` handlers?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** What must a unified rate-limit error carry (category, rate_limit_type, headers, detail) and which header-handling invariant is security-load-bearing?

## Connected graph-selected seam
**Path/Symbol:** `litellm/exceptions.py:RateLimitError` (:413-500) + `RateLimitErrorCategory` enum (:21).
**Signature:** `RateLimitError(message, llm_provider, model, response=None, litellm_debug_info=None, max_retries=None, num_retries=None, category=RateLimitErrorCategory.VENDOR_RATE_LIMIT, rate_limit_type=None, headers=None, detail=None)`.
**Data Shape:** Hard-codes `status_code = 429`, `code = "429"`, `type = "throttling_error"`; synthesizes its own `httpx.Response` (never trusts the caller's). Carries `category` (source of the limit: vendor vs proxy-side limiter), `rate_limit_type` (dimension exceeded: requests/tokens/parallel/budget/max-iterations; None when unclassified), `headers` (proxy-supplied retry-after etc.), `detail` (mirrors FastAPI HTTPException so one instance serializes through both ProxyException and HTTPException paths). `__str__` appends "LiteLLM Retried: N times" when retry counters are set.

### Decisive source
```python
        # IMPORTANT: we deliberately do NOT auto-populate self.headers from
        # response.headers when only `response` is provided. A vendor 429 can
        # set arbitrary response headers (Set-Cookie, CORS overrides, …); if
        # those leaked into e.headers and a downstream proxy serializer
        # forwarded them to the client, a malicious upstream could inject
        # browser-interpreted headers for the proxy origin. Vendor response
        # headers stay reachable on `e.response.headers` for callers that
        # explicitly want them; only the proxy-supplied `headers=` kwarg
        # makes it onto `self.headers`.
```

**Flow:** any limiter or provider mapper raising a rate-limit condition constructs this class with a category → callers distinguish source via `.category`, dimension via `.rate_limit_type` → proxy serializers read `.detail`. Sibling class `BudgetExceededError` (:960+) deliberately does NOT join the RateLimitError hierarchy (keeps existing `except BudgetExceededError:` working) but carries the SAME `category`/`rate_limit_type` string attributes so StandardLoggingPayload consumers see uniform fields.
**Invariant:** Only explicitly passed `headers=` may land on `e.headers`; vendor response headers must remain quarantined on `e.response.headers`. Auto-copying them is the exact header-injection vector the comment warns about. Also: never change BudgetExceededError's base to RateLimitError for "unification" — that silently reroutes existing handlers.
**Probe:** `tests/test_litellm/litellm_core_utils/test_exception_mapping_utils.py` 429 rows assert `(litellm.RateLimitError, 429)` per provider; deterministic check: `grep -c "deliberately do NOT auto-populate" litellm/exceptions.py` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "RateLimitErrorCategory VENDOR_RATE_LIMIT budget", limit: 8 });
```

## Verdict
Adopt the unified-error shape (category + dimension + quarantined headers) whenever several limiters share one catchable error. Adapt the enum values to your limiter set. Omit the FastAPI `detail` mirroring if you have no HTTP serialization layer. Coverage caveat: header-quarantine behavior is pinned by the in-comment rationale plus mapping tests, not by a dedicated unit test at this pin.
