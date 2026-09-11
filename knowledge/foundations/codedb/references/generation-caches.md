<!-- capsule-v2 -->
# Generation-keyed result-cache fleet (SearchResultCache / PlainRenderCache / env fingerprint) — what makes caching search results safe while lazy signals build mid-flight?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** How do you cache query results whose correctness depends on lazily-built ranking signals and env toggles?

## gen + env_fp double validation with conservative read-before-write
**Path/Symbol:** `src/explore.zig` (`SearchResultCache` :1137–1313, `sanitizeCachedBreakdown` :1318–1325, `PlainRenderCache` :1331–1448, `rankingEnvFingerprint` :1685–1702, front-door `searchContent` :4190–4207; siblings `FuzzyFileCache` :1457, `TreeRenderCache` :1544, `OutlineRenderCache` :1588).
**Signature:** key = `(query ≤1024 chars, max_results)`; validity = `entry.gen == search_gen (acquire-read BEFORE running) AND entry.env_fp == fingerprint(CODEDB_NO_CENTRALITY, NO_GRAPH_DISTANCE, NO_COCHANGE, LEX_FREQ_PENALTY, LEX_FREQ_AMP, RVSM_SIZE_PRIOR, RVSM_AMP, RVSM_K, IN_DEGREE_CENTRALITY)`.
**Data Shape:** 64 entries / 4 MiB / max 1 MiB per entry; LRU via tick counter; hits copy cached strings into the CALLER's allocator (identical ownership contract as fresh results); breakdown sanitized at put (timings zeroed, cache_hit=true).

### Decisive source
```zig
// The generation is read BEFORE the search runs, so any concurrent mutation
// makes the stored entry stale immediately — conservative in the safe
// direction. Lazy builds during a query's FIRST run bump the generation
// mid-search; that entry just never hits and the next run stores a valid one.
const gen = self.search_gen.load(.acquire);
const env_fp = rankingEnvFingerprint();
if (self.search_cache.get(query, max_results, gen, env_fp, allocator, &self.last_search_breakdown)) |hit| return hit;
const res = try self.searchContentUncached(query, allocator, max_results);
self.search_cache.put(query, max_results, gen, env_fp, res, self.last_search_breakdown);
```

**Flow:** mutation paths (`indexFile`, remove, word rebuilds, symbol/call-graph/co-change lazy builds) call `bumpSearchGen()` AT THE MOMENT the signal becomes available → readers sample gen+env_fp before searching → stale-or-mismatched entries are dropped ON GET (slot refills) → put replaces same-key entries then LRU-evicts. Render-level caches mirror the discipline for plain-text MCP output so both surfaces rank identically from the same engine state.
**Invariant:** A hit can NEVER observe state a fresh search would not have produced — this is the entire safety argument; OOM mid-copy falls through to a fresh search (never partial results); `CODEDB_NO_SEARCH_CACHE=1` disables for honest benchmarking.
**Probe:** `grep -n "bumpSearchGen" src/explore.zig` lists every invalidation site (mutation + each lazy build incl. ensureCoChange/ensureCallGraph tails); `src/test_search.zig` cache-related audit tests; config tests pin `codedbrc max_cached threads through to ContentCache capacity` (src/test_core.zig).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", name_pattern: "SearchResultCache", limit: 10 });
```

## Verdict
Adopt generation+fingerprint dual keying for caches above any lazily-completing engine; adapt fingerprint variable set to your knobs; omit the render-cache twins if your API returns structured results only.
