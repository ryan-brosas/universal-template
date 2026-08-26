<!-- capsule-v2 -->
# cooldown-decision-ladder — Which failures put a deployment in cooldown, and when do single-deployment groups get spared?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** What is the ordered cooldown gate (status filter → global switches → per-deployment policy → error-rate base case) that decides whether a failed deployment is benched?

## Connected graph-selected seam
**Path/Symbol:** `litellm/router_utils/cooldown_handlers.py:_should_run_cooldown_logic` (:258-314), `_is_cooldown_required` (:205-255), `_should_cooldown_deployment` (:317-404), per-deployment policy helpers (:90-202).
**Signature:** `_should_cooldown_deployment(litellm_router_instance, deployment, exception_status, original_exception, requested_model_group=None) -> bool`.
**Data Shape:** Constants: `DEFAULT_ALLOWED_FAILS=3`, `DEFAULT_COOLDOWN_TIME_SECONDS=5`, `DEFAULT_FAILURE_THRESHOLD_PERCENT=0.5` (50% of a minute's requests), plus `SINGLE_DEPLOYMENT_TRAFFIC_FAILURE_THRESHOLD` for the all-failed rule.

### Decisive source
```python
        if exception_status >= 400 and exception_status < 500:
            if exception_status == 429:
                return True          # cool down rate limits
            elif exception_status == 401:
                return True          # cool down auth errors
            elif exception_status == 408 or exception_status == 404:
                return True
            else:
                # Do NOT cool down all other 4XX Errors
                return False
        else:
            # should cool down for all other errors
            return True
```
(`_is_cooldown_required`; string guard above it: any exception_str containing "APIConnectionError" never cools down.)

**Flow:** `_should_run_cooldown_logic` gates FIRST on: deployment/group resolvable → `time_to_cooldown` not ≈0 (`math.isclose(abs_tol=1e-9)`) → `disable_cooldowns` flag → `_is_cooldown_required` status filter UNLESS the deployment carries an explicit per-exception-type `allowed_fails_policy` entry (that opt-in overrides the 4XX default-skip) → not a provider-default deployment. Then `_should_cooldown_deployment`: (1) DEPLOYMENT-LEVEL policy wins over router-level — `_EXCEPTION_POLICY_FIELDS` is an ORDERED tuple where ContentPolicyViolationError precedes BadRequestError because it SUBCLASSES it; policy hit yields a type-name cache-key suffix so failure counters are per-exception-type. On a single-deployment group with only generic allowed_fails set, defer to the safety net instead of benching the only deployment (:149-151). (2) BASE CASE (no policies): compute this minute's fail rate from success/fail counters; cooldown iff 429-on-multi-deployment, OR 100% fails with traffic ≥ threshold, OR fails > 50% with ≥ minimum requests and multi-deployment, OR `litellm._should_retry(status)` says non-retryable. (3) Legacy allowed-fails counting path otherwise. Cooldown writes go through `_set_cooldown_deployments` into the router cache (local + redis).
**Invariant:** The 4XX default-skip exists because client errors are usually not the deployment's fault; ONLY an explicit named-type policy entry may override it. Subclass ordering in the policy table is semantic. Cooldown decisions must remain observable as plain bools so callers can log WHY.
**Probe:** `tests/test_litellm/router_unit_tests/test_router_cooldown_utils.py` (direct tests incl. `test_is_cooldown_required_empty_string_exception_status` :530-542 and the single-deployment safety-net family); deterministic check: `grep -c "APIConnectionError" litellm/router_utils/cooldown_handlers.py` → ≥1 (the ignore-string guard).
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "ext-litellm", query: "_is_cooldown_required allowed_fails_policy", limit: 8 });
```

## Verdict
Adopt the three-layer decision (status filter → opt-in policy → error-rate statistics) for any retry pool that benches bad backends. Adapt thresholds and policy field names to your config surface. Omit the redis sync if you're single-process. Coverage caveat: none at this pin.
