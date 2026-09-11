<!-- capsule-v2 -->
# Lexical index tokenizer & scoring — how do you build a fast code-text search index with versioned token caches and a self-healing empty-index guard?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** How does a tantivy-based lexical index over code snippets get tokenized, cached, built, searched, and score-normalized — and which guards make it safe under concurrent/async build?

## tokenize_code + CustomIndex.search_index: filter-tokenized tantivy index with empty-searcher retry
**Path/Symbol:** `sweepai/core/lexical_search.py:tokenize_code` (:78–95), `CustomIndex.search_index` (:59–72), module-level `search_index` (:163–183), `get_lexical_cache_key` (:213–220), `prepare_index_from_snippets` (:111–158).
**Signature:** `tokenize_code(code: str) -> str`; `CustomIndex.search_index(self, query: str) -> list[tuple[str, float, dict]]`; `search_index(query: str, index: CustomIndex) -> dict[str, float]`.
**Data Shape:** docs are `(title, body)` where title = `"{rel_path}:{start}-{end}"` (repo-dir prefix stripped via `len_repo_cache_dir`); token cache is diskcache keyed `content + CACHE_VERSION` ("v1.0.16"); the whole-index/snippet cache key is `f"{basename(repo)}_{commit}_{CACHE_VERSION}_{seed}"` with commit defaulting to `git rev-parse HEAD`.

### Decisive source
```python
# tokenize_code — a part survives only if it looks like a real identifier fragment
for part in variable_pattern.findall(section):
    if len(part) < 2:
        continue
    # if more than half of the characters are letters
    # and the ratio of unique characters to the number of characters is less than 5
    if sum(1 for c in part if 'a' <= c <= 'z' or 'A' <= c <= 'Z' or '0' <= c <= '9') > len(part) // 2 \
        and len(part) / len(set(part)) < 4:
        tokens.append(part.lower())

# CustomIndex.search_index — "for some reason, the first searcher is empty"
for i in range(100):
    searcher = self.index.searcher()
    if searcher.num_docs > 0:
        break
    print(f"Index is empty, sleeping for {0.01 * i} seconds")
    time.sleep(0.01)
else:
    raise Exception("Index is empty")
results = searcher.search(query, limit=200).hits

# module search_index — min-max normalize to [0,1]
min_score = min(res.values()) if min(res.values()) < max_score else 0
res = {k: (v - min_score) / (max_score - min_score) for k, v in res.items()}
```

**Flow:** prepare_lexical_search_index (@streamable) → snippets from diskcache or `directory_to_chunks` → per-doc tokenization: cache hit by `content + CACHE_VERSION`, misses tokenized in a `multiprocessing.Pool(cpu_count() // 2)` and written back → `add_documents` (single writer, one commit) → search: `parse_query(tokenize_code(query))` → re-fetch searcher up to 100× with constant 0.01 s sleeps (the print message claims growing) until `num_docs > 0`, else raise → top-200 hits → per-doc scores min-max normalized (all-equal ⇒ all 1.0 via the min_score=0 guard; empty ⇒ {}).
**Invariant:** The tokenizer must reject repetitive/non-identifier noise (`len/unique < 4`) or the index degenerates on generated code; the empty-searcher retry loop is load-bearing — tantivy's first searcher after a commit can see zero docs, so a port that searches immediately will flake; CACHE_VERSION must be part of BOTH the token key and the index key so a tokenizer change invalidates every cached artifact at once; repo identity in the cache key is basename-only, so two same-named repos sharing a cache dir collide — a port should hash the full path or origin URL.
**Probe:** No offline-runnable test exists: `tests/search/test_lexical_search.py` is STALE at pin (line 1 imports `tokenize_call`, which does not exist — only `tokenize_code` does; the file is a copy of an old on_ticket harness referencing removed symbols) and its import chain blocks on missing `tantivy` (executed: `python3 -m unittest tests.search.test_lexical_search` → FAILED errors=1, ModuleNotFoundError tantivy). Deterministic probes at pin: `grep -c 'def tokenize_code' sweepai/core/lexical_search.py` → 1; `grep -n 'for i in range(100)'` → :63; `grep -n 'Index is empty'` → :67,:70; `grep -n 'limit=200'` → :71; `grep -n 'CACHE_VERSION = ' sweepai/core/lexical_search.py` → :26 only ("v1.0.16"); `grep -n 'cpu_count() // 2'` → :130,:132.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "tokenize_code CustomIndex search_index tantivy lexical", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source read of
// lexical_search.py (274L whole) at pin substituted — see verification.md pass 4.
```

## Verdict
Adopt the identifier-fragment tokenizer filters (length ≥ 2, letter-majority, uniqueness ratio < 4), the content+version keyed token cache with pool-only-miss tokenization, the bounded empty-searcher retry before raising, and the min-max normalization with its all-equal guard. Adapt the cache-key identity (use a full-path or origin hash, not basename) and the retry budget to your engine. Omit the print-in-loop progress (use a logger) and the bare `Exception("Index is empty")` (raise a typed error). Coverage caveat: no live direct test at pin (stale test file + missing tantivy dependency).
