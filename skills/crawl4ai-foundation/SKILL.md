---
name: crawl4ai-foundation
description: Use when building or porting async web crawlers - anti-bot retry/detection tiers, smart cache validation, memory-adaptive dispatch, deep-crawl traversal guards, sitemap/Common-Crawl seeding, and recycled browser fleets - capsule-v2 source maps with decisive excerpts and graph retrieval.
disable-model-invocation: true
---
# crawl4ai: async crawler foundations
## Use this for
Use when building or porting an async crawling engine: blocked-fetch recovery ladders, cache freshness without re-rendering, bounded-concurrency multi-URL dispatch, resumable deep-crawl traversals, URL discovery pipelines with hard rate caps, or long-lived browser-process fleets. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.
## Load the matching source dump
- `references/antibot-tiered-detector.md` - three detection tiers sized 15KB/<10KB/<50KB with data-response exemptions and 403/503-always-block.
- `references/antibot-retry-proxy-ladder.md` - attempts x proxies nesting, exception-swallow rule, fallback-fetch promotion, and the crawl_stats ledger every result carries.
- `references/smart-cache-freshness.md` - 304/head-fingerprint validation with FRESH/STALE/UNKNOWN/ERROR mapped to hit_validated/recrawl/hit_fallback.
- `references/content-hash-db-cache.md` - task-id-pooled aiosqlite (WAL) whose rows store content hashes pointing at filesystem blobs, UPSERTed with etag/lastmod/fingerprint metadata.
- `references/cache-mode-context.md` - five CacheModes collapsed onto should_read/should_write predicates with legacy-flag precedence.
- `references/deep-crawl-decorator-guard.md` - ContextVar latch installed by decorating arun at construction so nested arun calls fall through to single-URL mode.
- `references/bfs-level-loop-resume.md` - level-synchronous traversal cloning deep_crawl_strategy away per delegation, success-gated budgets, and a four-key resume snapshot.
- `references/url-filter-chain-scoring.md` - sync-inline/async-gather hybrid chain feeding scored-capacity-trimmed link selection with boundary-checked glob buckets.
- `references/seeder-pipeline-backpressure.md` - bounded queue + global QPS semaphore + drain-flush early-stop so max_urls cuts off without hanging joins.
- `references/sitemap-cache-lastmod.md` - HEAD-verified sitemap discovery, lastmod-TTL-validated JSON cache envelope, sentinel-counted index fan-out, and write-while-streaming CC mirrors.
- `references/browser-recycle-drain.md` - whitelist config signatures + refcounted contexts + version-bump drain capped at 3 pending browsers with 30s force-clean.
- `references/managed-browser-prelaunch.md` - port-owner kill, singleton-lock removal, detached process groups, verify-then-connect CDP, and terminate->killpg escalation.

## Capsule map
- **Fetch & resilience** - `antibot-tiered-detector`: three detection tiers sized 15KB/<10KB/<50KB with data-response exemptions and 403/503-always-block.
- **Fetch & resilience** - `antibot-retry-proxy-ladder`: attempts x proxies nesting, exception-swallow rule, fallback-fetch promotion, and the crawl_stats ledger every result carries.
- **Cache plane** - `smart-cache-freshness`: 304/head-fingerprint validation with FRESH/STALE/UNKNOWN/ERROR mapped to hit_validated/recrawl/hit_fallback.
- **Cache plane** - `content-hash-db-cache`: task-id-pooled aiosqlite (WAL) whose rows store content hashes pointing at filesystem blobs, UPSERTed with etag/lastmod/fingerprint metadata.
- **Cache plane** - `cache-mode-context`: five CacheModes collapsed onto should_read/should_write predicates with legacy-flag precedence.
- **Multi-URL orchestration** - `deep-crawl-decorator-guard`: ContextVar latch installed by decorating arun at construction so nested arun calls fall through to single-URL mode.
- **Multi-URL orchestration** - `bfs-level-loop-resume`: level-synchronous traversal cloning deep_crawl_strategy away per delegation, success-gated budgets, and a four-key resume snapshot.
- **Multi-URL orchestration** - `url-filter-chain-scoring`: sync-inline/async-gather hybrid chain feeding scored-capacity-trimmed link selection with boundary-checked glob buckets.
- **URL discovery** - `seeder-pipeline-backpressure`: bounded queue + global QPS semaphore + drain-flush early-stop so max_urls cuts off without hanging joins.
- **URL discovery** - `sitemap-cache-lastmod`: HEAD-verified sitemap discovery, lastmod-TTL-validated JSON cache envelope, sentinel-counted index fan-out, and write-while-streaming CC mirrors.
- **Browser fleet** - `browser-recycle-drain`: whitelist config signatures + refcounted contexts + version-bump drain capped at 3 pending browsers with 30s force-clean.
- **Browser fleet** - `managed-browser-prelaunch`: port-owner kill, singleton-lock removal, detached process groups, verify-then-connect CDP, and terminate->killpg escalation.

## Extending the foundation
Add one `references/<seam>.md` capsule-v2 for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
crawl4ai (Apache-2.0), `main@7e801521428ee12509994d39151006f64055ebe3` (= graph base_sha, zero drift); Codebase Memory project `ext-crawl4ai` (FULL mode, 11,395 nodes / 56,815 edges, generated 2026-08-23T09:21Z generation_matches=true; parse_partial x8 all docs/examples HTML/CSS fixtures, none cited; 14 cited paths all no_recorded_issue+metadata_match).

## Full view (memory graph)
Revalidate `ext-crawl4ai` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: retry/proxy loop topology, tiered block heuristics with data exemptions, cache predicate tables, ContextVar recursion guards, refcount-and-drain recycling, sentinel-counted generator fan-out. Adapt the host-specific integrations: Playwright/patchright bindings, httpx/aiohttp transports, xxhash fingerprints, sqlite blob layout, vendor block-page regex lists. Omit product surfaces: docker_api server, CLI, MCP server, hub marketplace, adaptive/statistical crawler scoring internals, LLM extraction strategies, markdown-generation strategy tree.
