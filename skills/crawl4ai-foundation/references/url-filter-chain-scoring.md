<!-- capsule-v2 -->

# Filter chain: sync short-circuit + concurrent async gather, categorized pattern matching — How does a chain of mostly-sync URL filters avoid serializing on the rare async one, and how do glob patterns get fast paths?

**Source:** crawl4ai Apache-2.0 `main@7e801521428ee12509994d39151006f64055ebe3`; Codebase Memory `ext-crawl4ai`. **Question:** How does a chain of mostly-sync URL filters avoid serializing on the rare async one, and how do glob patterns get fast paths?

## Hybrid apply + typed pattern buckets

**Path/Symbol:** `crawl4ai/deep_crawling/filters.py:FilterChain.apply (91-116); URLPatternFilter (119-256)`.

**Signature:** `@lru_cache(maxsize=10000) def apply(self, url: str) -> bool  # filter-level; async chain-level apply`.

**Data Shape:** FilterStats uses array('I',[total,passed,rejected]) counters. Patterns bucketed: SUFFIX(*.html)/PREFIX(/foo/*)/DOMAIN(*.example.com)/PATH(glob->fnmatch.translate, **->.*, {a,b}->(a|b))/REGEX(starts ^, ends $, or contains \d).

### Decisive source
```python
tasks = []
        for f in self.filters:
            result = f.apply(url)
            if inspect.isawaitable(result):
                tasks.append(result)  # Collect async tasks
            elif not result:  # Sync rejection
                self.stats._counters[2] += 1  # Sync rejected
                return False
        if tasks:
            results = await asyncio.gather(*tasks)
            ...
```

**Flow:** Chain iterates filters: sync filters evaluated INLINE (first False aborts immediately, no event-loop yield); awaitable results collected then gathered CONCURRENTLY; pass requires all-True. URLPatternFilter.apply checks cheapest buckets first (suffix split -> domain regex -> prefix startswith with boundary char check -> compiled path patterns) with reverse= inverting the verdict at every return site; lru_cache(10000) memoizes per-instance verdicts.

**Invariant:** (1) Sync rejection returns BEFORE any async filter starts - a rejecting cheap filter suppresses expensive HeadPeekr-style checks entirely. (2) Prefix match requires the NEXT character in {'/', '?', '#'} (or exact-length equality) so '/foo/*' doesn't match '/foobar'. (3) DOMAIN patterns rewrite '*.' to '[^/]+'\ so subdomains match but path impostors don't. (4) In BFS link_discovery the chain runs at depth>=1 ONLY (start URL bypasses filters), and capacity trimming sorts valid_links by score DESCENDING before truncating to remaining_capacity - unscored crawls truncate insertion-order.

**Probe:** `tests/deep_crawling/` filter usage + `tests/test_normalize_url.py` (URL forms fed to filters); SEO/domain/content-type filters exercised in docs/examples/deep_crawling suites

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-crawl4ai", "query": "FilterChain apply URLPatternFilter", "limit": 5}'
```

## Verdict
Adopt the hybrid sync-short-circuit/awaitable-gather chain and the categorized-pattern matcher with its boundary rule. Adapt the tracking-param strip-list and threshold defaults. Beware porting the lru_cache onto a MUTATING filter - invalidation semantics differ (chain.add_filter rebuilds the tuple; URLPatternFilter caches per-instance and is effectively frozen post-init).
