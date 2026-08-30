<!-- capsule-v2 -->
# LIKE hint prefilter — how do you make regex search over a big table fast without wrong answers?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you combine an index-satisfying LIKE prefilter with a full regex without introducing false negatives?

## Literal-segment extraction, alternation bail-out
**Path/Symbol:** `src/store/store.c:cbm_extract_like_hints` (4085–4150) + `where_add_like_hints` (4297–4316) + `where_add_regex` (4280–4291).
**Signature:** `int cbm_extract_like_hints(const char *pattern, char **out, int max_out);`
**Data Shape:** Hints = literal segments between regex metacharacters, each wrapped `%hint%` and bound as `col LIKE ?`; the ORIGINAL pattern still applies as `col REGEXP/iregexp(?)` (case-sensitive uses `REGEXP`, default insensitive `iregexp(pattern, col)`).

### Decisive source
```c
/* Bail on alternation — can't convert OR regex to AND LIKE */
for (const char *p = pattern; *p; p++) { if (*p == '|') return 0; }
...
/* Prepend LIKE pre-filter conditions for literal segments of a regex pattern.
 * The idx_nodes_name index satisfies LIKE '%literal%', cutting the rows that
 * reach the (more expensive) iregexp call ... bails on alternation, so no
 * false negatives. */
```

**Flow:** parse user regex → if it contains `|`, skip hints entirely (AND-composition of LIKEs is only sound for conjunctive literals) → else emit one `%lit%` per literal run → WHERE becomes `(LIKE hints...) AND (regexp ...)` → index narrows candidates, custom regexp function (regex cached via sqlite3_set_auxdata per statement, compiled once not per row) decides.
**Invariant:** Hints are a pure optimization: any pattern the extractor cannot safely translate must yield ZERO hints rather than partial ones; the regexp predicate alone decides membership.
**Probe:** `tests/test_store_search.c` around 1050–1090 (`cbm_extract_like_hints(".*handler.*")`, `"^handleRequest$"`, alternation cases) plus `store_glob_to_like`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_extract_like_hints", limit: 5 });
```

## Verdict
Adopt "hints are advisory, regex decides" for hybrid text filtering; adapt to your SQL dialect's index rules; omit the auxdata regex cache only if your engine compiles patterns natively.
