<!-- capsule-v2 -->
# empty-retrieval-retry-ladder — how does Dealer avoid zero-hit answers?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ext-ragflow`. **Question:** What relaxation steps run when the first hybrid search returns total==0, and in what order?

## Zero-total retry ladder
**Path/Symbol:** `Dealer.search` `rag/nlp/search.py:202-261` (retry arm `:240-260`).
**Signature:** first attempt `self.qryr.question(qst, min_match=(0.3 if min_match else 0))`; retry `min_match=(0.1 ...)`; `matchDense.extra_options["similarity"] = 0.17`.
**Data Shape:** `total == 0` triggers exactly one retry; two mutually exclusive arms keyed on `filters.get("doc_id")`.

### Decisive source
```python
# If result is empty, try again with lower min_match
if total == 0:
    if filters.get("doc_id"):
        res = await thread_pool_exec(self.dataStore.search, src, [], filters, [], orderBy, offset, limit, idx_names, kb_ids)
        total = self.dataStore.get_total(res)
    else:
        matchText, _ = self.qryr.question(qst, min_match=(0.1 if min_match else 0))
        matchDense.extra_options["similarity"] = 0.17
        res = await thread_pool_exec(... [matchText, matchDense, fusionExpr] ...)
```

**Flow:** attempt 1 (`min_match=0.3` unless caller passed `vector_similarity_weight >= 0.8` → `min_match=False`→0) → total==0? → doc_ids-filtered query drops ALL match exprs (pure filter scan by design; a scoped lookup must not relax text matching) → otherwise rebuild text expr at `min_match=0.1` AND raise dense similarity floor 0.1→0.17 (looser lexical, stricter vector — deliberate opposite moves), re-search once. No further retries.
**Invariant:** the retry mutates `matchDense.extra_options["similarity"]` IN PLACE on the same MatchDenseExpr object reused from attempt 1; a porter rebuilding expressions must preserve that mutation or clone it. `min_match=False` callers never relax below their explicit opt-out.
**Probe:** `grep -n 'min_match=(0.' rag/nlp/search.py` → exactly lines 202 and 245 (`0.3` then `0.1`); `grep -n '"similarity"\] = 0.17' rag/nlp/search.py` → 1 hit at :246. Both executed GREEN at pin; behavior pinned indirectly by `test/unit_test/rag/nlp/test_gaussdb_retrieval.py` dealer-search tests (9/9 executed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ragflow", query: "Dealer search min_match retry similarity 0.17", limit: 5, fields: ["name", "file"] });
```

## Verdict
Adopt the ordered two-arm single-retry shape and the doc_id short-circuit; adapt threshold constants to your tokenizer's match distribution; omit the OceanBase/SereneDB src-append side branch (backend-specific field transport).
