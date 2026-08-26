---
name: geoready-foundation
description: 'Use when building GEO/AI-visibility tooling: site audits scored 0-100, llms.txt generation, citation checks against answer engines, anti-SSRF fetching, plugin registries, or AI-crawler analytics — port the mined GeoReady (geo-optimizer-skill) contracts.'
license: MIT
---

# GeoReady (aeo-geo-optimizer-skill): GEO Audit & AI-Visibility Foundation

## Use this for
Use when building tools that audit how citable a site is to AI answer engines — weighted scoring engines, robots/llms.txt/schema checkers, citation measurement against Perplexity-style APIs, prompt-injection or hallucination-bait scanners, anti-SSRF URL fetchers, trend/history trackers, or MCP exposure of an audit kernel. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/check-registry-plugin-kernel.md` — third-party checks plug in via Protocol + entry points; fail-isolated, never score-affecting.
- `references/scoring-engine-breakdown.md` — SCORING weights → category breakdown → clamped 0–100 with split-budget asserts.
- `references/audit-orchestrator-builder.md` — one `_build_audit_result` composition point shared by sync/async/MCP callers.
- `references/recommendation-impact-ordering.md` — priority buckets re-ranked stably by recoverable category points.
- `references/ssrf-safe-fetch.md` — validate-once DNS pinning + per-hop redirect revalidation closes TOCTOU rebinding.
- `references/async-dns-pinning.md` — threading.local pins leak across coroutines; contextvars dual-set discipline.
- `references/trust-stack-layers.md` — five capped trust layers with cross-layer signal subtraction.
- `references/prompt-injection-detector.md` — eight manipulation categories, category-count severity, navigation-shape exemption.
- `references/jsonld-graph-unpacking.md` — flatten arrays + `@graph` or every WordPress schema block scores zero.
- `references/citability-normalization.md` — 47-method rubric normalized raw/max so new methods can't reshape the scale.
- `references/brand-match-precision.md` — conditional word boundaries + domain-root lookahead for entity mentions.
- `references/citation-check-rates.md` — answered-denominator mention/citation rates and four-state verdicts.
- `references/llm-client-contract.md` — error-as-value LLM responses; citations only from grounded providers.
- `references/llms-txt-generator.md` — sitemap→llms.txt with shared bomb budget, freshness sort, Optional section.
- `references/schema-injection-safety.md` — reserialization escaping + `</` guard + non-mutating FAQ harvest.
- `references/history-drift-severity.md` — canonical snapshot keys; crawlability loss outranks score-drop severity.
- `references/passive-monitor-signals.md` — seven weighted visibility signals with honest unknown-momentum.
- `references/batch-audit-concurrency.md` — semaphore + hard per-URL timeout; every page yields a row.
- `references/hallucination-bait-patterns.md` — context-gated regex families; verb-gated AI-authorship detection.
- `references/intent-mapping-coverage.md` — weighted intent taxonomy with schema-required gating.
- `references/topic-authority-clusters.md` — DF-filtered term clusters, hub-and-spoke interlink ratio, pillar pages.
- `references/fixer-score-estimation.md` — generated fixes carry computed deltas from the scorer's own branch logic.
- `references/ai-log-analyzer.md` — config-driven UA fragments over combined/JSON server logs.
- `references/skill-catalog-validation.md` — YAML skill specs cross-validated against AST-discovered MCP tools.
- `references/perception-extractor.md` — deterministic "simulated perception" always labeled as such.
- `references/answer-snapshot-archive.md` — position-preserving citation extraction + tolerant timestamps.
- `references/competitive-narrative-gaps.md` — deterministic gap facts; LLM contributes sanitized prose only.
- `references/cache-telemetry-stores.md` — tolerant-read TTL cache; closed telemetry event vocabulary.
- `references/bots-tier-config.md` — 3-tier bot taxonomy; citation-critical subset grounded in vendor docs (#512).
- `references/coherence-analyzer.md` — cross-page conflicting definitions, duplicate titles, mixed language.
- `references/mcp-server-surface.md` — thin asdict tools + config-as-resources over the kernel.
- `references/negative-signals-penalties.md` — gated penalty detectors feeding one negative breakdown key.
- `references/brand-entity-signals.md` — name voting across surfaces, KG pillar counting, suffix-aware normalization.

## Capsule map
- **Plugin kernel** — `check-registry-plugin-kernel`: Protocol registry, lock-snapshot + deepcopy soup, exception→zero-score isolation.
- **Scoring core** — `scoring-engine-breakdown`: weights dict → breakdown dict → clamp[0,100] w/ overflow warn; assert-tied split budgets. `recommendation-impact-ordering`: stable recoverable-points bucket ranking.
- **Orchestration** — `audit-orchestrator-builder`: single builder, empty-default substitution, lazy sub-audit fallbacks, soup_clean perf contract. `batch-audit-concurrency`: semaphore+timeout fan-out, errors-as-rows.
- **Transport & security** — `ssrf-safe-fetch`: validate→pin→dial→revalidate-per-hop. `async-dns-pinning`: thread-local vs coroutine pinning trap. `cache-telemetry-stores`: TTL cache tolerance; closed event vocab.
- **Trust & safety scanners** — `trust-stack-layers`: 5×5pt layers minus social overlap. `prompt-injection-detector`: 8-category severity ladder. `hallucination-bait-patterns`: verb-gated claim families. `negative-signals-penalties`: single negative-key penalties.
- **Content intelligence** — `citability-normalization`: raw/max method ledger. `jsonld-graph-unpacking`: array+@graph BFS iterator. `brand-match-precision`: boundary-conditional mention regex. `brand-entity-signals`: name voting + KG pillars. `intent-mapping-coverage`: schema-gated intent rubric. `topic-authority-clusters`: DF-gated cluster scoring. `coherence-analyzer`: definition-conflict detection.
- **AI measurement** — `citation-check-rates`: answered-denominator verdicts. `llm-client-contract`: four-vendor normalized client. `answer-snapshot-archive`: first-position citations. `competitive-narrative-gaps`: deterministic facts, sanitized prose. `passive-monitor-signals`: derived dashboard signals. `ai-log-analyzer`: UA-fragment log mining.
- **Generators & surfaces** — `llms-txt-generator`: bounded sitemap→index. `schema-injection-safety`: JSON-LD emit/inject guards. `fixer-score-estimation`: computed post-fix deltas. `skill-catalog-validation`: AST cross-validated specs. `mcp-server-surface`: asdict tools + config resources. `history-drift-severity`: precedence severity ladder. `perception-extractor`: labeled simulated view. `bots-tier-config`: tier taxonomy + citation subset.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
GeoReady / geo-optimizer-skill (MIT), `main@a7165be2bf4c97681e6802f419caf2ef5a2ba1ef`; Codebase Memory project `ext-aeo-geo-optimizer-skill` (ready FULL, 5,945n/22,846e, head==base==a7165be2 zero drift at squeeze time; parse_partial ×3 = 2 frontend TSX lines + jekyll layout lines, none cited; not_indexed = images/fonts by design). Pass 1 of the AEO/GEO dedicated lane, 2026-08-26.

## Full view (memory graph)
Revalidate `ext-aeo-geo-optimizer-skill` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Real-runner evidence at pin: uv venv (py3.11) + pytest → 1,706 passed / 17 skipped / 0 failed across the core suite (test_core, test_registry, test_citability, test_trust_stack, test_prompt_injection, test_llms_v2_validation, test_ssrf_hardening, test_history, test_drift_detector, test_monitor, test_batch_audit, test_cli, test_skill_system, test_topic_authority, test_coherence, test_brand_match, …); web-app and mcp-server suites exist but were NOT executed this pass (optional-dep install blocked by lane security gate) — their capsules cite deterministic contract evidence instead.

## Boundaries
Adopt the pure decision cores: scoring/breakdown math, registry isolation, severity ladders, regex pattern tables, normalization formulas, severity precedence, mention regexes, citation aggregation. Adapt thresholds, bot lists, weight tables, and language variants (the config module is deliberately the single tuning surface). Omit the product shells: FastAPI web app (`web/app.py` 2,424L), Astro marketing frontend (`frontend/`), Docker/render deployment, GitHub Actions workflows, i18n .mo/.po binaries, and the Jekyll `site/` demo — transport/product behavior below the porting bar.
