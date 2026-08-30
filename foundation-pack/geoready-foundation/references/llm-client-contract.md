<!-- capsule-v2 -->
# Provider-agnostic LLM client — one response shape, four vendors, citations only from grounded ones

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you normalize OpenAI/Anthropic/Groq/Perplexity behind one call while never losing Perplexity's source URLs?

## detect → dispatch → LLMResponse(error-or-payload)
**Path/Symbol:** `src/geo_optimizer/core/llm_client.py:query_llm` (78–127), `_query_perplexity` (186–223), `detect_provider` (58–75).
**Signature:** `query_llm(prompt, *, system="", provider=None, api_key=None, model=None, max_tokens=1024) -> LLMResponse`.
**Data Shape:** `LLMResponse(text, model, provider, prompt_tokens, completion_tokens, error|None, citations: list[str])` — errors are VALUES on the dataclass, never exceptions.

### Decisive source
```python
# Auto-detection ORDER is deliberate: Perplexity listed LAST so adding its key
# does not silently change the provider for users who configured another one.
_PROVIDER_ENV_KEYS = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
                      "groq": "GROQ_API_KEY", "perplexity": "PERPLEXITY_API_KEY"}
...
# Sonar exposes sources both as a flat `citations` list and as structured
# `search_results`; merge them preserving order.
citations = list(data.get("citations") or [])
for result in data.get("search_results") or []:
    url = result.get("url", "")
    if url and url not in citations:
        citations.append(url)
```

**Flow:** explicit `GEO_LLM_PROVIDER`+key wins → else first env key present in dict order → model resolution `explicit arg > GEO_LLM_MODEL > per-provider default` (`sonar`, `gpt-4o-mini`, ...) → vendor-specific transport (SDK imports wrapped in try/ImportError returning a descriptive error RESPONSE; Perplexity uses plain requests against the OpenAI-compatible chat endpoint) → every failure path returns `LLMResponse(error=f"{type(exc).__name__}: {exc}", ...)` after logging at WARNING.
**Invariant:** Callers branch on `.error`, never try/except — one contract for missing-keys, missing-SDKs, and API failures; `_LLM_TIMEOUT=30` bounds every vendor call; citation extraction exists ONLY on the Perplexity arm because parametric providers genuinely return no sources. A porter who "unifies" by parsing citations from text conflates grounded and parametric knowledge.
**Probe:** `tests/test_llm_client.py` (mocked transports incl error paths; `PYTHONPATH=src pytest tests/test_llm_client.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "detect_provider query_llm LLMResponse", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt error-as-value + env-detection-order + citations-only-from-grounded arms; adapt vendor list/models to current APIs; omit SDK-import fallbacks if you hard-require deps.
