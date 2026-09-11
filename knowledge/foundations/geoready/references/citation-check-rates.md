<!-- capsule-v2 -->
# AI citation check — how do you measure whether answer engines cite your domain (and why Perplexity first)?

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How does a citation-check run turn N LLM answers into mention/citation rates and a four-state verdict?

## Query templates → per-answer extraction → rate aggregation
**Path/Symbol:** `src/geo_optimizer/core/citations.py:run_citation_check` (83–185), `resolve_provider` (64–80), `_verdict` (54–61).
**Signature:** `run_citation_check(brand, domain, *, topic="", queries=None, provider=None, api_key=None) -> CitationCheckResult`.
**Data Shape:** default queries = 3 templates (`What is the best tool for {topic}?` / recommend / compare) with `topic=brand`; result carries `entries[]`, `queries_run`, `brand_mention_rate`, `domain_citation_rate` (both rounded to 2), `top_cited_domains[:5]`, `verdict`.

### Decisive source
```python
def _verdict(domain_citation_rate: float, brand_mention_rate: float) -> str:
    if domain_citation_rate >= _STRONG_CITATION_RATE:   # 0.5
        return "strong"
    if domain_citation_rate > 0:
        return "cited"
    if brand_mention_rate > 0:
        return "mentioned_only"     # brand known but never sourced — the GEO gap
    return "invisible"

# resolve_provider: explicit provider wins; else PREFER Perplexity when its key is set
# (real web citations), falling back to the standard auto-detection chain.
perplexity_key = os.environ.get("PERPLEXITY_API_KEY", "")
if perplexity_key:
    return "perplexity", perplexity_key
return detect_provider()
```

**Flow:** normalize domain (`strip www`, hostname-only via urlparse when `://` present) → per query call `query_llm` → erroring answers become error entries and are EXCLUDED from denominators (`answered`) → per answered query: cited domains = provider `citations` list + URL-bearing text domains deduped, brand mentioned via precise `brand_pattern`, non-self domains tallied in a Counter → rates over `answered` only.
**Invariant:** Grounded vs parametric providers are NOT interchangeable for citation measurement — Sonar returns source URLs; OpenAI/Anthropic/Groq can only reveal brand knowledge (their `citations` lists are empty), so provider preference order is load-bearing. Rates divide by ANSWERED count, not attempted; all-failed runs degrade to `skipped_reason` with the first error quoted.
**Probe:** `tests/test_citations.py` (+ `tests/test_llm_client.py` for the transport mocks; `PYTHONPATH=src pytest tests/test_citations.py tests/test_llm_client.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "run_citation_check perplexity verdict", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the answered-denominator aggregation + four-state verdict + grounded-provider-first resolution; adapt query templates and provider set; omit the specific vendor URLs.
