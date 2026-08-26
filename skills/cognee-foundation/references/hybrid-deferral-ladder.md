<!-- capsule-v2 -->
# Hybrid deferral ladder — when HYBRID_COMPLETION must not run

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** Which request shapes force a hybrid search to degrade to graph completion, and which must hard-error instead?

## hybrid_deferral + FEELING_LUCKY resolution
**Path/Symbol:** `cognee/modules/search/methods/hybrid_deferral.py:hybrid_deferral_reason` (:57-76), `request_deferral_reason` (:30-47), `reject_hybrid_graph_only_knobs` (:16-27); resolver `cognee/modules/search/methods/get_retriever_output.py:_effective_search_type` (:16-33); LLM selector `cognee/modules/search/operations/select_search_type.py:select_search_type` (:11-41).
**Signature:** `reject_hybrid_graph_only_knobs(kwargs)` raises `CogneeValidationError(name="InvalidHybridSearchConfig")`; `hybrid_deferral_reason(kwargs, *, graph_is_empty) -> Optional[str]`.
**Data Shape:** Graph-only knobs = `("wide_search_top_k", "triplet_distance_penalty")`.

### Decisive source
```python
# HARD error — explicit values are invalid on hybrid, even the numbers graph
# completion uses as its own defaults. Omitted/None is fine:
for name in _GRAPH_ONLY_KNOBS:
    if kwargs.get(name) is not None:
        raise CogneeValidationError(message=f"{name} requires query_type=SearchType.GRAPH_COMPLETION.", ...)

# SOFT deferral (return reason, caller logs and swaps retriever):
if custom_node_type or untyped_named_scope: return f"node_type={type_name} is not NodeSet"
if kwargs.get("neighborhood_depth") is not None: return "neighborhood_depth is set"
if (kwargs.get("feedback_influence") or 0.0) > 0: return "feedback_influence > 0"
# + chunk-collection check, SKIPPED on empty graph, fails OPEN on backend errors:
if not await vector_engine.has_collection(_DOCUMENT_CHUNK_COLLECTION):
    return f"{_DOCUMENT_CHUNK_COLLECTION} collection missing"
```

**Flow:** `_effective_search_type`: FEELING_LUCKY on an EMPTY graph short-circuits to HYBRID_COMPLETION (no LLM selector call), else asks an LLM to name a SearchType (invalid/unusable answer ⇒ RAG_COMPLETION default; CODE excluded because it needs a structured code_query the selector can't construct) → hybrid requests get knobs validated THEN deferral checked → payload records the EFFECTIVE type; only `search()` strips it.
**Invariant:** The error-vs-defer split is the contract: knobs that change ranking SEMANTICS on hybrid are user mistakes (raise); capabilities hybrid can't serve at all defer with a logged reason. Collection probes fail open so a backend hiccup degrades availability of one optimization, not the search.
**Probe:** `cognee/tests/unit/modules/retrieval/test_hybrid_deferral.py` / deferral pins in `cognee/tests/unit/modules/retrieval/hybrid*`; `select_search_type` exclusion pinned in `cognee/tests/unit/modules/search/`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "hybrid_deferral_reason reject_hybrid_graph_only_knobs FEELING_LUCKY", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier validate-then-degrade pattern; adapt knob names to your retrievers; omit the LLM-based search-type selector unless you want FEELING_LUCKY routing.
