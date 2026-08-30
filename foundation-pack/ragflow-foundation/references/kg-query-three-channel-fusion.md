<!-- capsule-v2 -->
# KG query three-channel fusion — how does a question become one knowledge-graph context chunk ranked by sim × pagerank?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** When a KB has GraphRAG enabled, what exact retrieval/ranking pipeline turns the query into entity/relation/community context, and why can it never blow the token budget?

## One pseudo-chunk assembled from four signals
**Path/Symbol:** `rag/graphrag/search.py` class `KGSearch(Dealer)` (whole file); singleton wiring `common/settings.py:479` (`kg_retriever = kg_search.KGSearch(docStoreConn)`).
**Signature:** `async def retrieval(self, question, tenant_ids, kb_ids, emb_mdl, llm, max_token=8196, ent_topn=6, rel_topn=6, comm_topn=1, ent_sim_threshold=0.3, rel_sim_threshold=0.3)`.
**Data Shape:** Three candidate channels: A) entities-by-keyword — dense vector of ", ".join(LLM keywords), filter `knowledge_graph_kwd="entity"`, N=56; B) entities-by-type — term filter on `entity_type_kwd`, ordered `rank_flt` desc, N=10000, **no similarity floor** (`_ent_info_from_(es_res, 0)`); C) relations-by-text — dense over the raw question, filter `knowledge_graph_kwd="relation"`. Entity rows carry `entity_kwd`, `rank_flt` (pagerank), `n_hop_with_weight` (JSON paths+weights); relation rows carry `from_entity_kwd`/`to_entity_kwd` (sorted pair key) and `weight_int`.

### Decisive source
```python
# search.py:171-197 — n-hop edge credit + cross-channel boosts
for nbr in nhops:
    path, wts = nbr["path"], nbr["weights"]
    for i in range(len(path) - 1):
        f, t = path[i], path[i + 1]
        nhop_pathes[(f, t)]["sim"] += ent["sim"] / (2 + i)   # distance decay
        nhop_pathes[(f, t)]["pagerank"] = max(..., wts[i])
# P(E|Q) => P(E) * P(Q|E) => pagerank * sim
for ent in ents_from_types.keys():
    if ent not in ents_from_query: continue
    ents_from_query[ent]["sim"] *= 2                          # type corroboration
...
ents_from_query = sorted(..., key=lambda x: x[1]["sim"] * x[1]["pagerank"],
                         reverse=True)[:ent_topn]
```
```python
# search.py:225-230 — budget exhaustion drops the OVERFLOWING item, never exceeds
max_token -= num_tokens_from_string(str(ents[-1]))
if max_token <= 0:
    ents = ents[:-1]; break
```
```python
# dialog_service.py:790-796 — call site inserts the KG chunk FIRST when non-empty
ck = await settings.kg_retriever.retrieval(" ".join(questions), tenant_ids, ...)
if ck["content_with_weight"]:
    kbinfos["chunks"].insert(0, ck)
```

**Flow:** LLM query_rewrite (fail-soft ⇒ keywords=[question]) → channels A/B/C in sequence → n-hop edges harvested from channel-A hits credit unseen `(f,t)` pairs with decayed sim → boosts applied (type-hit entity ×2; text-found relation ×(1 + nhop_credit + endpoint-type-hits); n-hop-only relations seeded into the relation map) → rank both maps by `sim × pagerank` → truncate entities then relations under the running token budget → append community section with leftover budget → return ONE synthesized chunk: `docnm_kwd="Related content in Knowledge Graph"`, CSV tables via pandas, hardcoded `similarity=1.0`.
**Invariant:** The pipeline always produces a result even when every channel is empty or the rewriter dies (empty strings concatenate to ""); the token budget is a hard ceiling because each appended row pays its own cost and the overflowing row is removed; final rank is always the product `similarity × pagerank`, so an entity that only matches textually but has no PageRank still surfaces (sim>0 × 0 = 0 — actually dead unless pagerank>0; the type channel exists to give recall, the product to give precision).
**Probe:** `test/unit_test/rag/graphrag/test_graphrag_utils.py::TestGraphNodeToChunk` pins the write-side fields this ranking depends on (`rank_flt`, JSON `n_hop_with_weight`) — "dropped ranking fields" regression class docstring names KGSearch explicitly. No dedicated Python test for `KGSearch.retrieval` itself (source-read-only caveat).

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", query: "graphrag query retrieval entities keywords community report", filePattern: "*search*", fields: ["signature","lines"] });
// rank-1..8 = KGSearch._community_retrieval_, get_relevant_ents_by_keywords,
// query_rewrite, retrieval (:139-275), Go ParseCommunityReportChunks, Dealer.retrieval
await mcp.codebase_memory.get_code_snippet({ project: "ragflow", qualified_name: "ragflow.rag.graphrag.search.KGSearch.retrieval" });
await mcp.codebase_memory.trace_path({ project: "ragflow", function_name: "ragflow.rag.graphrag.search.KGSearch.retrieval", direction: "inbound" });
// callers_total 12: advanced_rag orchestrators/harness tools; production entry via settings.kg_retriever singleton
```

## Verdict
Adopt the channel decomposition (dense-keyword entities / type-recall entities / dense relations), the `sim × pagerank` product ranking, distance-decayed n-hop edge crediting, and drop-the-overflow-item token accounting. Adapt thresholds (0.3), tops (6/6/1), and the pandas-CSV rendering to host formats. Omit the Dealer inheritance if your store lacks the shared filter helper — only `get_filters/get_vector/dataStore.search` are used.
