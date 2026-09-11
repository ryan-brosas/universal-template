<!-- capsule-v2 -->
# provider-resolution-ladder — How does a bare model string become (model, provider, key, api_base) without ambiguity?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** What is the exact precedence order of `get_llm_provider`, and which traps (prefix rewriting, JSON providers, proxy default) must a porter preserve?

## Connected graph-selected seam
**Path/Symbol:** `litellm/litellm_core_utils/get_llm_provider_logic.py:get_llm_provider` (:130-502) + `_get_openai_compatible_provider_info` (:516-857).
**Signature:** `get_llm_provider(model: str, custom_llm_provider=None, api_base=None, api_key=None, litellm_params=None) -> tuple[str, str, str | None, str | None]`.
**Data Shape:** Returns `(model_without_prefix, custom_llm_provider, dynamic_api_key, api_base)`. Raises `litellm.exceptions.BadRequestError` on unresolvable models (never a raw exception — the outer `except` at :503-513 wraps everything else into BadRequestError with `llm_provider=""`).

### Decisive source
```python
        # check if llm provider provided
        if (
            model.split("/", 1)[0] in litellm.provider_list
            and model.split("/", 1)[0] not in litellm.model_list_set
            and len(model.split("/")) > 1  # handle edge case ... issues/1351 (`mistral`)
        ):
            return _get_openai_compatible_provider_info(...)
```

**Flow:** (1) PROXY DEFAULT FIRST: if `_should_use_litellm_proxy_by_default(litellm_params)` (env `USE_LITELLM_PROXY` bool / `litellm_params.use_litellm_proxy` / module flag) → return `litellm_proxy/<model>` untouched (:151-156). This is why a porter must NOT reorder it below prefix parsing. (2) Azure-AI-Studio carve-out: model starting `azure/` whose suffix is a known cohere/mistral model is rewritten to provider `openai` (:169-172). (3) Suffix upgrades: `cohere/command-r` → `cohere_chat`; `anthropic/<text-model>` → `anthropic_text` (both handlers return early only when the prefix matches AND the model list confirms). (4) Prefix reconciliation: if explicit `custom_llm_provider` differs from the model's first segment, REBUILD `model = provider + "/" + model` (:179-182) so downstream always sees a prefixed string. (5) OpenRouter strip rule (:189-193): with `custom_llm_provider == "openrouter"` and model starting `openrouter/`, keep `openrouter/auto` intact but reduce `openrouter/anthropic/claude-3.5-sonnet` → `anthropic/claude-3.5-sonnet` (OpenRouter expects provider/model natively). (6) JSON-configured providers checked BEFORE enum `provider_list` (:195-204) — a registered `providers.json` slug wins over builtin lists. (7) Builtin prefix branch: first-segment ∈ `provider_list` and NOT in `model_list_set` and has `/` → openai-compatible info fill (api_base/key from secrets); elif plain prefix match → simple split (:221-228). (8) api_base sniffing against `litellm.openai_compatible_endpoints` using parsed-URL matching (see api-base-endpoint-matching capsule), assigning provider + pulling the provider's API key env var into `dynamic_api_key`. (9) Model-list membership ladders (openai chat/text, anthropic, cohere, replicate 64-char-version-id heuristic :388-395, vertex family of NINE lists, bedrock trio, startswith families like `bytez/`, `oci/`, `amazon_nova`). (10) LAST RESORT declarative fallback `match_routing_generalization(model)` (:480-481) routes future unknown models by declared rules — only on total miss. (11) Miss → colored docs URL print unless `litellm.suppress_debug_info`, then `BadRequestError`.

The companion `_get_openai_compatible_provider_info` is a ~340-line elif ladder keyed on the provider slug that fills `(api_base, dynamic_api_key)` — pattern: `api_base or get_secret("<X>_API_BASE") or "<hardcoded default>"`, `dynamic_api_key = api_key or get_secret_str("<X>_API_KEY")`. Some providers delegate to their config class (`litellm.GroqChatConfig()._get_openai_compatible_provider_info(...)`), three providers RETURN an upgraded provider slug (`azure_ai`, `github_copilot`, `chatgpt` can rewrite `custom_llm_provider` in place), and `ragflow` re-prefixes the model back onto itself (:834-841). Final normalization (:851-857): type-check both strings, and `if dynamic_api_key is None and api_key is not None: dynamic_api_key = api_key`.

**Invariant:** Precedence order is load-bearing: proxy-default → azure carve-out → suffix upgrades → prefix reconcile → openrouter strip → JSON registry → provider_list prefix → api_base endpoint match → model lists → generalization fallback → error. Moving any rung changes which credentials get attached to real traffic.
**Probe:** `tests/test_litellm/litellm_core_utils/test_get_llm_provider.py` pins prefix/suffix behavior across providers; the newest pin for this seam lives in `tests/test_litellm/litellm_core_utils/test_exception_mapping_utils.py` sibling suites — run `grep -c "def test" tests/test_litellm/litellm_core_utils/test_get_llm_provider.py` (≥30 parametrized cases at f005afa1).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "get_llm_provider custom_llm_provider", limit: 10 });
```

## Verdict
Adopt the ordered ladder + secret-fill pattern wholesale — it is the reusable "route a bare model name" contract. Adapt the provider tables (`provider_list`, endpoint list, config classes) to your host's provider set. Omit the litellm-specific proxy default and JSON-provider registry unless you port those features too. Coverage caveat: the giant elif ladder is exercised by upstream unit suites, not a single table test.
