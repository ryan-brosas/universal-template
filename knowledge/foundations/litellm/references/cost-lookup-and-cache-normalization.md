<!-- capsule-v2 -->
# cost-lookup-and-cache-normalization — How is a request's USD cost computed, and why must cache tokens be normalized across providers first?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** What is the model-cost lookup order in `cost_per_token` and the prompt-tokens-inclusion invariant for cached traffic?

## Connected graph-selected seam
**Path/Symbol:** `litellm/cost_calculator.py:cost_per_token` (:301+) with `_cost_per_token_custom_pricing_helper`, plus `router_strategy/lowest_tpm_rpm_v2.py:log_success_event` (:211+) as the usage-ledger consumer.
**Signature:** `cost_per_token(model="", prompt_tokens=0, completion_tokens=0, ..., custom_llm_provider=None, cache_creation_input_tokens=0, cache_read_input_tokens=0, usage_object=None, call_type="completion", region_name=None, service_tier=None, ...) -> tuple[float, float]` (prompt USD, completion USD).
**Data Shape:** Reads `litellm.model_cost` (the global price map). Handles character-priced (vertex/tts), per-second, per-query (rerank billed units), cache-tiered, service-tier, data-residency (`eu`/`us` uplift), and vertex-region pricing variants.

### Decisive source
```python
    # Normalize cache token counts across providers:
    #   - OpenAI-compatible: usage.prompt_tokens_details.cached_tokens
    #     (prompt_tokens already INCLUDES cached_tokens)
    #   - Anthropic: usage.cache_read_input_tokens / cache_creation_input_tokens
    #     (prompt_tokens does NOT include these — adjust before calling helper)
...
    _normalized_prompt_tokens = float(prompt_tokens)
    if _is_anthropic_style:
        _normalized_prompt_tokens += _cache_read_tokens + _cache_creation_tokens
```
and the lookup ladder:
```python
    if model_with_provider in model_cost_ref:  # Option 2. "openai/gpt-4"
        model = model_with_provider
    elif model in model_cost_ref:             # Option 1. raw model string
        model = model
    elif model_without_prefix in model_cost_ref:  # Option 3. strip "bedrock/" prefix
        model = model_without_prefix
```

**Flow:** custom caller pricing short-circuits first → normalize cache tokens (OpenAI-compatible nested details vs Anthropic top-level fields; write tokens may arrive as `cache_write_tokens` OR `cache_creation_tokens`) → ANTHROPIC STYLE ADJUSTMENT: add cache tokens INTO the prompt total because downstream helpers assume prompt_tokens includes them; OpenAI style must NOT be adjusted again — double counting is the classic port bug → provider-prefix dedup loop (`openai/openai/gpt-5.5` chains stripped only when the CALLER supplied a provider; a MagicMock guard prevents an infinite dedup loop on non-string models) → optional `provider/region/model` key wins over plain keys → three-option lookup → call-type-specific branches (speech/aspeech require prompt_characters under character pricing). The tpm_rpm_v2 ledger then keys spend as `{model_id}:{model}:tpm:{HH-MM}` minute buckets via `increment_cache`.
**Invariant:** Exactly ONE normalization happens per usage object; the helper's contract is "prompt_tokens includes cache tokens" and every provider shape must be converted TO that contract before pricing. Region-prefixed pricing beats provider-prefixed pricing beats bare names.
**Probe:** `tests/test_litellm/litellm_core_utils/test_cost_calculator.py` (cache-token normalization + lookup-order cases); deterministic checks: `grep -c "_is_anthropic_style" litellm/cost_calculator.py` ≥ 4; `grep -c "Option 2. use model with provider" litellm/cost_calculator.py` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "cost_per_token cache_read_input_tokens", limit: 8 });
```

## Verdict
Adopt the normalize-to-one-contract rule and the three-option price-key ladder for any billing layer spanning providers with different cache semantics. Adapt the price-map schema. Omit per-second/per-character branches you don't serve. Coverage caveat: none at this pin.
