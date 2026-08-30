---
name: aeo-elmo-foundation
description: "Use when building AI-visibility (AEO/GEO) tracking: multi-provider answer-engine adapters, citation extraction from raw LLM/scraper payloads, mention-based Share of Voice, history-metered per-target scheduling with failure backoff + maintenance self-healing, and encrypted credential storage."
disable-model-invocation: true
---
# Elmo (aeo-elmo) Foundation

## Use this for
Build a brand-visibility tracker over AI answer engines (ChatGPT/Claude/Gemini/Perplexity/Google AI surfaces): one Provider SPI unifying scraped consumer surfaces and direct model APIs, read-time citation/text extraction over stored vendor payloads, mention-detection → SoV metrics, a pg-boss-style scheduler whose cadence is metered against recorded run history (not job timers), failure backoff capped at the normal cadence, a pure-decision maintenance sweep, JWE-encrypted credential overrides, and onboarding that turns one URL into a trackable identity. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/scrape-target-grammar.md` — model:provider[:version][:online] env grammar, invertible parse/format.
- `references/provider-contract.md` — the Provider SPI, ScrapeResult normalization, scraped-vs-api access.
- `references/dataforseo-route-selection.md` — one provider id, three upstream routes, honest access labels.
- `references/citation-dispatch.md` — read-time shape auto-detect; shown-results ≠ cited-sources.
- `references/grounding-redirects.md` — resolve expiring Vertex redirect links before storing citations.
- `references/web-queries-sentinel.md` — real / unavailable-marker / none encoding for fan-out queries.
- `references/mention-detection.md` — name+alias+domain lowercase substring funnel.
- `references/share-of-voice.md` — SoV formulas, null-vs-zero, round-once-at-display.
- `references/representative-prompts.md` — 2 strengths + 2 opportunities with a zero-SoV cap.
- `references/failure-backoff.md` — ramp capped AT cadence; streak rides on the job payload.
- `references/per-target-cadence.md` — targetKey(model::provider::web), due-with-tolerance vs overdue-late.
- `references/maintenance-sweep.md` — gather→pure decisions→expedite/schedule executor.
- `references/expedite-guard.md` — never expedite a job carrying a failure streak.
- `references/job-envelope.md` — retryLimit:0 economics for paid fan-out jobs.
- `references/usage-attribution.md` — billing-grade ledger counting failed attempts; plan-derived ceiling.
- `references/premium-run-policy.md` — two-tier targets, slower-only override clamp, oldest-first pools.
- `references/secret-keyring.md` — dir+A256GCM JWE with kid + context AAD; overlay rebuild.
- `references/onboarding-analysis.md` — schema-is-contract brand analysis + paranoid normalization.
- `references/website-excerpt.md` — Jina→Readability fail-open excerpt ladder.
- `references/citation-volatility.md` — Jaccard set vs Bray–Curtis weighted churn.
- `references/lvcf-trend.md` — per-prompt last-value-carried-forward share trend + leaderboard twin.
- `references/citation-rollup.md` — normalize-then-fold URLs; category by dominant child.
- `references/fanout-analysis.md` — prompt-rewrite token diff; stopword list keeps commercial modifiers.
- `references/report-selection.md` — over-sample 20%, sort by signal, reuse paid runs.
- `references/branded-arbitration.md` — one-sided user override truth table.
- `references/bulk-prompts.md` — every dropped line gets a reason bucket.
- `references/local-provisioning.md` — one-shot INSERTs, targeted conflict guards, index-walk slugify.
- `references/entitlement-resolution.md` — mode-first unlimited short-circuit; healthiest-subscription pick.
- `references/output-caps.md` — store-and-warn clipping honesty; two-tier search budgets.
- `references/scraper-shape-ladders.md` — BrightData/Oxylabs/Cloro ordered probe ladders.

## Capsule map
- **Configuration** — `scrape-target-grammar`: comma-split entries; last segment "online"; middle segments rejoin into version slugs; parse∘format invertible.
- **Provider plane** — `provider-contract`: run()→ScrapeResult{textContent,rawOutput,webQueries,citations,modelVersion}; access = scraped|api; grounded = webSearch ∧ api. `dataforseo-route-selection`: route table mirrors advertised access; version pin = API opt-in. `scraper-shape-ladders`: ordered probe ladders over drifting vendor shapes; indexOf not regex for UI-noise titles.
- **Extraction** — `citation-dispatch`: extractors re-read stored rawOutput; dedupe+http-prefix gates; legacy engine aliases in dispatch. `grounding-redirects`: manual-redirect Location resolution at fetch time, fail-open. `web-queries-sentinel`: never echo the prompt as a fan-out query.
- **Measurement** — `mention-detection`: substring funnel incl. domains; aliases curated substring-minimal. `share-of-voice`: brand/(brand+competitors) integer % or null; visibility separate; unstable-stats keep floats. `representative-prompts`: has-competition strengths, lowest-SoV opportunities, ≤1 zero-SoV. `citation-volatility`: set (Jaccard) vs volume-weighted (Bray–Curtis) churn + transition-count gate. `lvcf-trend`: per-prompt LVCF pre-seeded; leaderboard matches trend endpoint. `citation-rollup`: fold on normalized URL before classify; positions weighted by count. `fanout-analysis`: exclude verbatim repeats + sentinel; one vote per distinct token. `report-selection`: candidates=1.2×target; reuse selected paid runs. `branded-arbitration`: one-sided override else system; isOverridden audit flag.
- **Scheduling** — `failure-backoff`: min(ramp[failures−1], cadence); any success clears streak. `per-target-cadence`: due leans early (≤30min/¼-interval tolerance), overdue leans late (full interval + grace). `maintenance-sweep`: parked chains never alert; zero-runs ⇒ inherently overdue; batched sends + start_after UPDATE expedite. `expedite-guard`: refusal by streak then recency. `job-envelope`: retryLimit 0 because retries double-bill; expiry > slowest fan-out. `premium-run-policy`: picks→ungrounded only; override slows-only; pools oldest-first. `usage-attribution`: count attempts not runs; ceiling = 1.5× plan maxima.
- **Platform** — `secret-keyring`: kid-stamped JWE, ctx AAD comparison defeats row-swap; retired-keys-requires-current throw. `entitlement-resolution`: non-cloud ⇒ UNLIMITED at the first branch; always-populate map. `onboarding-analysis`: provided names outrank model; hostname-only tracked identity. `website-excerpt`: two-rung ladder returns "" not throws. `output-caps`: warn-on-length without failing; recurring budgets tighter than research. `bulk-prompts`: blank/in-paste/of-existing/capacity check order attributes blame correctly. `local-provisioning`: plain INSERTs behind a first-signup gate; slug suffixing with reserved-route set.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Elmo / aeo-elmo (MIT license), `main@da87272cf026208ab198084b4f2552baca975a7b`; Codebase Memory project `ext-aeo-elmo` (9,453 nodes / 27,077 edges, FULL mode, generation 2026-08-23T10:26:30Z, generation_matches true; parse_partial limited to CSS/SQL files, none cited; not_indexed = icons/images by design).

## Full view (memory graph)
Revalidate `ext-aeo-elmo` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/external/aeo-elmo`, branch main, HEAD da87272c (= base_sha, zero drift at pass 1). All 17 cited paths no_recorded_issue + metadata_match. Monorepo note: apps/web Next.js surfaces (postgres-read, editorial-domains 25k LOC data file, server/* route fns) and packages/{ui,cloud,deployment,api-spec} were NOT mined this pass — see work record NEXT-PASS TARGETS. Source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: run-policy/expedite/backoff math, report-metrics, visibility-stats, bulk-prompts, scrape-target grammar (all dependency-free and unit-tested). Adapt provider adapters (each vendor's field ladders and route tables are revision-pinned), the drizzle/pg-boss integration points, and the better-auth/stripe entitlement plumbing to your stack. Omit product surface: Next.js dashboards, whitelabel report rendering, Auth0 sync, marketing www app, and the 25k-line editorial-domains dataset.
