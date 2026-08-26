<!-- capsule-v2 -->
# search_code line-exact probe — when BM25 can't find it, what primitive still resolves a needle?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How does search_code complement FTS for doc files and non-symbol text?

## Raw substring scan with file-pattern filter
**Path/Symbol:** `src/store/store.c` content-scan backing + tests/test_store_arch.c:461 (`store_search_code_finds_line_exact_match`); tool wiring in mcp.c.
**Signature:** `int cbm_store_search_code(cbm_store_t *s, const char *project, const char *pattern, const char *file_glob, int limit, cbm_code_hit_t **out, int *count);`
**Data Shape:** Scans stored file contents (or on-disk under root) for literal pattern; optional glob narrows to e.g. `*.mdx`; hits carry path + 1-based line + excerpt; complements FTS which indexes identifiers only.

### Decisive source
```c
TEST(store_search_code_finds_line_exact_match) { ... }
```

**Flow:** validate pattern → iterate candidate files (glob-filtered) → byte scan per line → collect first N hits → emit. This is the retrieval plane that works on DOC-shaped repos where BM25 token tables miss prose needles.
**Invariant:** Literal matching (no regex surprises) is the point — this is the fallback that must never fail to find an exact string the indexer saw.
**Probe:** the named test; cross-check with like-hint capsule for regex-side optimization.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "search_code", limit: 5 });
```

## Verdict
Adopt a literal line scanner as the guaranteed floor under any fancy retrieval stack; adapt storage source; cap results.
