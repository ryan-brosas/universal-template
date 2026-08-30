<!-- capsule-v2 -->
# Completion-with-fallbacks loop — how does the model-level (non-router) fallback chain preserve per-attempt isolation and report attempts?

**Source:** litellm (MIT), `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** the standalone fallback runner in litellm_core_utils — semantics a porter must keep if they port it without the Router.

## completion-with-fallbacks-loop
**Path/Symbol:** `litellm/litellm_core_utils/fallback_utils.py` (`async_completion_with_fallbacks` :17-81, `completion_with_fallbacks` :84-85); header annotation helper `add_retry_fallback_headers_to_response` at `litellm/router_utils/add_retry_fallback_headers.py:222-241`.
**Signature:** `async_completion_with_fallbacks(**kwargs) -> ModelResponse`; `fallbacks: list[str | dict]` popped from nested `kwargs["kwargs"]["fallbacks"]`.
**Data Shape:** effective chain = `[original_model] + fallbacks`; dict entries = `{model?: str, ...param-overrides}` merged over base kwargs; response gains header `x-litellm-attempted-fallbacks: <index of successful attempt>`.

### Decisive source
```python
for attempted_fallbacks, fallback in enumerate(fallbacks):
    try:
        completion_kwargs = safe_deep_copy(base_kwargs)
        # Handle dictionary fallback configurations
        if isinstance(fallback, dict):
            fallback_config = safe_deep_copy(dict(fallback))
            model = fallback_config.pop("model", original_model)
            completion_kwargs.update(fallback_config)
        else:
            model = fallback

        # Filter out internal parameters that shouldn't be sent to provider APIs
        completion_kwargs = filter_internal_params(completion_kwargs)

        response = await litellm.acompletion(
            **completion_kwargs,
            model=model,
            litellm_logging_obj=litellm_logging_obj,
        )

        if response is not None:
            return add_fallback_headers_to_response(
                response=response,
                attempted_fallbacks=attempted_fallbacks,
            )
```
(:48-72)

**Flow:** build ONE `base_kwargs` (nested kwargs flattened, fresh `litellm_call_id`, `model` removed, caller's `litellm_logging_obj` preserved and reused across attempts) → iterate chain: per-attempt `safe_deep_copy` so dict-fallback mutations can't leak into later attempts → dict fallback pops its `model` (defaulting to ORIGINAL model — a dict may only override params while keeping the primary model) → `filter_internal_params` strips router-only fields before the provider call → first non-None response wins; exceptions are logged with the failing model name, remembered as `most_recent_exception_str`, and the loop continues → exhaustion raises a plain Exception whose message LEADS with the most recent failure.
**Invariant:** (1) per-attempt deepcopy is the isolation contract — direct test `test_fallback_dict_not_mutated` pins that the caller's fallback dict survives unchanged; (2) `attempted_fallbacks` is the ENUM INDEX (0 = primary succeeded), asserted by `test_async_completion_with_fallbacks_sets_attempted_fallbacks_header` (:53) and `..._header_is_zero_when_primary_succeeds` (:84); (3) sync entry runs the async body via `run_async_function` (thread-offload for sync callers), so both share one code path; (4) this module has NO cooldown/health integration — it is the dumb-but-honest chain; Router-managed fallbacks live elsewhere (router-level `fallbacks=[...]` handling + context-window/content-policy fallback machinery, deliberately out of scope here).
**Probe:** `tests/test_litellm/litellm_core_utils/test_fallback_utils.py` — 6 tests GREEN at pin incl. the two header tests above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "async_completion_with_fallbacks", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-attempt deepcopy + index-truthful attempt headers; adapt the param-filter list to your internal field names; omit the shared logging-object reuse if your logger isn't idempotent across attempts.
