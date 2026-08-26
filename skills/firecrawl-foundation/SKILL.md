---
name: firecrawl-foundation
description: "Use when porting web-scraping platform kernels: multi-engine waterfall orchestration, feature-flag retry ladders, tiered cancellation, credit pricing, crawl dedup state, and signed webhook delivery."
disable-model-invocation: true
---

# Firecrawl: Web-Scraping Platform Kernel Foundation

## Use this for
Use when building or porting a scraping/extraction service that must try multiple fetch strategies in quality order under one budget: an engine fallback list built from capability matrices, a concurrent waterfall race with per-engine error classification, adaptive retries that MUTATE feature flags instead of repeating work, three-tier abort semantics (external/scrape/engine), a per-job LLM cost ledger feeding a replace-vs-additive credit ladder, Redis-backed crawl dedup with URL-permutation canonicalization, ZDR-safe finish bookkeeping, and signed SSRF-guarded webhook delivery. Source code is ground truth; each capsule carries a decisive excerpt, invariant, executed probe, and graph retrieval.

## Load the matching source dump
### Scrape orchestration plane (`apps/api/src/scraper/scrapeURL/`)
- `references/meta-object-lifecycle.md` — one Meta object carries id/options/flags/prefetches; tri-state prefetches (`undefined`=not-yet, `null`=came-back-empty) gate antibot fallbacks.
- `references/engine-fallback-list.md` — priority-threshold filter over a 16-flag × 15-engine matrix; quality-sign partition keeps specialty engines only when no general engine survives.
- `references/engine-waterfall-race.md` — engines start eagerly and race with a waterfall timer; WrappedEngineError carries the engine id; EngineUnsuccessful is silent-by-design.
- `references/retry-tracker-feature-ladder.md` — AddFeature/RemoveFeature/PDFAntibot errors are control signals mutating flags under a two-level (global + per-reason) budget.
- `references/abort-manager-tiers.md` — AbortManager fans typed abort instances into one signal; tier discriminates fatal from swallowable; child managers dispose per attempt.
### Document enrichment plane (`scraper/scrapeURL/transformers/`)
- `references/transformer-stack-order.md` — 20-stage sequential stack where markdown precedes redactPII/LLM extract; out-of-order guards throw; final stage strips unrequested fields.
### Usage ledger & billing plane (`apps/api/src/lib/`)
- `references/cost-tracking-ledger.md` — append-only call ledger with record-time stacks, NaN-proof totals, throw-after-record limit; serialized shape is the cross-process contract.
- `references/credit-pricing-ladder.md` — base 1 + additive surcharges vs replace-style rules (json=5, deterministicJson=10|3, fire-1=cost×1800); failures bill scans but no base.
### Crawl state & delivery plane (`lib/crawl-redis.ts`, `services/webhook/delivery.ts`)
- `references/url-permutation-dedup.md` — www/scheme/index-file permutations collapsed to ONE canonical key via idempotence invariant; SADD arity admits.
- `references/crawl-finish-zdr-bookkeeping.md` — completion = jobs_done==jobs AND kickoff AND sitemap done; HSETNX threat records double as billing dedup; unconditional ZDR wipes at finish.
- `references/webhook-delivery.md` — HMAC-over-exact-bytes signature, private-IP SSRF gate, RabbitMQ-or-inline split, buffered log insertion that degrades gracefully.
### Worker & error planes (`services/queue-worker.ts`, `lib/error.ts`)
- `references/worker-lifecycle.md` — RAM/CPU admission-controlled pull loops, tracked in-flight drain on shutdown, TransportableErrors exempt from crash reporting.
- `references/transportable-error-taxonomy.md` — internal control-flow errors never cross processes; TransportableError serialize/deserialize pairs with string-code wire contract.

## Capsule map
- **Scrape orchestration** — `meta-object-lifecycle`, `engine-fallback-list`, `engine-waterfall-race`, `retry-tracker-feature-ladder`, `abort-manager-tiers`: one immutable-feeling context drives a quality-ordered concurrent engine ladder whose retries mutate capabilities under hard budgets.
- **Document enrichment** — `transformer-stack-order`: fields derive in dependency order and get stripped to exactly what was requested.
- **Usage ledger & billing** — `cost-tracking-ledger`, `credit-pricing-ladder`: every LLM call lands once with its stack; credits price by features with honest failure billing.
- **Crawl state & delivery** — `url-permutation-dedup`, `crawl-finish-zdr-bookkeeping`, `webhook-delivery`: variant URLs collapse to one lock key, completion needs all conjuncts, and customer webhooks are signed and SSRF-safe.
- **Worker & errors** — `worker-lifecycle`, `transportable-error-taxonomy`: workers admit on load and drain cleanly; only user-facing errors ever leave the process.

