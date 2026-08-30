<!-- capsule-v2 -->
# Extraction & load workflow guards — empty-graph fail-fast, covariate id minting, and the NLP twin's missing raise

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory project `graphrag`. **Question:** Where do the extraction workflows fail fast vs degrade, and what input/output shaping happens at the workflow layer (not the operations layer)?

## Key facts
**Path/Symbol:** `graphrag/index/workflows/extract_graph.py` (`run_workflow` :32-94 dual-model wiring; module-level `extract_graph` :97-154 with zero-entity/zero-relationship ValueError raises :127-137; raw snapshot BEFORE summarization :139-141; `get_summarized_entities_relationships` :157-185 — drop-description-then-left-merge). Twin: `extract_graph_nlp.py` (:77-89 — entities raise, edges only LOG: missing `raise`, latent bug); `prune_graph.py` (workflow fn :46-77 re-raises empty after prune :66-75); `extract_covariates.py` (:60-108 text_unit_id copy trick + uuid4 ids); `load_input_documents.py` (:20-40 zero-documents raise).
**Signature:** extraction models are built PER CONCERN with separate cache children: `create_completion(extraction_model_config, cache=context.cache.child(config.extract_graph.model_instance_name), ...)` and again for summarization (:45-59).
**Data Shape:** covariates output = COVARIATES_FINAL_COLUMNS with `id = str(uuid4()) per row` and `human_readable_id = index`; text_units get a TEMPORARY `text_unit_id` column so claim rows inherit it, dropped afterward ("don't pollute the global").

### Decisive source
```python
# extract_graph.py :113-141 — raise-on-empty guards flank the raw-copy boundary:
if len(extracted_entities) == 0:
    raise ValueError("Graph Extraction failed. No entities detected during extraction.")
if len(extracted_relationships) == 0:
    raise ValueError("Graph Extraction failed. No relationships detected during extraction.")
# copy these as is before any summarization
raw_entities = extracted_entities.copy(); raw_relationships = extracted_relationships.copy()
```
```python
# extract_graph_nlp.py :84-89 — SAME guard shape but the raise was never added:
if len(extracted_edges) == 0:
    error_msg = "NLP Graph Extraction failed. No relationships detected during extraction."
    logger.error(error_msg)          # ← logs and FALLS THROUGH to write an empty edge table
```
```python
# extract_covariates.py — id plumbing comment is the contract:
# "reassign the id because it will be overwritten in the output by a covariate one"
text_units["text_unit_id"] = text_units["id"]
...
text_units.drop(columns=["text_unit_id"], inplace=True)  # don't pollute the global
```
**Flow:** read text units → wire extraction+summarization models (separate cache namespaces) → extract → GUARD → snapshot raw if `config.snapshots.raw_graph` → summarize descriptions via drop+left-merge → write tables; prune step repeats the same raise-after-filter discipline.
**Invariant:** LLM extraction treats empty graphs as FATAL; the NLP fast path currently does NOT for edges (log-only) — a porter must CHOOSE which semantics to port and not assume the twins agree; raw snapshots capture PRE-summarization state by design; summarization merges are left-joins that DROP the old description column first (no stale descriptions survive).
**Probe:** no dedicated unit tests for these workflow files at this HEAD — behavior pinned transitively by `tests/unit/indexing/operations/` extractor tests and golden-file community tests; coverage caveat recorded here (including this capsule's own bug documentation).
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "graphrag", query: "extract_graph get_summarized_entities_relationships filter_orphan_relationships prune_graph", limit: 10 })`

## Verdict
Adopt fail-fast-on-empty extraction, pre-summarization raw snapshots, and the temp-column id inheritance trick; adapt model wiring. Record the NLP-twin asymmetry wherever you port both paths — it is upstream's bug, not a spec.
