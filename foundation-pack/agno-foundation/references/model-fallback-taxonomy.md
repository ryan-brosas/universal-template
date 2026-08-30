<!-- capsule-v2 -->
# Model fallback taxonomy — Which provider errors may fall back to another model, and which must surface?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** How does fallback selection classify errors, and what hygiene keeps each attempt's message list clean?

## Error-specific lists win; 4xx never masked; attempts run on fresh message copies
**Path/Symbol:** `libs/agno/agno/models/fallback.py:get_fallback_models` (:76-111), `_clean_kwargs_for_fallback` (:119-129), `_copy_kwargs_with_fresh_messages`/`_sync_appended_messages` (:132-155), `call_model_with_fallback` (:158-182).
**Signature:** `get_fallback_models(fallback_config: Optional[FallbackConfig], error: Exception) -> Optional[List[Model]]`; `call_model_with_fallback(model, fallback_config: Optional[FallbackConfig], **kwargs) -> ModelResponse`.
**Data Shape:** FallbackConfig = on_error / on_rate_limit / on_context_overflow lists (+ optional callback); strings resolved via get_model and DEEPCOPY'd per config so shared configs don't cross-mutate agents.

### Decisive source
```python
# Don't mask non-retryable client errors (401/403/etc.) — these are
# configuration bugs that the developer needs to see and fix.
_retryable_status_codes = {429, 529}
if (
    isinstance(error, ModelProviderError)
    and not isinstance(error, (ModelRateLimitError, ContextWindowExceededError))
    and error.status_code
    and 400 <= error.status_code < 500
    and error.status_code not in _retryable_status_codes
):
    return None

def _clean_kwargs_for_fallback(kwargs: dict) -> dict:
    """The primary model's retry-with-guidance logic may have appended
    provider-specific guidance messages... Fallback models should not see those."""
    cleaned = dict(kwargs)
    if "messages" in cleaned:
        cleaned["messages"] = [m for m in cleaned["messages"] if not getattr(m, "temporary", False)]
    return cleaned
```

**Flow:** primary fails with ModelProviderError → classify (explicit exception types first, then re-classify generic provider errors) → pick list (rate_limit > context_overflow > on_error) → `_clean_kwargs_for_fallback` strips `temporary` guidance messages → each attempt runs on its OWN copied messages list (`_copy_kwargs_with_fresh_messages`) → whatever the successful fallback appended past seed_len is extended back onto the caller's list (`_sync_appended_messages`) so history persists. Stream variants emit a `fallback_model_activated` event before switching.
**Invariant:** 401/403/400 are configuration bugs — falling back would hide them behind another provider's success; only 429/529 and 5xx/network are legitimate fallback triggers when no specific list matched. The temporary-strip prevents provider-specific retry guidance from leaking into a different provider's prompt.
**Probe:** `grep -c '_retryable_status_codes = {429, 529}' libs/agno/agno/models/fallback.py` → **1**; `grep -c 'getattr(m, .temporary., False)' libs/agno/agno/models/fallback.py` → **1**; direct behavior tests `libs/agno/tests/unit/test_fallback.py::TestGetFallbackModels::test_get_fallback_models_blocks_401_auth_error`, `::test_get_fallback_models_classifies_429`, `::test_get_fallback_models_specific_over_general`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "FallbackConfig get_fallback_models call_model_with_fallback", limit: 10, fields: ["signature", "name", "file"] });
```
(resolves FallbackConfig members line-exact 44-68.)

## Verdict
Adopt the classification precedence + 4xx no-mask rule + per-attempt message-copy hygiene wholesale; adapt exception class names to your provider-error hierarchy; omit the callback hook if you have no alerting path.
