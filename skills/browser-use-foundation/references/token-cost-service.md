<!-- capsule-v2 -->
# Token cost service — layered pricing resolution with XDG-cached remote data

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how does an agent framework compute per-run LLM cost across any provider, including prompt-cache pricing, without hardcoding a price table?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tokens/service.py` (647 lines): `TokenCost` (:49) — `initialize` (:67), `_load_pricing_data` (:74), `_find_valid_cache` (:84), `_fetch_and_cache_pricing_data` (:151), `get_model_pricing` (:176-219), `calculate_cost` (:221+); sources: `custom_pricing.py` (`CUSTOM_MODEL_PRICING`), `mappings.py` (`MODEL_TO_LITELLM`), `openrouter_pricing.py` (live metadata API); cache at `xdg_cache_home()` (:42).
**Signature:** `get_model_pricing(model)` resolves through a strict precedence chain; `calculate_cost(model, usage)` splits cached vs uncached input tokens and applies per-tier rates.
**Data Shape:** `ModelPricing {input_cost_per_token, output_cost_per_token, max_tokens?, max_input/output_tokens?, cache_read_input_token_cost, cache_creation_input_token_cost, cache_creation_1h_input_token_cost}`; `ChatInvokeUsage` carries `prompt_cached_tokens`, `pricing_multiplier`, 5m/1h cache-creation splits.

### Decisive source
```ts
# precedence chain in get_model_pricing:
if model_name in CUSTOM_MODEL_PRICING: return ...      # 1. user overrides
if is_openrouter_pricing_model(model_name):            # 2. openrouter-prefixed
    return await get_openrouter_model_pricing(...)
litellm_name = MODEL_TO_LITELLM.get(model_name, model_name)
if litellm_name in self._pricing_data: return ...      # 3. LiteLLM snapshot (cached)
return await get_openrouter_model_pricing(...)         # 4. live fallback
# cost math separates token classes:
uncached_prompt_tokens = usage.prompt_tokens - (usage.prompt_cached_tokens or 0)
# 5m vs 1h cache-write tiers priced differently when reported
```

**Flow:** first use → look for a valid XDG cache file (source-matched, freshness-checked) → else fetch the LiteLLM pricing database once and cache it → per call, resolve pricing by the 4-step chain → cost = Σ over token classes (uncached input × input rate + cached read × cache rate + cache writes × tier rate + output × output rate), scaled by any provider `pricing_multiplier`. Unknown models degrade to None (cost tracking silently off), never raise.
**Invariant:** user overrides always win; remote pricing fetched once and disk-cached (XDG path); cache-aware accounting (a cached-token-heavy run costs what it actually cost); missing pricing is non-fatal.
**Probe:** `tests/tokens/` tests (override precedence; cache hit avoids refetch; cached-vs-uncached split math; openrouter id normalization).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "TokenCost get_model_pricing calculate_cost CUSTOM_MODEL_PRICING cache", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt layered pricing resolution (overrides → prefixed → cached snapshot → live API) with class-separated token costing and silent None on unknowns.
