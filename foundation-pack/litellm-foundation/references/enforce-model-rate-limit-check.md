<!-- capsule-v2 -->
# Enforce-model-rate-limits check — how do you enforce per-deployment TPM/RPM limits across ALL routing strategies without a second Redis round-trip per request?

**Source:** litellm (MIT), `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `ext-litellm`. **Question:** enforce deployment TPM/RPM as a pre-call check (not a routing strategy) with correct limit semantics and no request loss on infra failure.

## enforce-model-rate-limit-check
**Path/Symbol:** `litellm/router_utils/pre_call_checks/model_rate_limit_check.py:ModelRateLimitingCheck` (`pre_call_check` :139-217, `async_pre_call_check` :219-305, `_get_deployment_limits` :99-127, `async_log_success_event` :307-363).
**Signature:** `pre_call_check(self, deployment: dict) -> dict | None`; raises `litellm.RateLimitError` when over limit, returns deployment otherwise.
**Data Shape:** deployment dict with optional `tpm`/`rpm` read from THREE places in order: top-level → `litellm_params.tpm/rpm` → `model_info.tpm/rpm` (first non-None wins per field). Cache keys `{model_id}:{deployment_name}:tpm:{HH-MM}` / `...:rpm:{HH-MM}` (UTC minute via `get_utc_datetime().strftime("%H-%M")`), TTL 60s (`RoutingArgs.ttl`).

### Decisive source
```python
# Check TPM limit
if tpm_limit is not None:
    # First check local cache
    current_tpm: Final = self.dual_cache.get_cache(key=tpm_key, local_only=True)
    if current_tpm is not None and current_tpm >= tpm_limit:
        raise litellm.RateLimitError(...)

# Check RPM limit (atomic increment-first to avoid race conditions)
if rpm_limit is not None:
    current_rpm: Final = self.dual_cache.increment_cache(key=rpm_key, value=1, ttl=RoutingArgs.ttl)
    if current_rpm is not None and current_rpm > rpm_limit:
        raise litellm.RateLimitError(...)
```
(:172-192 sync; async twins at :253-279 additionally pass `num_retries=0` so the router does NOT retry its own 429.)

**Flow:** pick deployment → (optional ITPM/OTPM reserve if deployment sets itpm/otpm, see itpm-otpm-reservation-ledger) → TPM: local-only READ of post-hoc counter (`async_log_success_event` increments by actual `total_tokens` after each success :350-360) → RPM: atomic INCREMENT-FIRST then compare `> rpm_limit` → raise RateLimitError carrying `RouterErrors.user_defined_ratelimit_error` marker + `retry-after: 60` + synthetic httpx.Response (method=`"model_rate_limit_check"`).
**Invariant:** TPM and RPM are deliberately ASYMMETRIC — TPM reads local-only (tokens are counted post-success, so incrementing pre-call would double-count) while RPM must increment first or N concurrent requests all see "current < limit" and pass (race). The whole check is FAIL-OPEN: any non-RateLimitError exception returns the deployment unchanged (:214-217 "Don't fail the request if rate limit check fails"). If a deployment configures itpm/otpm alongside tpm/rpm BOTH are enforced and a once-per-model_id warning fires (`_io_token_conflict_warned_ids` set; degenerate configs without an id warn every time).
**Probe:** `tests/test_litellm/test_router/test_enforce_model_rate_limits.py` — `test_pre_call_check_raises_rate_limit_error_when_over_rpm` (:90) and `test_pre_call_check_raises_rate_limit_error_when_over_tpm` (:127); suite GREEN 53/53 at pin (runner: repo venv + PYTHONPATH deps, see leaf Full view).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "ModelRateLimitingCheck pre_call_check", limit: 5, fields: ["signature", "name", "file"] });
```
(rank-1 = `ModelRateLimitingCheck.pre_call_check` model_rate_limit_check.py:139-217.)

## Verdict
Adopt the asymmetric enforcement (TPM local-read of post-hoc counts, RPM increment-first) and the fail-open wrapper; adapt key grammar/ttl to your cache backend; omit the proxy-specific `user_defined_ratelimit_error` marker string only if your retry loop has no equivalent user-vs-vendor limiter distinction.