## Extending the foundation
Add one source-confirmed capsule-v2 per porting question: loader line here, matching map entry above, decisive excerpt + invariant + executed probe + `search_graph` Retrieve against `ext-firecrawl`. Candidate next seams live in `search/` (v1→v2 backend ladder, searxng/ddg), `lib/extract/` + `lib/extract/fire-0/` (schema dereference, rerankers, f0 twins), `lib/deterministicJson/` (sandboxed extractor generation), `services/worker/nuq-fdb/` (FoundationDB queue kernel), `lib/threat-protection/` (provider store/sync/verdict), and `lib/branding/` (logo/color extraction).

## Provenance
firecrawl (firecrawl), AGPL-3.0 license, `main@ca0be9b7d91eb9b48d3430f5678211f0d47e1d90` (= base_sha, unchanged since index); upstream origin/main is +1 commit (`7f1ecf3`, audit-ci.jsonc pin bump only — zero code drift, adjudicated). Codebase Memory project `ext-firecrawl` (18,970n / 91,982e FULL mode, direct root `/mnt/hdd/utopia/inspo/external/firecrawl`, generation 2026-08-23T09:21:49Z, generation_matches=true; parse_partial ×36 = SQL/YAML/test fixtures, none cited). All 14 cited source paths `no_recorded_issue` + `metadata_match` via stdin-JSON coverage. Pass-1 squeeze, FIRST learning row for this repo (row-gap class repaired same change). Gate-5: vitest ^4.1.9 declared but node_modules ABSENT clone-wide — runner honestly BLOCKED; deterministic battery executed byte-exact with 7 expectation corrections re-derived from live grep before shipping (counts: prefetch-comments 3, nanProof 4, extends-TransportableError 24, snipeAbortController 3, threat_blocked 2). Retrieval liveness: BM25 rank-1 line-exact on buildFallbackList :589-914, ScrapeRetryTracker.record :36-77, AbortManager.dispose/child, calculateCreditsToBeBilled :63-225, generateURLPermutations :412-486; adversarial wrong-project probes (`AbortManager tier child dispose scrape`) vs ext-gpt-researcher/ext-storm = unrelated-plane hits only.

## Full view (memory graph)
Revalidate `ext-firecrawl` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`; source decides shipped claims. Graph hot seams resolve line-exact via BM25 `search_graph` (e.g. `buildFallbackList` → engines/index.ts:589-914; `ScrapeRetryTracker.record` → retryTracker.ts:36-77; `calculateCreditsToBeBilled` → scrape-billing.ts:63-225; `generateURLPermutations` → crawl-redis.ts:412-486). Layers: `scrapeURL/index.ts` (1,557L) is the hub — buildMetaObject feeds scrapeURLLoop which races engine promises from engines/index.ts's handler/MRT/options triple-table dispatch; winners flow through transformers/index.ts's ordered stack into Document; lib/scrape-billing prices, services/webhook delivers, lib/crawl-redis holds crawl state, services/queue-worker runs the loop. The api tree (~733 TS files) also carries search/, extract/, deterministicJson/, threat-protection/, nuq-fdb queue kernels not yet mined — see Extending.

## Boundaries
Adopt the pure contracts: capability-matrix engine selection, race-with-waterfall degradation, flag-mutation retry budgets, tiered aborts, ledger+pricing split, permutation-canonical dedup, HSETNX-scoped dedup keys, unconditional ZDR wipes, sign-after-stringify webhooks. Adapt integration specifics: Redis key layout/TTLs, BullMQ/nuq/FireEngine boundaries, credit constants (product pricing), provider tables. Omit product behavior: hosted Exchange/index engines behind config walls, self-host message branching, apps/js-sdk|python-sdk client surfaces, kubernetes/helm examples — and do NOT treat EngineUnsuccessfulError as fatal or reorder the transformer stack (markdown-before-redactPII is load-bearing).
