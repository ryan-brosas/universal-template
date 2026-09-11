<!-- capsule-v2 -->
# Usage-first cost ladder — in what order does cost calculation trust API usage, pricing tables, and tiktoken estimates?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** When porting cost tracking, which source of token counts wins, and what happens for Anthropic or non-OpenAI embedding models?

## calculate_llm_cost precedence chain
**Path/Symbol:** `gpt_researcher/utils/costs.py:159-241` (`calculate_anthropic_cost`, `calculate_llm_cost`), `estimate_embedding_cost` :244-263.
**Signature:** `def calculate_llm_cost(llm_provider, model, input_content, output_content, response_metadata=None, usage_metadata=None, request_options=None) -> float`
**Data Shape:** Pricing tables are tuples of `(patterns, $in/MTok, $out/MTok)` scanned by substring, FIRST match wins (so `-mini`/`-nano` entries precede base models). `ANTHROPIC_US_INFERENCE_GEO_MODELS` gets a 1.1× surcharge when `request_options["inference_geo"] == "us"`.

### Decisive source
```python
if llm_provider == "anthropic":
    anthropic_cost = calculate_anthropic_cost(...)   # native usage + table; None if no rule
    if anthropic_cost is not None:
        return anthropic_cost
usage_tokens = _extract_usage_tokens(usage_metadata)
if usage_tokens is not None:                          # API-reported beats estimates:
    input_tokens, output_tokens = usage_tokens        # "the latter overcounts input and
    pricing = _get_openai_pricing(model)              #  misses reasoning tokens entirely"
    ...
return estimate_llm_cost(input_content, output_content)  # tiktoken o200k_base fallback
```

**Flow:** provider metadata captured per call → Anthropic branch reads `response_metadata.usage.input_tokens/output_tokens` (falls back to langchain `usage_metadata`) → OpenAI branch uses reported tokens with table pricing else flat defaults ($5/$15 MTok) → final fallback re-tokenizes both strings.
**Invariant:** missing Anthropic pricing rule returns None (→ falls through to generic ladder) instead of guessing; `estimate_embedding_cost` catches the `tiktoken.encoding_for_model` KeyError for Ollama/Cohere/etc. and falls back to `o200k_base` so embedding-cost accounting NEVER aborts mid-research.
**Probe:** `tests/test_costs.py` covers native-Anthropic preference, dated model names, fallback-without-usage, and non-OpenAI embeddings not raising; battery P05a-d GREEN (`* multiplier` ×1 — surcharge applied exactly once).
