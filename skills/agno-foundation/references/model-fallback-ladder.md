<!-- capsule-v2 -->
# Model-fallback ladder — which error gets which fallback list, and why are 401s never masked?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** Given a failed primary model call, how do you select the fallback list and preserve message history across attempts?

## FallbackConfig selection + attempt loop
**Path/Symbol:** `libs/agno/agno/models/fallback.py` (`get_fallback_models` :76-111, `call_model_with_fallback` :158, `_try_fallback_models` :283, message helpers :119-155).
**Signature:** `get_fallback_models(fallback_config: Optional[FallbackConfig], error: Exception) -> Optional[List[Model]]`; FallbackConfig carries three lists — `on_error`, `on_rate_limit`, `on_context_overflow` — plus an activation `callback(primary_id, fallback_id, error)`.
**Data Shape:** errors are classified subclasses of `ModelProviderError` (`ModelRateLimitError`, `ContextWindowExceededError`); models may be given as instances or string ids (resolved via deepcopy so a shared config never mutates).

### Decisive source
```python
def get_fallback_models(fallback_config, error):
    if isinstance(error, ModelRateLimitError) and fallback_config.on_rate_limit:
        return fallback_config.on_rate_limit                    # 1 specific beats general
    if isinstance(error, ContextWindowExceededError) and fallback_config.on_context_overflow:
        return fallback_config.on_context_overflow
    if isinstance(error, ModelProviderError):                   # late classification
        classified = ModelProviderError.classify(error)
        if isinstance(classified, ModelRateLimitError) and fallback_config.on_rate_limit:
            return fallback_config.on_rate_limit
        ...
    _retryable_status_codes = {429, 529}                        # Anthropic OverloadedError
    if (isinstance(error, ModelProviderError)
            and not isinstance(error, (ModelRateLimitError, ContextWindowExceededError))
            and error.status_code and 400 <= error.status_code < 500
            and error.status_code not in _retryable_status_codes):
        return None                                             # NEVER mask config bugs
    return fallback_config.on_error or None
```
Attempt loop: seed_len = len(kwargs["messages"]); per fallback, `_copy_kwargs_with_fresh_messages` gives EACH attempt its own list copy; on success `_sync_appended_messages(original_messages, attempt_messages, seed_len)` appends only what the fallback added (:144-156); on total failure the PRIMARY error is re-raised, not the last fallback's.
Streaming twins yield a `fallback_model_activated` event before switching (:227/:252).

**Flow:** primary raises ModelProviderError → classify → pick specific list else general (unless 4xx-non-{429,529}) → try each fallback in order with fresh message copies → first success syncs appended messages back into the caller's list → callback fires → else raise the ORIGINAL primary error.
**Invariant:** (1) 400/401/403/404/413/422 minus {429,529} return None — masking an auth bug with another model would hide it forever. (2) A 429 with an EMPTY on_rate_limit still falls through to on_error (legitimate scenario). (3) Temporary guidance messages (see retry-with-guidance capsule) are stripped for fallback attempts but each successful fallback's own additions ARE persisted. (4) All-fail re-raises the primary error for diagnosis.
**Probe:** `tests/unit/test_fallback.py` (25 tests: `test_get_fallback_models_specific_over_general`, `test_get_fallback_models_blocks_401_auth_error`, `test_fallback_response_synced_to_messages`, `test_all_models_fail_raises_primary_error`, ...); upstream suite executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "acall_model_with_fallback", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole selection ladder including the 429/529 carve-out; adapt status-code semantics to your providers; omit agno's stream-event vocabulary. Direct tests exist and were executed green.
