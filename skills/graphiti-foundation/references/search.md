<!-- capsule-v2 -->
# Search orchestrator — pay for embeddings only when needed

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how does graph retrieval decide whether to embed a query, and how does it short-circuit empty queries?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/search/search.py` (874 lines): `search` (top-level); `search/search_utils.py` (2,048 lines); `search/search_config_recipes.py`.
**Signature:** `search(query, ...)` — short-circuits empty queries to an empty `SearchResults`; decides whether the query needs embedding AT ALL (only if some configured scope uses cosine similarity or an MMR reranker).
**Data Shape:** zero sentinel vector `[0.0] * EMBEDDING_DIM` (:141-152) keeps signatures uniform without Optional plumbing; BM25-only configs never pay for embedding.

### Decisive source
```ts
# Top-level search() short-circuits empty queries to an empty SearchResults,
# then decides whether the query needs embedding AT ALL — only if some
# configured scope uses cosine similarity or an MMR reranker.
# Otherwise a zero sentinel vector ([0.0] * EMBEDDING_DIM, :141-152) keeps
# signatures uniform without Optional plumbing. Embedding is the expensive
# external call; BM25-only configs never pay for it.
# Newlines are stripped pre-embed because some embedders/indexes treat them poorly (:148)
```

**Flow:** search short-circuits empty queries, then decides embedding need (cosine/MMR scopes only); a zero sentinel keeps signatures uniform; newlines stripped pre-embed. Retrieval runs across the configured scopes (BM25, cosine, MMR rerank).
**Invariant:** embedding is only paid for when a scope needs it (BM25-only configs skip); empty queries return empty results; signatures stay uniform via the sentinel.
**Probe:** `tests/` search tests (empty query returns empty; BM25-only config skips embedding; cosine/MMR scope embeds; newline stripping).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "search orchestrator embed cosine MMR BM25 sentinel short-circuit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the search orchestrator (short-circuit empty, embed only when needed, zero sentinel, newline stripping); adapt the scopes and reranker to host.
