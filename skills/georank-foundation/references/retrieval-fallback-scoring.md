<!-- capsule-v2 -->
# Lexical retrieval fallback — scoring published companies without embeddings

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** When vector search is unavailable (no embedding key / dead Qdrant), what deterministic ranking still returns sensible company recommendations?

## Script-aware tokenization + weighted field match
**Path/Symbol:** `backend/app/services/company_retrieval.py`: `_tokenize_query` :30–57, `_company_search_blob` :59–77, `_match_score` :61–110, `fallback_company_recommendations` :112+.
**Signature:** `fallback_company_recommendations(db, query: str, *, diagnostic_report_id: str | None = None, limit: int = 5) -> list[Company]`.
**Data Shape:** Tokens: latin `[a-zA-Z0-9][a-zA-Z0-9#+.\-]{1,}` + CJK `[\u4e00-\u9fff]{2,8}`, deduped lowercase. Score components: preferred-id +120; name exact +60/partial +34; category exact +26/partial +18; tag ±20/12; tech-stack ±16/10; blob hit +5; is_geo_certified +2; geo_score/25 capped +4.

### Decisive source
```python
for token in tokens:
    if token == name: score += 60.0
    elif token in name: score += 34.0
    ...
    if token and token in blob: score += 5.0        # weak whole-blob evidence
if company.is_geo_certified: score += 2.0           # tiny platform-trust nudges
if company.geo_score: score += min(company.geo_score / 25.0, 4.0)
```
The RAG caller (`ai_client.rag_recommend` :499+) skips Qdrant entirely for BYOK requests — platform embedding is a platform COST:
```python
search_results = []
if provider_override is None:          # BYOK path uses deterministic recommendations as context
    try:
        query_vector = await self.embed(message)
        search_results = vector_store.search_companies(query_vector, top_k=5)
    except Exception:
        search_results = []            # any failure ⇒ fallback ranking below
```

**Flow:** tokenize query (mixed-script aware) → load PUBLISHED companies once → score each on field-weighted token matches + small trust boosts → sort desc, prefer the diagnostic's own company (+120 anchor when invoked from a report context) → top-5 feed the LLM prompt as grounded context with name/description/geo_score.
**Invariant:** Fallback output type/shape EXACTLY mirrors the vector path (list of Company + context text), so prompt assembly never branches. Scores are pure functions of stored fields — snapshot-testable. Trust boosts are bounded so a high geo_score can't outrank a literal name match.
**Probe:** `backend/tests/test_company_retrieval.py::test_*` (tokenization + weight-table assertions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "fallback_company_recommendations", limit: 5 });
// verified line-exact: company_retrieval.py :112+
```

## Verdict
Adopt as the always-available tier under ANY semantic retriever; adapt weights per field richness; keep CJK bigram-ish token classes if serving Chinese queries.
