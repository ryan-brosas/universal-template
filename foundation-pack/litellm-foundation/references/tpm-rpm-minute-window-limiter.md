<!-- capsule-v2 -->
# tpm-rpm-minute-window-limiter — How are per-deployment TPM/RPM budgets enforced pre-call without a thundering-herd of redis reads?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** What is the local-first increment protocol that raises a user-defined RateLimitError before the provider call, and what must NOT fail the request?

## Connected graph-selected seam
**Path/Symbol:** `litellm/router_strategy/lowest_tpm_rpm_v2.py:LowestTPMLoggingHandler_v2.pre_call_check` (:60-133) / `async_pre_call_check` (:135-209) / `log_success_event` (:211+); base class `router_strategy/base_routing_strategy.py`.
**Signature:** `async_pre_call_check(self, deployment: dict, parent_otel_span: Span | None) -> dict | None`.
**Data Shape:** Cache keys: `{model_id}:{deployment_name}:rpm:{HH-MM}` and `...:tpm:{HH-MM}` — UTC minute strings (`dt.strftime("%H-%M")`) so all instances bucket identically regardless of system timezone. TTL from `routing_args.ttl`. Limit resolution ladder: `deployment["rpm"]` → `litellm_params["rpm"]` → `model_info["rpm"]` → `float("inf")`.

### Decisive source
```python
            local_result: Final = await self.router_cache.async_get_cache(
                key=rpm_key, local_only=True
            )  # check local result first

            ...
            if local_result is not None and local_result >= deployment_rpm:
                raise litellm.RateLimitError(
                    message=f"Deployment over defined rpm limit={deployment_rpm}. current usage={local_result}",
                    ...,
                    headers={"retry-after": str(60)},
                    num_retries=deployment.get("num_retries"),
                )
            else:
                # if local result below limit, check redis ## prevent unnecessary redis checks
                result = await self._increment_value_in_current_window(key=rpm_key, value=1, ttl=self.routing_args.ttl)
                if result is not None and result > deployment_rpm:
                    raise litellm.RateLimitError(... current usage=result ...)
```

**Flow:** local cache read (local_only=True) → if already ≥ limit, raise immediately with NO redis write → else INCREMENT (atomic in-window increment; the async variant uses `_increment_value_in_current_window`) → if post-increment count EXCEEDS limit, raise. The raised error is `litellm.RateLimitError` whose content embeds `RouterErrors.user_defined_ratelimit_error.value` so the router can distinguish USER-DEFINED limits (rotate deployment) from vendor 429s (cool down), carries `retry-after: 60` and the deployment's own num_retries hint (which `async_function_with_retries` consumes as the retry-count override). On success events, TPM tokens are incremented by the response's total_tokens. EVERYTHING is wrapped in try/except that re-raises only RateLimitError and swallows infrastructure failures (`return deployment  # don't fail calls if eg. redis fails to connect`).
**Invariant:** A limiter outage must degrade to NO limiting, never to failed requests. The boundary check is asymmetric by design: local `>=` short-circuit avoids redis chatter, but only the shared increment gives cross-instance truth — skipping the increment when local says over-limit trades a little accuracy for O(1) redis load.
**Probe:** `tests/test_litellm/router_unit_tests/test_router_strategy/test_lowest_tpm_rpm_routing.py` (direct tests for both check variants + success-event accounting).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "pre_call_check rpm tpm increment_cache", limit: 8 });
```

## Verdict
Adopt the local-first/increment-second minute-window limiter and its fail-open wrapper for any multi-instance budget enforcer. Adapt key grammar and limit-resolution order to your deployment schema. Omit TPM token accounting if you only cap request rates. Coverage caveat: none at this pin.
