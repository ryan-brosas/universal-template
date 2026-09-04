<!-- capsule-v2 -->
# MinHash/LSH clone detection — how do you find near-clone functions at repo scale without pairwise comparison?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What fingerprint, LSH geometry, and emission caps make SIMILAR_TO edges cheap AND deterministic?

## Leaf-token MinHash + 32×2 banded LSH + QN-order pair ownership
**Path/Symbol:** `src/simhash/minhash.h` (constants 25–39) + `cbm_minhash_jaccard` (minhash.c 269–280) + candidate gating in `src/pipeline/pass_similarity.c:225–258`.
**Signature:** `double cbm_minhash_jaccard(const cbm_minhash_t *a, const cbm_minhash_t *b);`
**Data Shape:** Signature = K=64 min-hash values over leaf-AST tokens (identifiers normalized); MIN_NODES=30 leaf tokens minimum (≈ BigCloneBench's 50 raw tokens); LSH: CBM_LSH_BANDS=32 bands × CBM_LSH_ROWS=2 rows ⇒ threshold ≈ (1/32)^(1/2) ≈ 0.18 recall band with Jaccard decision at 0.95; ≤10 edges per node.

### Decisive source
```c
/* Pair ownership by canonical QN order, not node id: ids are assigned in
 * parallel-merge order and vary run to run, which flipped which side owned a
 * pair and (with the per-source edge cap) flickered the emitted set. */
if (!src->qn || !cand->qualified_name || strcmp(src->qn, cand->qualified_name) >= 0) continue;
...
double jaccard = cbm_minhash_jaccard(&src->fp, cand->fingerprint);
if (jaccard < CBM_MINHASH_JACCARD_THRESHOLD) continue;   /* 0.95 */
```

**Flow:** extraction fingerprints each function (trigram-weighted MinHash over normalized leaf tokens) → similarity pass buckets by LSH band → candidate pairs filtered to same file-extension → canonical-QN ordering decides the source side → Jaccard ≥0.95 emits a SIMILAR_TO edge with `{jaccard,same_file}` properties → per-node atomic count enforces the 10-edge cap.
**Invariant:** Determinism requires identity from CONTENT (QN), never from parallel-assigned ids; extension gate keeps cross-language false clones out.
**Probe:** `tests/test_simhash.c:minhash_identical_source_same_fingerprint`, `minhash_renamed_vars_same_fingerprint`, `lsh_same_bucket_similar`; end-to-end `tests/test_lang_contract.c:contract_edge_similar_to`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_minhash_jaccard", limit: 5 });
```

## Verdict
Adopt banded-LSH MinHash with content-derived pair ownership; adapt token normalization and thresholds to your language mix; omit RaBitQ quantization unless you also need dense embedding storage (`src/semantic/rotsq.h`).
