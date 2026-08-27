---
name: open-seo-foundation
description: "Use when porting a pay-as-you-go SEO platform's reusable machinery: Cloudflare Workflows run orchestration (per-step Postgres scoping, partial-index single-flight guards, stale-run reconciliation), SERP rank-check adapters over a metered third-party API (live vs task-queue vs live-fallback ladders), credit estimation that matches per-call rounding, drift-free schedule anchoring for cron admission control, R2 cache keys that survive schema evolution, URL/domain research-scope grammar, AI-search (LLM mentions) fan-out with cache-only-on-complete, Durable-Object crawl scratchpads, and agent-facing MCP tool registration or in-app agent turn hooks. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# OpenSEO: metered SEO platform foundation

## Use this for
Use when porting a pay-as-you-go SEO platform's reusable machinery: Cloudflare Workflows run orchestration (per-step Postgres scoping, partial-index single-flight guards, stale-run reconciliation), SERP rank-check adapters over a metered third-party API (live vs task-queue vs live-fallback ladders), credit estimation that matches per-call rounding, drift-free schedule anchoring for cron admission control, R2 cache keys that survive schema evolution, URL/domain research-scope grammar, AI-search (LLM mentions) fan-out with cache-only-on-complete, Durable-Object crawl scratchpads, and agent-facing MCP tool registration or in-app agent turn hooks. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/pgStep.md` — why AsyncLocalStorage does not reach Workflow steps and the wrapper that fixes it.
- `references/run-lifecycle-guards.md` — one active run per config via partial unique index + workflow-status reconciliation.
- `references/rank-check-workflow.md` — prepare/batches/finalize state machine that never resurrects superseded runs.
- `references/live-queued-check-paths.md` — batch ladders, poll cadence, and the never-abort-a-paid-run rule.
- `references/credit-estimation.md` — per-call round-then-ceiling credit math that matches real metering.
- `references/schedule-anchor.md` — drift-free computeNextCheckAt advancing from the previous anchor.
- `references/scheduled-rank-checks-cron.md` — tick budget/deadline admission control; never write nextCheckAt on errors.
- `references/dataforseo-metered-client.md` — lazy section loading behind a meter() proxy with charged-task accounting.
- `references/billing-envelope-assert-ok.md` — the status ladder separating access failures from charged-but-failed tasks.
- `references/serp-rankcheck-adapter.md` — organic-only position extraction plus stop_crawl_on_match cost control.
- `references/billing-error-classifier.md` — balance-failure text/status classifier scoped by API path prefix.
- `references/r2-cache-key.md` — sorted-param SHA-256 keys, metadata TTL, zod-validate-on-read.
- `references/research-scope-target-parser.md` — domain/URL scope grammar with PSL validation and post-filter matching.
- `references/brand-lookup-fanout.md` — sequenced metered calls, settled sub-calls, complete-only caching.
- `references/audit-scratchpad-do.md` — SQLite Durable Object frontier with self-healing cleanup alarm.
- `references/site-audit-phases.md` — paid-call checkpoint isolation, legacy checkpoint shapes, robots-replay pinning.
- `references/mcp-tool-registration.md` — typed tool table, instrumentation wrap, oseo_-scoped API-key lane.
- `references/sam-agent-turn-hooks.md` — refusal-as-model gating, per-turn metering, rewind race containment.

## Capsule map
- **Workflow kernel** — `pgStep`: step.do + request-scoped PG client; ALS does not propagate into steps.
- **Workflow kernel** — `run-lifecycle-guards`: failed INSERT = already-running signal; stale blocker fails before retry.
- **Workflow kernel** — `rank-check-workflow`: finalize recounts from DB; completed/failed runs are terminal.
- **Rank tracking** — `live-queued-check-paths`: 10-keyword batches; 4/2/2/2/2/3-min polls; straggers get one live shot.
- **Rank tracking** — `credit-estimation`: round each metered call's USD then ceil to credits, sum per call.
- **Rank tracking** — `schedule-anchor`: advance from previous anchor so delayed runs never drift.
- **Rank tracking** — `scheduled-rank-checks-cron`: first start always admitted; plan-check errors leave row due.
- **DataForSEO adapter** — `dataforseo-metered-client`: type-only section imports; charge on success AND charged failure.
- **DataForSEO adapter** — `billing-envelope-assert-ok`: classify access errors first; "No Search Results" is empty success.
- **DataForSEO adapter** — `serp-rankcheck-adapter`: rank_group not rank_absolute; stop_crawl_on_match restricted to organic.
- **DataForSEO adapter** — `billing-error-classifier`: 40200/40210/402 codes or balance text → typed error, path-prefixed only.
- **Shared infra** — `r2-cache-key`: sorted params → SHA-256; expiresAt in customMetadata; revalidate shape on read.
- **Shared infra** — `research-scope-target-parser`: exact_url/subfolder/domain/subdomains; charset + PSL gate pre-billing.
- **AI measurement** — `brand-lookup-fanout`: platforms sequenced for balance checks; cache only when every call succeeded.
- **Site audit** — `audit-scratchpad-do`: seeds in DO not step returns (~1MiB limit); alarm re-armed every construction.
- **Site audit** — `site-audit-phases`: paid fetch vs persist split into separate checkpoints; parse robots from checkpoint text.
- **Agent surfaces** — `mcp-tool-registration`: raw-shape or z.object inputs normalized at register; API keys never become sessions.
- **Agent surfaces** — `sam-agent-turn-hooks`: canned refusal model replaces provider call; rewind cancels in-flight turn first.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
OpenSEO (github.com/openseo-network/open-seo, MIT), `main@cd6a782092556d6f7a0e3ab1cdb66a4dada30e28`; Codebase Memory project `ext-open-seo` (28,043 nodes / 58,132 edges, FULL mode, head_sha = base_sha = cd6a7820 zero drift at pass 1, generation_matches=true). parse_partial ×18 (drizzle SQL migrations ×12, ChatMessage.tsx :283, app.css :17/23/59, ai.tsx :54/207, support.tsx :28, worker-configuration.d.ts :23/24) — none cited by capsules; grep those files if porting from them. Repo was 13 commits behind origin/main at pick time (next-pass diff-first rule).

## Full view (memory graph)
Revalidate `ext-open-seo` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Pass-1 retrieval battery resolved cited symbols line-exact via search_graph (`beginRankCheckRun`, `estimateRankCheckCredits`, `assertOk`, `buildRankCheckResult`, `pgStep`, `parseResearchTarget`, `getBrandLookup`, `AuditScratchpad`, `registerOpenSeoTool`, …) and adversarial cross-project probes returned total:0.

## Boundaries
Adopt pure contracts: run-slot coordination, credit math, schedule anchoring, envelope status ladder, scope grammar, cache key/TTL discipline, checkpoint isolation of paid calls. Adapt host-specific integrations: Cloudflare Workflows/Durable Objects/R2/Autumn billing/DataForSEO SDK types can be swapped for other schedulers, KV stores, billing providers, and SERP vendors as long as the invariants (single active run, charged-vs-unbilled split, per-call rounding, complete-only caching) hold. Omit source-specific product behavior: hosted-vs-self-host auth modes, Stripe/Autumn wiring, PostHog telemetry, the Astro marketing web/, GA4/GSC OAuth UX, and the SAM persona content.
