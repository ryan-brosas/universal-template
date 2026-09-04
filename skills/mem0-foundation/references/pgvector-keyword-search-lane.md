<!-- capsule-v2 -->
# PGVector keyword_search — how does the pgvector backend serve the BM25 lane, and why does failure return None instead of raising?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** what contract must a SQL vector store satisfy to plug into mem0's hybrid scoring keyword lane?

## Connected graph-selected seam
**Path/Symbol:** `mem0/vector_stores/pgvector.py`: `PGVector.keyword_search` (:369-403); GIN index provisioned at `create_col` (:301-309).
**Signature:** `keyword_search(self, query: str, top_k: int = 5, filters: Optional[dict] = None) -> Optional[List[OutputData]]`.
**Data Shape:** query is the ALREADY-lemmatized text (`lemmatize_for_bm25` output) — the store never lemmatizes itself; it searches the `payload->>'text_lemmatized'` JSONB field written by the BM25 write-path capsule. Returns OutputData(score=ts_rank_cd relevance, DESC) or None on any error.

### Decisive source
```python
cur.execute(sql.SQL("""
    SELECT id, ts_rank_cd(to_tsvector('simple', payload->>'text_lemmatized'),
                         plainto_tsquery('simple', %s)) AS score, payload
    FROM {}
    WHERE to_tsvector('simple', payload->>'text_lemmatized') @@ plainto_tsquery('simple', %s)
    {}
    ORDER BY score DESC
    LIMIT %s
""").format(self._col(), filter_clause),   # filter_clause = "AND ..." (search uses "WHERE ...")
(query, query, *filter_params, top_k))
...
except Exception as e:
    logger.debug(f"Keyword search failed: {e}")
    return None
```

**Flow:** hybrid search calls `vector_store.keyword_search(query=lemma_text)` → tsvector match over the materialized lemma column ranked by `ts_rank_cd` → caller (`main.py` :1647/:3312) treats None as "no keyword evidence" and proceeds semantic-only; capability probe at init (:543) compares `type(store).keyword_search` against `VectorStoreBase.keyword_search` and logs that hybrid is disabled when un-overridden.
**Invariant:** the base class's default `keyword_search` RAISES NotImplementedError while this override returns None on failure — the None-not-raise contract is load-bearing because the hybrid path runs keyword search opportunistically inside a larger pipeline and `if keyword_results is not None` gates BM25 fusion; filter params splice with an AND-prefixed clause here vs WHERE-prefixed in vector search (same `_build_filter_conditions`, different join word). Capability probing happens at BOTH init ladders — sync `Memory.__init__` (main.py :543-549) and async (main.py :2208-2214) — so porters adding a third entry point must repeat the sniff.
**Probe:** `grep -n "ts_rank_cd" mem0/vector_stores/pgvector.py` (exactly ONE site, :389 SELECT; the ranking expression appears only there while `plainto_tsquery` appears twice, :389+:391); `grep -c "does not support keyword search" mem0/memory/main.py` (=2: sync :545 + async :2210).
**Direct test:** `tests/vector_stores/test_pgvector.py::test_search_psycopg*` family covers the filter-splice machinery; live-server score semantics pinned cross-backend in `tests/vector_stores/test_score_normalization.py::TestPGVector::test_scores_are_similarity` (:231, needs a running pgvector — recorded as env-gated).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "keyword_search ts_rank_cd text_lemmatized pgvector", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the None-on-failure keyword lane + init-time capability sniffing for any optional-capability backend; adapt the FTS engine (tsvector→your engine's rank function); omit nothing from the lemma-column coupling — pointing keyword_search at raw text silently breaks recall parity with the write-path capsule. Env-gated live-server test caveat recorded in-capsule.
