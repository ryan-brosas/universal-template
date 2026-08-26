<!-- capsule-v2 -->
# Router filter pipeline ordering — in what order do cooldown, callback filters, tag routing, order/weighted-failover exclusion narrow the candidate list?

**Source:** litellm (MIT), `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** the exact stage order inside `async_get_healthy_deployments` and how per-deployment pre-call checks attach AFTER a pick.

## router-filter-pipeline-order
**Path/Symbol:** `litellm/router.py:Router.async_get_healthy_deployments` (:11181-11310), `async_callback_filter_deployments` (:7545-7592), `async_routing_strategy_pre_call_checks` (:7484-7543), `add_optional_pre_call_checks` (:1803-1887).
**Signature:** `async_callback_filter_deployments(model, healthy_deployments, messages, parent_otel_span, request_kwargs, logging_obj) -> list[dict]`.
**Data Shape:** each stage takes the previous stage's list; two kwargs are POPPED as consumed: `_target_order`, `_excluded_deployment_ids`.

### Decisive source
```python
cooldown_deployments: Final = await _async_get_cooldown_deployments(...)
_pre_cooldown_deployments: Final = healthy_deployments
healthy_deployments = self._filter_cooldown_deployments(...)
# Safety net: only bypass cooldown filter when health-check routing is
# driving cooldown (i.e. allowed_fails_policy is set). Without a policy,
# cooldowns are from real request failures and must not be bypassed.
if not healthy_deployments and self.enable_health_check_routing and self.allowed_fails_policy is not None:
    ...
    healthy_deployments = _pre_cooldown_deployments
...
healthy_deployments = await self.async_callback_filter_deployments(...)
if self.enable_pre_call_checks and (messages is not None or input is not None):
    healthy_deployments = self._pre_call_checks(..., input_token_count=await self._acount_pre_call_check_tokens(...))
...
## WEIGHTED FAILOVER EXCLUSION ## -> drop deployments already tried in
## this request via weighted-failover. Always honored, regardless of the
## router-level flag, so a stale exclusion key on kwargs cannot escape.
```
(:11222-11296)

**Flow (ordered):** `_common_checks_available_deployment` → team filter → web-search filter → health-check filter → cooldown filter (with the policy-gated bypass) → blocked-deployments filter → **callback filters** (every CustomLogger's `async_filter_deployments` — budget limiter, affinity checks, prompt-caching pin run here, in callback registration order; exceptions log failure + re-raise) → strategy pre-call checks (`enable_pre_call_checks`: context-window/model-max filtering with one batched token count) → tag-based routing → routing-plugin candidates → order filter → weighted-failover exclusion → empty ⇒ `async_raise_no_deployment_exception`. AFTER a specific deployment is picked by the strategy, `async_function_with_retries` calls `async_routing_strategy_pre_call_checks(deployment)` INSIDE the semaphore — RateLimitError there triggers failure-logging AND cooldown registration before re-raising (:7505-7527).
**Invariant:** (1) callback filters see the post-cooldown healthy set and may only NARROW (or raise); pick strategies consume their output — this is why budget/affinity/prompt-cache checks are filters while tpm-rpm enforcement is a post-pick check; (2) the cooldown bypass requires BOTH health-check routing enabled AND an allowed_fails_policy — real-failure cooldowns are never bypassed; (3) `_excluded_deployment_ids` is honored unconditionally so a stale key can't skip filtering; (4) optional check NAMES map to callbacks once (`enforce_model_rate_limits`, `router_budget_limiting` auto-appended when budgets configured :793-796, affinity trio folded into one shared instance); (5) token counting for pre-call checks is done ONCE via `_acount_pre_call_check_tokens` with `skip_inline_token_count=True`.
**Probe:** `grep -c 'async_filter_deployments' litellm/router.py` = **1** (the dispatch loop at :7569); direct tests: `tests/test_litellm/test_router.py` router-level suites GREEN slices this pass (affinity/budget/hotpath suites exercise the pipeline through `Router` construction).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "async_callback_filter_deployments Router", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the stage ORDER (it defines precedence semantics: cooldown > callback filters > tag > order > failover-exclusion) and the semaphore-scoped post-pick check placement; adapt stage names; omit health-check-routing bypass if you have no active probing.
