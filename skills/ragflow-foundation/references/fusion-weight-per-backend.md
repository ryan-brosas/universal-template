<!-- capsule-v2 -->
# fusion-weight-per-backend — which weights reach the store's fusion expression?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ext-ragflow`. **Question:** A porter wiring a new doc engine must know exactly what fusion weight string each backend receives and why ES differs.

## Per-backend fusion-weight selection
**Path/Symbol:** `rag/nlp/search.py:35-42` (`build_fusion_expr`) and `Dealer.search` `rag/nlp/search.py:220-233`.
**Signature:** `build_fusion_expr(topn: int, vector_similarity_weight: float = 0.3) -> FusionExpr`.
**Data Shape:** `FusionExpr("weighted_sum", topk, {"weights": "<term>,<vector>"})`; weights are `%g`-formatted complements (`term = 1 - vector`). The string form is load-bearing — Infinity parses it as an expression, not JSON.

### Decisive source
```python
def build_fusion_expr(topn: int, vector_similarity_weight: float = 0.3) -> FusionExpr:
    term_similarity_weight = 1 - vector_similarity_weight
    return FusionExpr(
        "weighted_sum",
        topn,
        {"weights": f"{term_similarity_weight:g},{vector_similarity_weight:g}"},
    )
```

**Flow:** In `Dealer.search`, after building `matchText`/`matchDense`: Infinity → `build_fusion_expr(topk, req["vector_similarity_weight" or 0.3])`; GaussDB → inline `FusionExpr("weighted_sum", topk, {"weights": f"{1-float(w)},{float(w)}"})` (same semantics, no `%g`); every other engine including Elasticsearch → hardcoded `{"weights": "0.001,1"}`. The fused result is appended as third match expr only when `matchText` is non-empty; dense-only queries pass `[matchDense]` with no fusion.
**Invariant:** ES never receives user weights in the fusion expr — its `_score` is rescored client-side later (see es-vectorless-rerank). A porter who forwards `vector_similarity_weight` into the ES path double-applies the weight.
**Probe:** `sed -n '232p' rag/nlp/search.py | grep -c '0.001,1'` → `1` (ES default literal exists exactly once); direct tests pin both sides: `test/unit_test/rag/test_search_fusion_weight.py:121-145` asserts `"0.2,0.8"` for Infinity at weight 0.8, `:149-173` asserts `"0.001,1"` when `DOC_ENGINE_INFINITY=False`, `:176-190` parametrizes `(0.0,"1,0") (0.3,"0.7,0.3") (0.5,"0.5,0.5") (1.0,"0,1")`. Executed GREEN: full suite 6/6 at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ragflow", query: "build_fusion_expr weighted_sum weights vector_similarity_weight", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the complement-of-vector-weight string contract and the three-backend switch; adapt GaussDB's inline formatting if your host lacks `%g` rounding parity; omit SereneDB/OceanBase vector-fetch branches if porting the ES path. Direct-test coverage is strong (dedicated suite).
