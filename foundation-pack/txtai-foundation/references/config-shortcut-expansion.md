<!-- capsule-v2 -->
# Config shortcut expansion — keyword/sparse/hybrid/dense booleans compile into concrete component configs

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How do top-level boolean shortcuts expand into scoring/vectors/ANN components, and when does the default embedding model load?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/embeddings/base.py:Embeddings.defaults` (:824-847), `.defaultsparse` (:849-876), `.defaultallowed` (:878-887), `.loadvectors` (:889-907), `.createann` (:959-971).
**Signature:** `defaults()` mutates `self.config` in place; called from initindex/batchtransform.
**Data Shape:** shortcut keys: `keyword|sparse|hybrid: bool|str`, `dense: bool|str(path)`, `defaults: bool`; expanded into `scoring {method, terms, normalize}`, `path`, `dense`.

### Decisive source
```python
# defaultsparse
method = None
for x in ["keyword", "hybrid"]:
    value = self.config.get(x)
    if value:
        method = value if isinstance(value, str) else "bm25"
        # Enable dense index when hybrid enabled
        if x == "hybrid":
            self.config["dense"] = True

sparse = self.config.get("sparse", {})
if sparse or method == "sparse":
    sparse = {"path": self.config.get("sparse")} if isinstance(sparse, str) else {} if isinstance(sparse, bool) else sparse
    sparse["path"] = sparse.get("path", "opensearch-project/opensearch-neural-sparse-encoding-doc-v2-mini")
    self.config["scoring"] = {**{"method": "sparse"}, **sparse}
elif method:
    self.config["scoring"] = {"method": method, "terms": True, "normalize": True}
```
```python
# defaults — default model gate
if not self.model and (self.defaultallowed() or self.config.get("dense")):
    self.config["path"] = "sentence-transformers/all-MiniLM-L6-v2"
    self.model = self.loadvectors()

# defaultallowed — keyword/sparse present means NO default model unless explicitly allowed
params = [("keyword", False), ("sparse", False), ("defaults", True)]
return all(self.config.get(key, default) == default for key, default in params)
```

**Flow:** any of keyword/sparse/hybrid set (and no explicit scoring) → expand to a bm25/tfidf/sparse scoring config; hybrid ALSO flips dense=True so the dense model loads → default MiniLM path loads only when no keyword/sparse shortcut is active or `dense` is truthy → createann builds an ANN only if a model path exists or defaults are allowed (`config["path"] or defaultallowed()`) — a pure keyword index has NO ann.

**Invariant:** `keyword: True` yields `{method: bm25, terms: True, normalize: True}` — normalize ON is what routes hybrid to convex fusion instead of RRF. The default-model gate prevents surprise model downloads for keyword-only indexes. String values name alternate scoring methods (`hybrid: "tfidf"`). Scoring expansion happens at index time via hassparse() check in initindex (:786-822) — configure-time creates term-weighting scoring ONLY when scoring is NOT sparse.

**Probe:** `test/python/testembeddings.py:testShortcuts` (:473-495 — asserts exact component lists per shortcut combo), `testKeyword` (:328+), `testDefaults` (:99-109).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "defaults sparse hybrid keyword defaultallowed scoring", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the expansion table + no-default-model-under-shortcuts rule + conditional ANN creation; adapt default model path; omit sparse-vector default model reference if unused.
