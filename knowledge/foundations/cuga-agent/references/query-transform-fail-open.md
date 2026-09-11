<!-- capsule-v2 -->
# Multi-query + HyDE expansion that fails open — how do you add LLM query rewriting to retrieval without making the LLM a hard dependency, and where is HyDE allowed to go?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** You want multi-query and HyDE recall boosts on a RAG pipeline — how do you keep search working when the LLM is down/slow, and why does HyDE feed ONLY the dense leg?

## EXTRA legs, never replacements; every failure mode returns QueryVariants()
**Path/Symbol:** `src/cuga/backend/knowledge/query_transform.py` — module docstring :1-19 (fail-open + HyDE-leg rationale), `VALID_QUERY_TRANSFORMS` :32, `ChatGenerator` Protocol :37-40, `QueryVariants(dense_extra, lexical_extra)` :43-55, bounded `_CACHE` :60 (LRU 512 keyed `(mode, query, n)`), `_MULTI_PROMPT`/`_HYDE_PROMPT` :62-71, `expand_query` :74-107, `_generate` :110-121, `_parse_lines` :127-139.
**Signature:** `async expand_query(mode: str, query: str, generator: ChatGenerator | None, *, n=3, timeout_s=2.0) -> QueryVariants`; host adapts its own LLM to the one-method Protocol (`async generate(prompt) -> str`) — zero cuga imports inside the knowledge package.
**Data Shape:** `QueryVariants.dense_extra` feeds dense embeddings; `lexical_extra` feeds BM25. multi_query puts rewrites in BOTH; HyDE puts the hypothetical doc in `dense_extra` ONLY.

### Decisive source
```python
# :96-101 fail-open — timeout or ANY error degrades to no-extras
try:
    variants = await asyncio.wait_for(_generate(mode, q, generator, n), timeout=timeout_s)
except Exception as e:
    logger.warning(f"cuga.knowledge.query_transform_degraded mode={mode} err={e!r}")
    return QueryVariants()
```
```python
# :116-120 hyde — hallucinated tokens kept OUT of lexical/BM25 by construction
doc = (await generator.generate(_HYDE_PROMPT.format(q=query))).strip()
return QueryVariants(dense_extra=[doc] if doc else [])
```
**Flow:** guard (`generator is None` / mode off / empty query → no-extras) → LRU cache check → generate under 2.0s `wait_for` → parse lines (strip bullets/numbering/quotes, drop blanks + duplicates of original and each other case-insensitively) → cache → return. The engine ALWAYS retrieves the original query on its normal dense+lexical path; variants only add candidates into RRF.
**Invariant:** (1) Fail open on EVERYTHING — no generator, off-mode, empty query, timeout, parse error, LLM exception. Transformation is an additive recall aid, never a hard dependency. (2) The real query is never replaced — a hallucinated passage can only ADD candidates via dense similarity, never substitute for the user's terms in exact-match BM25. (3) Don't use LangChain MultiQueryRetriever/HypotheticalDocumentEmbedder here: they union-merge and DISCARD RANK, destroying downstream RRF fusion and the reranker overfetch window. (4) Cache key includes mode+query+n so per-scope fan-out doesn't re-pay the call.

**Probe:** `tests/unit/test_knowledge_query_transform.py` — `test_multi_query_parses_dedups_and_strips_numbering` (:29), `test_hyde_keeps_real_query_and_doc_is_dense_only` (:43), `test_fail_open_off_none_and_error` (:56), `test_timeout_fails_open` (:67), `test_hyde_searches_real_query_and_hypothetical_doc_end_to_end` (:118).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "expand_query query_transform multi_query hyde dense_extra lexical_extra", limit: 8 });
```
## Verdict
Adopt the EXTRA-legs shape + fail-open wrapper for any optional LLM enrichment of a retrieval path. Adapt prompts/n. Omit the lexical split only if you have no keyword leg — then HyDE's dense-only restriction becomes moot but the fail-open contract stands.
