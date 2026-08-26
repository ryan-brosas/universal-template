<!-- capsule-v2 -->

# Sitemap/CC discovery with lastmod-validated caching — What makes a cached sitemap URL list trustworthy, and how do nested sitemap indexes fan out without unbounded memory?

**Source:** crawl4ai Apache-2.0 `main@7e801521428ee12509994d39151006f64055ebe3`; Codebase Memory `ext-crawl4ai`. **Question:** What makes a cached sitemap URL list trustworthy, and how do nested sitemap indexes fan out without unbounded memory?

## Discovery ladder + validated cache envelope

**Path/Symbol:** `crawl4ai/async_url_seeder.py:_from_sitemaps (885-997), _iter_sitemap_content (999-1103), _from_cc (829-882), _is_cache_valid (96-143)`.

**Signature:** `cache_path = cache_dir/f"sitemap_{host_safe}_{digest}.json" where digest=md5(pattern)[:8]; _is_cache_valid(path, ttl_hours, validate_lastmod, current_lastmod) -> bool`.

**Data Shape:** Envelope {version:1, created_at ISO, sitemap_lastmod, sitemap_url, url_count, urls[]}. CC mirror: {index_id}_{safe}_{digest}.jsonl, one URL per line.

### Decisive source
```python
schemes = ('https', 'http')
        for scheme in schemes:
            for suffix in ("/sitemap.xml", "/sitemap_index.xml"):
                sm = f"{scheme}://{host}{suffix}"
                resolved = await self._resolve_head(sm)
                if resolved:
                    sitemap_url = resolved
                    ...sitemap_lastmod = _parse_sitemap_lastmod(sitemap_content)...
        ...
        if not force and cache_path.exists():
            if _is_cache_valid(cache_path, cache_ttl_hours, validate_lastmod, sitemap_lastmod):
                ...yield from cache...
                return
```

**Flow:** Resolve candidate sitemaps by single-hop-verified HEAD (https before http; direct 2xx or verified 3xx target; self-redirect rejected) -> fetch content ONCE and parse max lastmod (namespace-agnostic xpath) -> validate cache: version==1 AND within TTL AND cached lastmod >= current lastmod AND url_count>0 -> valid: yield-through pattern filter; else refetch -> index documents detected by presence of <sitemap> loc nodes fan out to per-sub-sitemap tasks feeding a bounded result_queue; each task enqueues sentinel None; consumer counts sentinels to completion -> robots.txt 'Sitemap:' lines are the final fallback -> CC path streams index.commoncrawl.org NDJSON, writing each URL to the jsonl mirror WHILE yielding matches, with 503 retried after 1/3/7s (final -1 = give up).

**Invariant:** (1) lastmod comparison is STRING max (ISO timestamps sort lexicographically) - mixed formats silently misorder; the code accepts this tradeoff. (2) Corrupted cache (JSONDecodeError/KeyError/zero-count) returns invalid -> refetch, never raise. (3) Cache write failure is swallowed AFTER yielding - URLs already delivered are not lost. (4) Index fan-out preserves lazy semantics: the async generator yields as sentinels arrive, capped queue backpressures slow consumers. (5) loc text is stripped of zero-width spaces/BOM and urljoin'd against the sitemap URL.

**Probe:** `tests/cache_validation/` (validator-side analogues) + seeder units under `tests/unit/`; live behavior pinned by `_resolve_head` redirect matrix (301/302/303/307/308 verified-target-or-None)

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-crawl4ai", "query": "from_sitemaps _iter_sitemap sitemap cache lastmod", "limit": 5}'
```

## Verdict
Adopt the discovery ladder, the versioned-cache envelope with the four invalidation triggers, and the write-while-streaming CC mirror. Adapt TTLs and hosts. Note the deliberate asymmetry: sitemap caches are whole-run JSON with lastmod revalidation; CC mirrors are append-only jsonl re-filtered by glob at read - porting either shape onto the other loses incremental yielding or freshness.
