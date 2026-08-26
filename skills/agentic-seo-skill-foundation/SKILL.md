---
name: agentic-seo-skill-foundation
description: "LLM-first SEO audit evidence-collector foundation plus GitHub repository-trust audit machinery"
---
# Agentic-SEO-Skill: LLM-first SEO audit evidence-collector foundation

## Use this for
Use when porting deterministic SEO/AEO/GEO audit machinery — SSRF-safe fetchers, robots/llms.txt evaluation, JSON-LD schema validation and generation, snippet-format scanning, E-E-A-T/freshness/citation content scoring, GSC decay/striking-distance tracking, AI-crawler policy matrices, authenticated GitHub repository-trust audits (provider fallback, rate-limit-aware retries, release/file-inventory scoring), or the orchestration pattern of an 88-script evidence layer under an LLM-first router. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/safe-http-ssrf-guard.md` — hardened request primitive with per-hop redirect revalidation.
- `references/dual-parser-html-kernel.md` — canonical page dict every collector agrees on.
- `references/robots-longest-match.md` — allow/disallow evaluator with allow-wins tiebreak.
- `references/finding-verifier-dedupe.md` — severity-ranked dedupe + counter-evidence suppression gate.
- `references/citation-readiness-scoring.md` — claim/citation ratio scorer with class-diversified caps.
- `references/answer-block-snippet-grammar.md` — Q-heading→answer, definition, list, table scoring windows.
- `references/llms-txt-quality-scoring.md` — llmstxt.org grammar parser + tiered-bonus grader.
- `references/ai-crawler-policy-matrix.md` — 9-UA roster × per-path decisions × alignment trichotomy.
- `references/schema-template-generator.md` — deep-copied JSON-LD template emission + type detection.
- `references/entity-sameas-knowledge-graph.md` — priority-tiered platform identity audit.
- `references/cms-aware-article-extraction.md` — Blogger/WP/Ghost detection + scoped body extraction.
- `references/frequency-keyword-extractor.md` — corpus-free weighted n-gram keyword ranking.
- `references/eeat-freshness-scoring.md` — trust-marker and date-semantics scorers.
- `references/decay-striking-distance.md` — median-split rank tracker from GSC CSVs.
- `references/report-weighted-aggregation.md` — None-excluding weighted composite score.
- `references/skill-orchestration-contract.md` — scripts-as-evidence pipeline doctrine + CI inventory gates.
- `references/github-fetch-provider-ladder.md` — unified REST/gh-CLI accessor with auth-shaped attempt ordering.
- `references/rest-json-retry-ratelimit-ladder.md` — 429/5xx backoff vs rate-reset wait; response envelope.
- `references/gh-auth-exit-zero-trap.md` — text-parsed `gh auth status`; token→env→dotenv ladder; mode trichotomy.
- `references/repo-slug-resolution.md` — slug/URL/SCP normalization falling back to git origin.
- `references/repo-audit-finding-contract.md` — confidence-carrying findings envelope + severity-weighted score.
- `references/release-seo-local-fallback.md` — releases→git-tags degradation with per-row provenance markers.
- `references/repo-file-inventory-scoring.md` — five-section trust inventory with warning-only score penalty.

## Capsule map
- **Transport kernel** — `safe-http-ssrf-guard`: per-hop SSRF revalidation; forced TLS; byte cap; 303 downgrade.
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
- **Repo intelligence** — `github-fetch-provider-ladder`: auth-shaped attempt order [api(token)→gh→api(public)]; labeled error merge on total failure.
- **Repo intelligence** — `rest-json-retry-ratelimit-ladder`: 429/5xx capped exp backoff; 403+`Remaining:0` waits until `X-RateLimit-Reset`; `{data,status,rate_limit}` envelope.
- **Repo intelligence** — `gh-auth-exit-zero-trap`: exit 0 ≠ valid token — parse stdout+stderr for success phrase minus three failure phrases; cached module-global.
- **Repo intelligence** — `repo-slug-resolution`: strip `.git`, rewrite SCP/URL forms, keep first two segments; explicit → git origin → both-remedies error.
- **Repo intelligence** — `repo-audit-finding-contract`: Confirmed→Likely downgrade when endpoints fail; origin-gated local checks; score `100−20C−8W`; Pass sentinel scores zero.
- **Repo intelligence** — `release-seo-local-fallback`: releases→`git for-each-ref` tags fallback; per-row `source` marker; additive penalties −20/−15/−10.
- **Repo intelligence** — `repo-file-inventory-scoring`: five CHECKS sections; presence-ratio×100 minus 2×warnings (errors never double-counted); install-CTA heuristic.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Agentic-SEO-Skill (MIT, pyproject `license = {text = "MIT"}`), `main@69199160e18372bc5cdf9ddec20ccb9fb1b509f1`; Codebase Memory project `aeo-agentic-seo-skill` (2,283 nodes / 7,604 edges, FULL mode, ready @ same pin, head=base zero drift, generation 2026-08-25T08:35:20Z generation_matches; parse_partial ×1 = install.ps1 only, none cited). The pre-existing leaf's 16 references were authored under the since-deleted project name `ext-aeo-agentic-seo-skill` (same HEAD; edge delta 7430→7604 is indexer-version drift) — all pass-2 capsules cite the live project name. Gate-5 real runner: upstream pytest suite 34/34 GREEN at pin (`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider`, clean tree); pass 1 probe battery 80/80 deterministic assertions green; pass 2 added the repo-auditee plane (7 capsule-v2 refs below, all Retrieves executed live on the graph; family subset tests/test_link_and_github_depth_scripts.py 4/4).

## Full view (memory graph)
Revalidate `aeo-agentic-seo-skill` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt pure scoring/evaluation contracts (scorers, evaluators, verifiers are dependency-light and directly portable); adapt network-touching collectors to host HTTP policy and the SKILL.md prose doctrine to your agent runtime's conventions; omit IDE installer matrix (`install.sh`/`install.ps1`), report HTML rendering (`github_seo_report.py`, `generate_report.py` — separate seam), and dated-fact constants as-is without re-verifying against current search-engine reality at port time. The GitHub repo-auditee family is mined as of pass 2; `analyze_title_strategy` (github_repo_audit :136-192), `seo_common.py` remainder, `env_loader.py`, and the sibling consumers (`github_community_health`, `github_readme_lint`, `github_weekly_scorecard`, …) remain uncited seams for later passes.
