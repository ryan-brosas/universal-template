<!-- capsule-v2 -->
# retry-loop-num-retries-resolution — How does the retry loop pick its retry count, and which exceptions must escape immediately instead of being retried?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** What is the precedence chain for `num_retries` and the exact raise-immediately taxonomy inside `should_retry_this_error`?

## Connected graph-selected seam
**Path/Symbol:** `litellm/router.py:async_function_with_retries` (:6650-6832) + `should_retry_this_error` (:6873-6935).
**Signature:** `async_function_with_retries(self, *args, **kwargs)` (pops `original_function`, `fallbacks`, `num_retries`, `model_group_retry_policy` from kwargs).
**Data Shape:** Metadata contract: `_metadata["attempted_retries"]` / `_metadata["max_retries"]` maintained BEFORE each attempt for spend-log observability; response gets `x-litellm-attempted-retries`-family headers via `add_retry_headers_to_response`.

### Decisive source
```python
        num_retries = request_num_retries
        if num_retries is None:
            # Fall back to the router setting (then 0) so the comparisons below never
            # hit `None > int`, which would mask the real upstream error with a TypeError.
            num_retries = self.num_retries if self.num_retries is not None else 0
...
            deployment_num_retries: Final = getattr(e, "num_retries", None)
            if (
                request_num_retries is None
                and deployment_num_retries is not None
                and isinstance(deployment_num_retries, int)
            ):
                num_retries = deployment_num_retries
```

**Flow (precedence):** request kwarg → per-deployment exception-carried `e.num_retries` (only if no explicit request value; set by pre-call limiters like tpm_rpm_v2 which attach `num_retries=deployment.get("num_retries")` to their RateLimitError) → retry-policy lookup `_get_num_retries_from_retry_policy(exception, model_group, ...)` (policy hit REPLACES num_retries AND sets `_retry_policy_applies`, which then SKIPS the should-retry gate entirely — policy takes precedence) → router default → 0. The None-guard matters: a bare `None > int` TypeError would replace the provider's real error with a confusing crash.

**Flow (`should_retry_this_error` — raises to stop retries):** ContextWindowExceededError with context_window_fallbacks configured → raise (fall through to fallback machinery instead of hammering the same context). ContentPolicyViolationError with content_policy_fallbacks → raise. Non-retryable status per `litellm._should_retry` → raise EXCEPT 401/403 (allowed to rotate to another deployment's credentials when multiple deployments exist). NotFoundError → always raise. openai.RateLimitError with zero healthy deployments but fallbacks available → raise (let fallbacks handle it). AuthenticationError with ≤1 total deployment → raise (retrying the only key cannot help). Zero healthy deployments at all → raise. Otherwise True → enter the retry loop.

**Loop tail invariant (:6776-6832):** every mid-loop exception REPLACES `original_exception` ("Always track the latest error so we raise the most recent exception instead of the first one"); after exhaustion, `max_retries`/actual-attempted counts are setattr'd back onto the final exception (only when it's a LITELLM_EXCEPTION_TYPES member) before re-raising.
**Invariant:** The gate check runs BEFORE the loop AND between attempts (unless policy applies); exhausted loops must raise the LAST error with accurate retry counters, never the first.
**Probe:** `tests/test_litellm/test_router_per_deployment_num_retries.py` (`TestNumRetriesNoneGuard` :266-316 pins the None→router-default→0 fallback chain directly); deterministic checks: `grep -c "Always track the latest error" litellm/router.py` → 1; `grep -c "def should_retry_this_error" litellm/router.py` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "async_function_with_retries should_retry_this_error", limit: 8 });
```

## Verdict
Adopt the precedence chain (request > deployment-hint > policy > default > 0) and the raise-now taxonomy for any multi-backend retry engine. Adapt which statuses count as non-retryable to your providers' contracts. Omit the metadata/header bookkeeping if you lack spend tracking. Coverage caveat: upstream router suites cover these paths broadly; run the cited test module on drift rather than trusting this pin forever.
