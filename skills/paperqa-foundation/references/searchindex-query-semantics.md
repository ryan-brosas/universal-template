<!-- capsule-v2 -->
# SearchIndex query semantics — what cleaning runs before tantivy, and how do field subsets, offsets, and stored-blob hydration work?

**Source:** paper-qa (Apache-2.0) `main@57e89f7223b0960d5ee5ea048c69e3c47e088572`; Codebase Memory `paper-qa`. **Question:** How does a raw LLM-authored query string survive tantivy's parser, and what is the exact shape of paginated, score-filtered results?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/agents/search.py:SearchIndex.query` (:399-434), `CLEAN_QUERY_REGEX` (:397), `searcher` (:221-226); `src/paperqa/utils.py:clean_possessives` (:654-668).
**Signature:** `async def query(self, query: str, top_n: int = 10, offset: int = 0, min_score: float = 0.0, keep_filenames: bool = False, field_subset: list[str] | None = None) -> list[Any]`.
**Data Shape:** Hits are `(score, doc_address)` from `searcher.search(parsed_query, top_n, offset)`; scores filtered by `min_score` AFTER retrieval; each address hydrates the STORED object via `get_saved_object` — a full `Docs` (pickle/zip) or JSON dict depending on the index's `storage`; `keep_filenames=True` returns `(object, file_location)` tuples.

### Decisive source
```python
query_fields = list(field_subset or self.fields)
cleaned_query = self.CLEAN_QUERY_REGEX.sub("", query)      # [*[]:(){}~^><+"\]
try:
    parsed_query = index.parse_query(cleaned_query, query_fields)
except ValueError:  # Rejected by tantivy
    # Retry with more aggressive cleaning
    parsed_query = index.parse_query(clean_possessives(cleaned_query), query_fields)
addresses = [s[1] for s in searcher.search(parsed_query, top_n, offset=offset).hits if s[0] > min_score]
```

**Flow:** strip special chars → parse against chosen fields → on ValueError degrade to possessive-stripped text and re-parse (never surface a parse error to the caller) → search with offset cursor → threshold-filter scores → hydrate stored objects. `self.searcher` lazily opens AND `index.reload()`s, so long-lived indexes observe concurrent writers' commits.
**Invariant:** Query parsing NEVER fails upward — worst case it searches degraded text; `min_score` is applied post-pagination so `top_n` counts pre-filter hits (you can receive fewer than `top_n` results even when more matched); offset pagination is the CALLER'S responsibility to advance (the PaperSearch tool keeps `previous_searches[(query, year)]` cursors — see agent-tool-loop-status).
**Probe:** `tests/test_agents.py::test_get_directory_index` (:102-119) — `"Who is 'Bates'"` and `"What is Bates' first name"` must return results (possessive/apostrophe survival); :103 pins `min_score=5` returning the bates.txt doc first; `tests/test_cli.py::test_cli_can_build_and_search_index` (:72-92) pins `keep_filenames` tuple shape (`result[0][1] == "paper.pdf"`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "paper-qa", query: "parse_query clean_possessives searcher.reload get_saved_object keep_filenames", limit: 10 });
```

## Verdict
Adopt two-stage query sanitization + post-score filtering + lazy reload-before-search for any tantivy/lucene-style keyword plane fed by LLM strings; adapt the storage enum choice (JSON for cross-language reads like the answers index; pickle for rich Python objects); omit blob hydration entirely if you only need doc addresses. Coverage caveat: exact regex char class verified at source (:397); tantivy parse-reject behavior pinned by tests, not by fuzzing.
