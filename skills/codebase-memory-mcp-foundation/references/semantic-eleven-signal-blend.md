<!-- capsule-v2 -->
# Semantic edge scoring — can you build SEMANTICALLY_RELATED links with zero external models?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What signal mix, weights, and thresholds produce useful vocabulary-mismatch edges from pure graph metadata?

## 11-signal blend, 0.75 threshold, 10-edge cap
**Path/Symbol:** `src/semantic/semantic.h` (signals 1–29, config 40–85) + `cbm_sem_corpus_idf` (semantic.c 1442–1455) + pass wiring `src/pipeline/pass_semantic_edges.c:cbm_pipeline_pass_semantic_edges` (1359+).
**Signature:** `float cbm_sem_corpus_idf(const cbm_sem_corpus_t *c, const char *token);` / `cbm_sem_config_t cbm_sem_get_config(void);`
**Data Shape:** Signals: TF-IDF on metadata tokens; Random Indexing (CBM_SEM_DIM=768, NNZE=8) with co-occurrence window 5 and frequent-token subsampling cap 512; MinHash structural reuse; API-signature vectors (same callees); type-signature vectors; module proximity multiplier; decorator vectors; 25-dim AST profile (control flow/nesting/Halstead-lite); params→return dataflow; graph diffusion. Weights sum ≈1.0; threshold default 0.75; max 10 edges/node.

### Decisive source
```c
/* Default score threshold for SEMANTICALLY_RELATED edge emission.
 * 0.75 balances recall with precision: validated ~95% precision on
 * Linux kernel (0.80 = 100% but only 90 edges, 0.70 = 2047 edges
 * but ~80% precision). */
#define CBM_SEM_EDGE_THRESHOLD 0.75
/* Frequent-token subsampling ... an evenly-spaced subsample preserves its
 * DIRECTION while bounding the work. Mirrors word2vec/GloVe subsampling. */
enum { CBM_SEM_MAX_OCCUR = 512 };
```

**Flow:** post-pass after similarity in FULL/MODERATE only → tokenize names via camel/snake/dot splitter with abbrev expansion → corpus TF-IDF + RI enrichment → candidate LSH → blended score per pair → diffusion spreads scores over neighbors → emit top-≤10 SEMANTICALLY_RELATED per node above threshold.
**Invariant:** Threshold was tuned against measured precision/recall — do not "fix" it without a corpus; subsampling must preserve direction (post-normalization), not magnitude.
**Probe:** `tests/test_semantic.c:sem_corpus_idf`, `sem_random_index_deterministic`, `sem_proximity_same_dir`, `sem_rotsq_ip_error_bounds` (4-bit quantized IP error well under the 0.75 decision margin); end-to-end presence by `tests/test_lang_contract.c:contract_edge_semantically_related`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_sem_corpus_idf", limit: 5 });
```

## Verdict
Adopt the multi-signal blend when embeddings are unavailable; adapt weights via env-overridable config; omit RaBitQ codes unless you persist dense vectors alongside.
