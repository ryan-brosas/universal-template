<!-- capsule-v2 -->
# Explain token attribution — leave-one-out scoring via n similarity passes

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How must per-token importance be computed for a query-text pair without gradient access to the embedding model?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/embeddings/search/explain.py:Explain.explain` (:66-118), `.texts` (:38-60); entry `embeddings/base.py:batchexplain` (:464-478).
**Signature:** `Explain(embeddings)(queries, texts, limit)` → list of dicts `{id, text, score, tokens: [(token, importance)]}`.
**Data Shape:** texts either provided (similarity path) or fetched via batchsearch when content enabled; requires `score` + `text` keys in result dicts.

### Decisive source
```python
# Create permutations of input text, masking each token to determine importance
permutations = []
for i in range(len(tokens)):
    data = tokens.copy()
    data.pop(i)
    permutations.append([" ".join(data)])

# Calculate similarity for each input text permutation and get score delta as importance
scores = [(i, result["score"] - abs(s)) for i, s in self.embeddings.similarity(query, permutations)]

# Append tokens to result
result["tokens"] = [(tokens[i], score) for i, score in sorted(scores, key=lambda x: x[0])]
```

**Flow:** resolve texts (given list or content-backed search) → optional SQL parse to extract the similar() clause text when a database exists → guard: return originals if no query/text/score → per text: tokenize on whitespace (or use token list) → build n leave-one-out permutations → ONE batch similarity call ranks all permutations against the query → token importance = original score − |permuted score| (removal cost) → tokens emitted in ORIGINAL index order; result list sorted by score desc.

**Invariant:** abs() on the permutation score means removal can raise or lower similarity — importance is signed relative to the ORIGINAL score. n+1 total embeddings per text (1 original + n masked) — batching all permutations into one similarity() call is what keeps this O(1) network round-trips. When the database parses a SQL query, only the similar-clause text is embedded as "query" — filters never reach the model.

**Probe:** `test/python/testembeddings.py:testExplain`-family (content and non-content paths pin dict shape `tokens` key ordering).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "Explain permutations tokens score importance", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt leave-one-out batched attribution + similar-clause extraction; adapt tokenizer (whitespace here); omit if you have native explainability. Coverage caveat: pinned by integration tests requiring model download.
