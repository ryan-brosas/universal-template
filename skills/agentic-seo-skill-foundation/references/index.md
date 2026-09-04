<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Agentic-SEO-Skill: LLM-first SEO audit evidence-collector foundation

## Use this for
Use when porting deterministic SEO/AEO/GEO audit machinery — SSRF-safe fetchers, robots/llms.txt evaluation, JSON-LD schema validation and generation, snippet-format scanning, E-E-A-T/freshness/citation content scoring, GSC decay/striking-distance tracking, AI-crawler policy matrices, authenticated GitHub repository-trust audits (provider fallback, rate-limit-aware retries, release/file-inventory scoring), the standalone-script runtime plane (non-raising fetch envelope, stdlib dotenv ladder, CLI output contract), or the orchestration pattern of an 88-script evidence layer under an LLM-first router. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./safe-http-ssrf-guard.md` — hardened request primitive with per-hop redirect revalidation.
- `./seo-common-fetch-envelope.md` — `fetch_url` non-raising result dict over the SSRF-safe primitive; 38 call sites.
- `./dual-parser-html-kernel.md` — canonical page dict every collector agrees on.
- `./robots-longest-match.md` — allow/disallow evaluator with allow-wins tiebreak.
- `./finding-verifier-dedupe.md` — severity-ranked dedupe + counter-evidence suppression gate.
- `./citation-readiness-scoring.md` — claim/citation ratio scorer with class-diversified caps.
- `./answer-block-snippet-grammar.md` — Q-heading→answer, definition, list, table scoring windows.
- `./llms-txt-quality-scoring.md` — llmstxt.org grammar parser + tiered-bonus grader.
- `./ai-crawler-policy-matrix.md` — 9-UA roster × per-path decisions × alignment trichotomy.
- `./schema-template-generator.md` — deep-copied JSON-LD template emission + type detection.
- `./entity-sameas-knowledge-graph.md` — priority-tiered platform identity audit.
- `./cms-aware-article-extraction.md` — Blogger/WP/Ghost detection + scoped body extraction.
- `./frequency-keyword-extractor.md` — corpus-free weighted n-gram keyword ranking.
- `./eeat-freshness-scoring.md` — trust-marker and date-semantics scorers.
- `./decay-striking-distance.md` — median-split rank tracker from GSC CSVs.
- `./report-weighted-aggregation.md` — None-excluding weighted composite score.
- `./skill-orchestration-contract.md` — scripts-as-evidence pipeline doctrine + CI inventory gates.
- `./env-loader-dotenv-ladder.md` — `load_env`/`get_env` stdlib-only cwd→SKILL_DIR→home .env ladder; real env always wins.
- `./seo-common-cli-contract.md` — `issue()` 4-key finding row, `print_json_or_text` dict+lines duality, exit(1) dep guards.
- `./github-fetch-provider-ladder.md` — unified REST/gh-CLI accessor with auth-shaped attempt ordering.
- `./rest-json-retry-ratelimit-ladder.md` — 429/5xx backoff vs rate-reset wait; response envelope.
- `./gh-auth-exit-zero-trap.md` — text-parsed `gh auth status`; token→env→dotenv ladder; mode trichotomy.
- `./repo-slug-resolution.md` — slug/URL/SCP normalization falling back to git origin.
- `./repo-audit-finding-contract.md` — confidence-carrying findings envelope + severity-weighted score.
- `./release-seo-local-fallback.md` — releases→git-tags degradation with per-row provenance markers.
- `./repo-file-inventory-scoring.md` — five-section trust inventory with warning-only score penalty.
- `./title-strategy-keyword-seeding.md` — `analyze_title_strategy` name→topics→description seed order with forced-"seo" slug promotion.
- `./topic-suggester-canonical-scoring.md` — `suggest_topics` phrase-table + word-floor + competitor scoring with limitations degradation.

## Capsule map
- **Transport kernel** — `safe-http-ssrf-guard`: per-hop SSRF revalidation; forced TLS; byte cap; 303 downgrade.
- **Transport kernel** — `seo-common-fetch-envelope`: `fetch_url` sentinel-initialized result dict, single `error` string, lowercased headers, redirect chain, HEAD body skip; `load_html` URL-vs-file heuristic.
- **Parsing kernel** — `dual-parser-html-kernel`: one canonical page dict; invalid-JSON sentinels; decompose-before-text.
- **Crawl policy** — `robots-longest-match`: longest pattern wins, equal length ⇒ allow; empty-disallow skip.
- **Report gate** — `finding-verifier-dedupe`: suppress-on-counter-evidence before dedupe; stronger severity wins merges.
- **AI measurement** — `citation-readiness-scoring`: 35 coverage / 20 trusted / 15 author / 20 sameAs / 10 canonical additive ladder.
- **AI measurement** — `answer-block-snippet-grammar`: direct answers 20-70 words ×20, definitions ×12, lists ≥3 ×10, tables ≥2 rows ×12.
- **AI measurement** — `llms-txt-quality-scoring`: title20+desc20+sections15+links20+length5 with bonus tiers, cap 100 (raw max 105).
- **AI measurement** — `ai-crawler-policy-matrix`: frozen 9-UA audit contract; documented/robots_only/allowed_without_llms_txt.
- **Schema plane** — `schema-template-generator`: fallback-subordinate catalog; deepcopy = placeholder-safety contract.
- **Schema plane** — `entity-sameas-knowledge-graph`: Critical/High missing-platform audit; @graph unwrap; substring-match caveat.
- **Content intelligence** — `cms-aware-article-extraction`: generator-meta-first CMS detection ladder; >8-word paragraph filter.
- **Content intelligence** — `frequency-keyword-extractor`: unigrams >3×1, bigrams ×3.0, trigrams ×5.0; longer-phrase-wins dedupe.
- **Content intelligence** — `eeat-freshness-scoring`: credential/experience ×7 capped 20; age penalty after 365-day grace; mismatch −15.
- **Rank tracking** — `decay-striking-distance`: median-split periods; weighted avg position window [4,20]; cap 200.
- **Scoring core** — `report-weighted-aggregation`: hreflang None = exclusion not zero; weight denominator renormalizes.
- **Orchestration** — `skill-orchestration-contract`: bounded retries, artifact-first deliverables, CI-counted inventory.
- **Script runtime** — `env-loader-dotenv-ladder`: `load_env`/`get_env` cwd→SKILL_DIR→home .env order; per-key live-env no-overwrite makes real env + earlier file win; idempotent flag; multi-name fallback.
- **Script runtime** — `seo-common-cli-contract`: `issue()` `{severity,message,url,evidence}` row; `print_json_or_text` insertion-order JSON vs text lines; None-sentinel optional imports + exit(1) pip-hint guards.
- **Repo intelligence** — `github-fetch-provider-ladder`: auth-shaped attempt order [api(token)→gh→api(public)]; labeled error merge on total failure.
- **Repo intelligence** — `rest-json-retry-ratelimit-ladder`: 429/5xx capped exp backoff; 403+`Remaining:0` waits until `X-RateLimit-Reset`; `{data,status,rate_limit}` envelope.
- **Repo intelligence** — `gh-auth-exit-zero-trap`: exit 0 ≠ valid token — parse stdout+stderr for success phrase minus three failure phrases; cached module-global.
- **Repo intelligence** — `repo-slug-resolution`: strip `.git`, rewrite SCP/URL forms, keep first two segments; explicit → git origin → both-remedies error.
- **Repo intelligence** — `repo-audit-finding-contract`: Confirmed→Likely downgrade when endpoints fail; origin-gated local checks; score `100−20C−8W`; Pass sentinel scores zero.
- **Repo intelligence** — `release-seo-local-fallback`: releases→`git for-each-ref` tags fallback; per-row `source` marker; additive penalties −20/−15/−10.
- **Repo intelligence** — `repo-file-inventory-scoring`: five CHECKS sections; presence-ratio×100 minus 2×warnings (errors never double-counted); install-CTA heuristic.
- **Repo intelligence** — `title-strategy-keyword-seeding`: `analyze_title_strategy` name→topics→desc-top15 seed order, first-occurrence dedupe; "seo" force-promoted to slug slot 0; acronym display map; title drops only for/and/the, cap 7 tokens.
- **Repo intelligence** — `topic-suggester-canonical-scoring`: `suggest_topics` phrase hits ×(20+12·extra words); raw-word +1 floor; competitor topics ×5; every failed source → `limitations`, never an exception.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Agentic-SEO-Skill (MIT, pyproject `license = {text = "MIT"}`), `main@69199160e18372bc5cdf9ddec20ccb9fb1b509f1`; Codebase Memory project `aeo-agentic-seo-skill` (2,283 nodes / 7,604 edges, FULL mode, ready @ same pin, head=base zero drift, generation 2026-08-25T08:35:20Z generation_matches; parse_partial ×1 = install.ps1 only, none cited). The pre-existing leaf's 16 references were authored under the since-deleted project name `ext-aeo-agentic-seo-skill` (same HEAD; edge delta 7430→7604 is indexer-version drift) — all pass-2 capsules cite the live project name. Gate-5 real runner: upstream pytest suite 34/34 GREEN at pin (`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider`, clean tree); pass 1 probe battery 80/80 deterministic assertions green; pass 2 added the repo-auditee plane (7 capsule-v2 refs below, all Retrieves executed live on the graph; family subset tests/test_link_and_github_depth_scripts.py 4/4); pass 3 added the standalone-script runtime plane (5 capsule-v2 refs: seo-common-fetch-envelope, seo-common-cli-contract, env-loader-dotenv-ladder, title-strategy-keyword-seeding, topic-suggester-canonical-scoring) — Codebase Memory MCP was absent in that session, so pass-3 seams were selected and confirmed by direct source+test reads at the same pin (their Retrieve calls are marked not-executed; revalidate on the graph before relying on them).

## Full view (memory graph)
Revalidate `aeo-agentic-seo-skill` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt pure scoring/evaluation contracts (scorers, evaluators, verifiers are dependency-light and directly portable); adapt network-touching collectors to host HTTP policy and the SKILL.md prose doctrine to your agent runtime's conventions; omit IDE installer matrix (`install.sh`/`install.ps1`), report HTML rendering (`github_seo_report.py`, `generate_report.py` — separate seam), and dated-fact constants as-is without re-verifying against current search-engine reality at port time. The GitHub repo-auditee family is mined as of pass 2; the standalone-script runtime plane (`env_loader.py`, `seo_common.py` fetch/output/guard helpers, `analyze_title_strategy`, `repo_topic_suggester`) is mined as of pass 3. Remaining uncited seams: the `seo_common.py` sitemap tail (`discover_sitemap_urls` :330-344, `parse_sitemap_xml` :347-381 — gzip-magic + namespace-local-tag handling), and the sibling consumers behind the shared client (`github_community_health`, `github_readme_lint`, `github_weekly_scorecard`, `repo_social_preview_checker`, `repo_docs_site_checker`, `github_traffic_archiver`, `github_search_benchmark`, `github_competitor_research`).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`ai-crawler-policy-matrix.md`](./ai-crawler-policy-matrix.md)
- [`answer-block-snippet-grammar.md`](./answer-block-snippet-grammar.md)
- [`citation-readiness-scoring.md`](./citation-readiness-scoring.md)
- [`cms-aware-article-extraction.md`](./cms-aware-article-extraction.md)
- [`decay-striking-distance.md`](./decay-striking-distance.md)
- [`dual-parser-html-kernel.md`](./dual-parser-html-kernel.md)
- [`eeat-freshness-scoring.md`](./eeat-freshness-scoring.md)
- [`entity-sameas-knowledge-graph.md`](./entity-sameas-knowledge-graph.md)
- [`env-loader-dotenv-ladder.md`](./env-loader-dotenv-ladder.md)
- [`finding-verifier-dedupe.md`](./finding-verifier-dedupe.md)
- [`frequency-keyword-extractor.md`](./frequency-keyword-extractor.md)
- [`gh-auth-exit-zero-trap.md`](./gh-auth-exit-zero-trap.md)
- [`github-fetch-provider-ladder.md`](./github-fetch-provider-ladder.md)
- [`llms-txt-quality-scoring.md`](./llms-txt-quality-scoring.md)
- [`release-seo-local-fallback.md`](./release-seo-local-fallback.md)
- [`repo-audit-finding-contract.md`](./repo-audit-finding-contract.md)
- [`repo-file-inventory-scoring.md`](./repo-file-inventory-scoring.md)
- [`repo-slug-resolution.md`](./repo-slug-resolution.md)
- [`report-weighted-aggregation.md`](./report-weighted-aggregation.md)
- [`rest-json-retry-ratelimit-ladder.md`](./rest-json-retry-ratelimit-ladder.md)
- [`robots-longest-match.md`](./robots-longest-match.md)
- [`safe-http-ssrf-guard.md`](./safe-http-ssrf-guard.md)
- [`schema-template-generator.md`](./schema-template-generator.md)
- [`seo-common-cli-contract.md`](./seo-common-cli-contract.md)
- [`seo-common-fetch-envelope.md`](./seo-common-fetch-envelope.md)
- [`skill-orchestration-contract.md`](./skill-orchestration-contract.md)
- [`title-strategy-keyword-seeding.md`](./title-strategy-keyword-seeding.md)
- [`topic-suggester-canonical-scoring.md`](./topic-suggester-canonical-scoring.md)
