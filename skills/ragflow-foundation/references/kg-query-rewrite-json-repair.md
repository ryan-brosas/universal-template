<!-- capsule-v2 -->
# KG query rewrite JSON-repair ladder — how do you get typed keywords out of an LLM without letting a malformed reply kill retrieval?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** What is the contract for the LLM step that rewrites a question into answer-type keywords + entities, and what happens on every failure mode?

## Two-tier parse, fail-soft consumer
**Path/Symbol:** `rag/graphrag/search.py:36-66` (`KGSearch._chat`, `KGSearch.query_rewrite`); prompt template `rag/graphrag/query_analyze_prompt.py` `PROMPTS["minirag_query2kwd"]`.
**Signature:** `async def query_rewrite(self, llm, question, idxnms, kb_ids) -> tuple[type_keywords: list, entities_from_query: list]`.
**Data Shape:** Prompt injects a type-pool hint: `get_entity_type2samples(idxnms, kb_ids)` returns `{entity_type: [sample entities]}` from stored `ty2ents` chunks (limit 10000 in the Go twin), serialized into the prompt so the model picks types that actually exist in the KB. Expected JSON: `{"answer_type_keywords": [...≤3...], "entities_from_query": [...]}`; Python caps entities at `[:5]`.

### Decisive source
```python
# search.py — cached chat with error sentinel
response = get_llm_cache(llm_bdl.llm_name, system, history, gen_conf)
if response: return response
response = await llm_bdl.async_chat(system, history, gen_conf)
if response.find("**ERROR**") >= 0:
    raise Exception(response)
set_llm_cache(llm_bdl.llm_name, system, response, history, gen_conf)
```
```python
# search.py:50-66 — repair ladder
try:
    keywords_data = json_repair.loads(result)          # tier 1: lenient parser
    return keywords_data.get("answer_type_keywords", []), \
           keywords_data.get("entities_from_query", [])[:5]
except json_repair.JSONDecodeError:
    try:
        result = result.replace(hint_prompt[:-1], "").replace("user", "").replace("model", "").strip()
        result = "{" + result.split("{")[1].split("}")[0] + "}"   # tier 2: brace rebuild
        keywords_data = json_repair.loads(result)
        ...
    except Exception as e:
        logging.exception(...); raise e                 # propagates to fail-soft caller
```
```python
# search.py:160-166 — the consumer never lets rewrite failure kill retrieval
try:
    ty_kwds, ents = await self.query_rewrite(llm, qst, ...)
except Exception as e:
    logging.exception(e); ents = [qst]                  # raw question becomes keyword
```

**Flow:** build hint prompt with KB-specific type pool → cached LLM call → parse (lenient → echo-strip + brace rebuild) → `(types, entities[:5])`. Any exception anywhere is caught by `retrieval`, which downgrades to "use the raw question as the only keyword" and continues with all channels.
**Invariant:** A rewrite failure degrades recall, never availability: the pipeline runs with `[question]` instead of dying or returning empty context. The LLM cache is keyed on the full prompt (which embeds the KB's type pool), so cache hits are per-KB correct. `.get(..., [])` defaults mean missing keys are tolerated at both tiers.
**Probe:** No dedicated upstream test for `query_rewrite` at this pin (source-read-only caveat recorded). The sentinel/cache behavior mirrors `graphrag-gleaning-extraction`'s `_async_chat`, whose cache/sentinel semantics are covered by extractor tests.

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", query: "graphrag query retrieval entities keywords community report", filePattern: "*search*" });
// rank-4 = ragflow.rag.graphrag.search.KGSearch.query_rewrite :46-66
```
Direct read of `rag/graphrag/query_analyze_prompt.py` confirmed the required keys (`answer_type_keywords` ≤3 "highest likelihood at the forefront", `entities_from_query` "must be extracted from the query") and few-shot examples ending in exactly those fields.

## Verdict
Adopt the two-tier parse with an echo-strip/brace-rebuild fallback and the fail-soft caller contract ("rewrite failure ⇒ use the question itself"); adopt the type-pool hint pattern (constrain the model to entity types that exist in this KB before it answers). Adapt the cap constants (5 entities, 3 types) and the cache key to your host; omit `json_repair` only if you keep an equivalent lenient parser as tier 1.
