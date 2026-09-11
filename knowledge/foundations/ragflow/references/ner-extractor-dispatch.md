<!-- capsule-v2 -->
# NER extractor selection — how does a KB run knowledge-graph extraction with zero LLM extraction calls, and where does the pipeline change shape for it?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** How is the extractor class chosen from config, and what must the indexing pipeline do differently when the chosen extractor needs no LLM?

## Config dispatch + batch bypass
**Path/Symbol:** `rag/graphrag/general/index.py:118-138` (`_select_extractor_type`, `_select_extractor`), `:334-336` (`load_doc_chunks` NER bypass); `rag/graphrag/ner/graph_extractor.py` class `GraphExtractor` (:328-633).
**Signature:** `def _select_extractor(graphrag_config: dict)` → `GeneralKGExt | NerKGExt | LightKGExt`; `async def _process_single_content(self, chunk_key_dp, chunk_seq, num_chunks, out_results, task_id="")`.
**Data Shape:** Config key `graphrag.method`: `"general"` (Microsoft LLM), `"light"` (LightRAG LLM, **default for missing or unrecognized values**), `"ner"` (spaCy, no LLM). NER unit of work is the RAW chunk: `load_doc_chunks` returns per-chunk contents without token-size merging; LLM methods get chunks merged up to `batch_chunk_token_size`.

### Decisive source
```python
# index.py:133-138 — fail-to-light dispatch
method = graphrag_config.get("method", "light")
if method == "general":  return GeneralKGExt
if method == "ner":      return NerKGExt
return LightKGExt
```
```python
# index.py:334-336 — pipeline shape change for no-LLM extraction
contents = [content for chunk in raw_chunks if (content := chunk.get("content_with_weight", ""))]
# For NER-based extractionm, no need to batch extract entity and relation
if _select_extractor_type(graphrag_config) == "ner":
    return contents
```
```python
# ner/graph_extractor.py:455-509 — LinearRAG relation-free bridging (no LLM)
for a_idx in range(len(ent_list)):
    for b_idx in range(a_idx + 1, len(ent_list)):
        pair = tuple(sorted([ea["entity_name"], eb["entity_name"]]))
        if pair in seen_pairs: continue
        seen_pairs.add(pair)
        weight = max(entity_tf.get(ea, 0) + entity_tf.get(eb, 0), 0.01) \
                 if self._use_tf_weight else self._relationship_strength
        edge_record = dict(src_id=pair[0], tgt_id=pair[1], weight=weight,
                           description="", keywords=[...], source_id=chunk_key)
```

**Flow:** entities = union of MGranRAG 3-pass stacking keywords (hyphen/apostrophe merge → capitalised-run merge absorbing ADP/CCONJ/DET/PART → PROPN/NOUN/NUM run merge; trailing-lowercase truncation; CCONJ split "Bob and Lucy"→Bob,Lucy) with spaCy NER ents minus skip-labels. Type resolution: spaCy label via `SPACY_TO_APP_ENTITY_TYPE`, else POS inference (PROPN→person, NOUN→category, NUM→event, any-uppercase→person, else category); `entity_types` allow-list filters. Relations: every pair co-occurring within `max_sentence_distance` sentences gets an edge with EMPTY description; the inherited Extractor merge machinery still may use the LLM downstream to summarize duplicate descriptions — but never for extraction. The spaCy model loads eagerly in `__init__` so missing-model errors surface at construction, not mid-task.
**Invariant:** Unknown method values fall back to light (never crash); NER mode keeps sentence boundaries intact by skipping chunk merging (merged mega-chunks would corrupt sentence-index-based pairing); edge descriptions are intentionally empty at extraction time — context lives in the shared sentence, not duplicated text.
**Probe:** No dedicated upstream test file for the NER path at this pin (source-read-only caveat recorded); dispatch behavior is pinned only by source. `DepRelationExtractor` (dependency-LCA relation descriptions) exists but its call sites are commented out in GraphExtractor — dead code at this pin, cited as boundary.

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", query: "select extractor NER keywords batch chunks graphrag entity extraction dispatch", fields: ["signature","lines"] });
// rank-1..2 = ner/graph_extractor.extract_keywords :119-294, ner_all_keywords :311-320;
// rank-3 = NERExtractor.extract_batch; rank-4/5 = _select_extractor :122-138 / _select_extractor_type :118-119
await mcp.codebase_memory.get_architecture({ project: "ragflow", path: "rag/graphrag", aspects: ["structure","overview"] });
// cluster 1 (_process_single_content, extract_keywords, ner_all_keywords, _has_uppercase, get_ner),
// cluster 18 (extract/extract_batch/_extract_entities/DepRelationExtractor/_ensure_model), cluster 20 (relation subtree helpers)
```
Direct reads: `rag/graphrag/general/index.py` :108-182 and :300-359; `rag/graphrag/ner/graph_extractor.py` :105-633.

## Verdict
Adopt the three-way dispatch with fail-to-light default and the "no-LLM ⇒ skip input batching" pipeline fork. Adapt entity-type vocabularies and the POS-inference ladder to your domain language; adapt TF-weighting choice (`use_tf_weight`) to your ranking needs. Omit the dependency-tree relation describer unless you revive it — it is disabled upstream.
