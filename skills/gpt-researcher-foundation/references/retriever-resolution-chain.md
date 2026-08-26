<!-- capsule-v2 -->
# Retriever resolution chain — in what priority are retriever names resolved, and what happens to invalid or spaced entries?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** How does a request select its search backends, and which two silent-fallback behaviors must a porter know?

## get_retrievers ladder + match-statement factory
**Path/Symbol:** `gpt_researcher/actions/retriever.py:128-168` (`get_retrievers`), `:8-125` (`get_retriever` match factory), `:171-178` (`get_default_retriever` → TavilySearch); validation twin `config/config.py:188-201` (`parse_retrievers` raises on invalid).
**Signature:** `def get_retrievers(headers: dict[str, str], cfg) -> list[type]`
**Data Shape:** Names come from `headers["retrievers"]` (comma list) → `headers["retriever"]` (single) → `cfg.retrievers` (list-or-comma-string) → `cfg.retriever` → default. 20+ named backends incl. tavily/duckduckgo/brave/bing/google/searx/serper/serpapi/searchapi/arxiv/exa/crw/semantic_scholar/pubmed_central/openalex/custom/mcp/xquik/getxapi/groundroute/bocha.

### Decisive source
```python
# Strip whitespace from each retriever name so comma-separated lists with
# spaces (e.g. "tavily, exa" from a header or config) resolve correctly
# instead of silently falling back to the default retriever.
retrievers = [r.strip() for r in retrievers if r and r.strip()]
retriever_classes = [get_retriever(r) or get_default_retriever() for r in retrievers]
```

**Flow:** per-request headers override per-instance config overrides default → each name lazily imports its class inside the match arm (keeps provider deps optional) → invalid names DO NOT raise here: they silently become Tavily — the strict ValueError path exists only in Config construction.
**Invariant:** whitespace stripping happens BEFORE class lookup (the historical bug: `" exa"` fell back to default); MCP configs appended later ride this same list (`agent.py`). Retrievers whose search returns prefetched `raw_content` >100 chars skip scraping entirely (`researcher.py:850-862` prefetch branch) — a backend contract, not an option.
**Probe:** `tests/test_get_retrievers_whitespace.py` (4 cases: comma+spaces, single-with-spaces, blanks dropped, config-string path); battery P08a-b GREEN.
