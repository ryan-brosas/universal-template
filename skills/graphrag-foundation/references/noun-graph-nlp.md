<!-- capsule-v2 -->
# build_noun_graph — no-LLM co-occurrence graph: hash-keyed extraction cache, sorted-pair combination edges, optional PMI weights, sequential by design

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** how does the fast NLP indexing path build a knowledge graph without a single LLM call, and what makes its cache keys safe?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/index/operations/build_noun_graph/build_noun_graph.py`: `build_noun_graph` (:23-53), `_extract_nodes` (:56-96), `_extract_edges` (:99-143); `np_extractors/base.py`: `BaseNounPhraseExtractor` (ABC; `load_spacy_model` auto-download :210-225); `np_extractors/factory.py` + `cfg_extractor.py` / `syntactic_parsing_extractor.py` / `regex_extractor.py`; `graphs/edge_weights.py::calculate_pmi_edge_weights`.
**Signature:** `build_noun_graph(text_unit_table: Table, text_analyzer: BaseNounPhraseExtractor, normalize_edge_weights: bool, cache: Cache) -> tuple[pd.DataFrame, pd.DataFrame]`.
**Data Shape:** nodes = {title, frequency=len(ids), text_unit_ids}; edges = {source, target, weight=co-occurrence count, text_unit_ids} with weight optionally replaced by PMI.

### Decisive source
```python
attrs = {"text": text, "analyzer": str(text_analyzer)}
key = gen_sha512_hash(attrs, attrs.keys())     # cache key covers TEXT + ANALYZER IDENTITY
result = await extraction_cache.get(key)
if not result:
    result = text_analyzer.extract(text)
    await extraction_cache.set(key, result)
...
for tu_id, titles in text_unit_to_titles.items():
    if len(titles) < 2: continue
    for pair in combinations(sorted(set(titles)), 2):   # dedupe + canonical order per text unit
        edge_map[pair].append(tu_id)
# weight = number of shared text units; PMI normalization optional
if normalize_edge_weights and not edges_df.empty:
    edges_df = calculate_pmi_edge_weights(nodes_df, edges_df)
```
Sequential loop is DELIBERATE (docstring): "NLP extraction is CPU-bound… threading provides no benefit under the GIL. We process rows sequentially, relying on the cache."

**Flow:** stream text units → per-row sha512(text+str(analyzer)) cache probe → spaCy/CFG/regex noun-phrase extraction (model auto-downloads on OSError) → invert to text_unit→titles → all sorted unique pairs per unit become edges weighted by shared-unit count → optional PMI reweighting using node frequencies.
**Invariant:** (1) Cache key includes `str(text_analyzer)` — swapping extractor type/model invalidates old entries automatically; omitting this poisons caches across config changes. (2) Pairs are built from `sorted(set(titles))` so (A,B) never duplicates as (B,A) and self-loops are impossible. (3) No threads here BY DESIGN — parallelism was consciously rejected for the NLP path.
**Probe:** `tests/verbs/test_extract_graph_nlp.py` (workflow verb smoke) + `tests/unit/indexing/test_cluster_graph.py::TestClusterGraphRealData` consume its output shape; extractor internals have no dedicated unit file — coverage caveat recorded.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "build_noun_graph _extract_nodes _extract_edges calculate_pmi_edge_weights BaseNounPhraseExtractor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt analyzer-aware content hashing for extraction caches plus sorted-combination co-occurrence edges as the cheap cold-start graph; adapt extractor choice (CFG vs regex) per corpus language; respect the sequential-loop rationale before adding threads to CPU-bound NLP.
