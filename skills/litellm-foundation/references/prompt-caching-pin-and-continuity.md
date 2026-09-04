<!-- capsule-v2 -->
# Prompt-caching deployment pin + Responses-API continuity shims — how do implicit cache hits and previous_response_id route to their origin?

**Source:** litellm (MIT), `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** prefix-hash pinning for auto-injected cache breakpoints, plus the deprecated and unified previous_response_id paths.

## prompt-caching-pin-and-continuity
**Path/Symbol:** `litellm/router_utils/pre_call_checks/prompt_caching_deployment_check.py` (`_get_min_token_count_for_deployments` :24-46, `async_filter_deployments` :53-102, `async_log_success_event` :104+); `responses_api_deployment_check.py:ResponsesApiDeploymentCheck` (whole file, 57L); unified successor wiring in `router.py:1810-1846`.
**Signature:** `async_filter_deployments(...) -> list[dict]` (narrow to `[deployment]` on hit); `ResponsesApiDeploymentCheck.__init__` emits `DeprecationWarning`.
**Data Shape:** `PromptCachingCache` maps affinity key (hash of messages-as-they-will-be-sent) → `{model_id}`; min-token gate = LOWEST `get_prompt_cache_min_tokens(model)` across the group, default `DEFAULT_MINIMUM_PROMPT_CACHE_TOKEN_COUNT`.

### Decisive source
```python
# That makes the lowest minimum in the group the correct threshold rather than the highest.
# `model` here is the model-group alias the operator chose, not a model name, so the threshold
# has to come from the deployments themselves, and a group may mix models whose minimums differ.
# Taking the highest would skip the lookup for a prefix a lower-minimum member genuinely cached,
# losing a cache hit it had earned. The lowest can only cost a lookup that finds nothing.
return min(
    (
        get_prompt_cache_min_tokens(model=deployment["litellm_params"]["model"])
        for deployment in healthy_deployments
        if deployment.get("litellm_params", {}).get("model")
    ),
    default=DEFAULT_MINIMUM_PROMPT_CACHE_TOKEN_COUNT,
)
```
(:39-46)

**Flow:** filter: gate on `is_prompt_caching_valid_prompt(messages, model=GROUP-alias, min_token_count=min-across-group)` → derive affinity messages via `AnthropicCacheControlHook.messages_with_default_injections` — because auto breakpoints are injected AFTER deployment pick inside `acompletion`, the key must be computed from messages AS THEY WILL BE SENT (:70-73 comment) → `prompt_cache.async_get_model_id` → narrow. Write side (`async_log_success_event`) records model_id only for completion/anthropic_messages call types of valid prompts. Continuity: deprecated `ResponsesApiDeploymentCheck` decodes `previous_response_id` → returns the originating deployment when still healthy; its logic was folded into `DeploymentAffinityCheck(enable_responses_api_affinity=True)` as the HIGHEST-priority pin — Router keeps ONE shared affinity callback and ORs flags if both names appear in `optional_pre_call_checks` (router.py:1823-1835), so enabling either spelling never double-registers.
**Invariant:** (1) the min-not-max threshold cannot cause a wrong pin because entries exist only if a deployment's real model actually cached that prefix — worst case is a wasted lookup; (2) tools are passed as None to BOTH cache write and read (`[TODO]` upstream :148) so tool-bearing prompts may collide across different tool sets — known limitation, not an invariant to preserve; (3) deprecation is loud but non-breaking: old name still routes correctly.
**Probe:** `tests/test_litellm/router_utils/pre_call_checks/test_prompt_caching_deployment_check.py::test_get_min_token_count_for_deployments_takes_min_across_mixed_group` (:63) + `test_affinity_key_matches_the_messages_auto_caching_actually_sends` (:222); suite GREEN at pin (18 passed incl fallback_utils).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "PromptCachingDeploymentCheck async_filter_deployments", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lowest-threshold group gating and write-side call-type filtering; adapt the affinity-key derivation to however your breakpoint injection works; omit the deprecated class entirely in greenfield ports (wire the unified flag instead).
