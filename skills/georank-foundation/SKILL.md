---
name: georank-foundation
description: "Use when building AI-visibility (GEO/SEO) platforms: token-reservation metering for LLM spend with principal merge + stage idempotency, BYOK header contracts with SSRF-pinned provider HTTP, deterministic GEO page scoring (schema/meta/content/citations), Celery pipeline stage claims with reservation-scoped writes, and profiled keyword expansion with offline fallback."
disable-model-invocation: true
---
# GEOrank (aeo-georank) Foundation

## Use this for
Build an AI-search-visibility platform (GEO diagnostics, company knowledge pipelines, keyword tooling) on FastAPI + Celery: a prepaid token-reservation ledger that survives worker crashes and concurrent spend, identity resolution that merges user+device wallets exactly once, bring-your-own-key headers that cannot be origin-hijacked, outbound provider calls pinned against DNS rebinding, deterministic four-axis page scoring fused by admin-editable weights, crawler state machines that only advance after durability is proven, and keyword generation whose output shape never branches on whether the LLM answered. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/reservation-ledger.md` — two-phase reserve→settle kernel; conditional UPDATE holds.
- `references/principal-merge.md` — lock→re-read→merge of user/device quota principals.
- `references/provider-stage-idempotency.md` — per-stage claim leases; completed spend is append-only.
- `references/cjk-token-estimator.md` — CJK 1-char/token heuristic; 3× reservation headroom; module floors.
- `references/byok-contract.md` — X-BYOK header protocol; configured-origin pinning; transient keys only.
- `references/ssrf-pinned-provider-http.md` — shape gate + resolve-verify + connect-time re-pin transport.
- `references/provider-failover-ladder.md` — providers→primary→fallback tiers; blank output IS failure; buffered streaming.
- `references/geo-diagnostic-scoring.md` — schema/meta/content/citation scorers + weighted fusion + degraded recommender twin.
- `references/pipeline-stage-claims.md` — error-column epoch lease; resume-after-crash re-dispatch.
- `references/task-finalize-boundary.md` — final-attempt detection; reservation-scoped terminal writes; broker-vs-business retries.
- `references/access-resolution-trio.md` — sync vs queued vs system AI authorization contexts.
- `references/reservation-expiry-sweeper.md` — piggy-backed SKIP LOCKED sweep; midnight-clamped async expiry.
- `references/usage-recording-settlement.md` — event converges to settled charge; BYOK events excluded from quota.
- `references/knowledge-page-selection.md` — weighted-keyword nav ranking; homepage always first; LLM-or-heuristic parity.
- `references/ssrf-safe-crawl.md` — per-request URL revalidation inside Playwright routing.
- `references/crawl-persist-verify.md` — put+read-back gate before advancing pipeline state.
- `references/graph-write-guard.md` — closed ontology validation + company-scoped MERGE + idempotent rebuilds.
- `references/vector-store-degradation.md` — embed-skip vs count-mismatch fail; replace-set upserts; centroid similarity.
- `references/keyword-expansion-profiles.md` — profile inference, hash-stable scores, template fallback with AI-path output parity.
- `references/settings-overlay-normalizer.md` — DB-over-env config builders; enum defaults; PG-int clamps; TTL cache.
- `references/encrypted-settings-aad.md` — AES-GCM envelope with setting-name AAD defeating row swaps.
- `references/profile-replace-semantics.md` — replace-vs-merge field mapping; provider-failure shield over heuristic base.
- `references/retrieval-fallback-scoring.md` — script-aware tokenization and weighted-field lexical ranking.

Additional capsules mined this pass (same directory): `graph-write-guard.md`, `vector-store-degradation.md`, `keyword-expansion-profiles.md`, `settings-overlay-normalizer.md`, `encrypted-settings-aad.md`, `profile-replace-semantics.md`, `retrieval-fallback-scoring.md`.

## Capsule map
- **Quota & metering** — `reservation-ledger`: personal wallet + global daily budget holds via conditional UPDATEs; settle releases holds and charges max(actual, module floor) with metadata-recorded overage. `principal-merge`: sorted advisory locks → post-lock link re-read → single merge preserving max(grant), summed counters, any(frozen). `provider-stage-idempotency`: event_metadata stage map {claimed→completed}; retries take fresh claim ids; actual_tokens = sum of completed stages. `cjk-token-estimator`: non_ascii×1 + ascii/4 ceil; reservations = max(module floor, 3× estimate). `access-resolution-trio`: BYOK dies at the queue boundary; system jobs hold global budget only via allow_anonymous flag. `reservation-expiry-sweeper`: skip_locked sweep piggybacked on new reservations; async expiry clamped to timezone midnight; liveness triple-check (pending ∧ unexpired ∧ same usage_date). `usage-recording-settlement`: event.total_tokens := settled charge; provider_source partitions paid vs free analytics.
- **Security** — `byok-contract`: provider key must exist in admin allowlist; user base-url must match configured ORIGIN (scheme+host+port); keys never persisted. `ssrf-pinned-provider-http`: https-only shape gate → getaddrinfo all-global → httpcore backend re-validates DNS at connect_tcp and dials IP literals; follow_redirects=False; trust_env=False. `encrypted-settings-aad`: AES-256-GCM envelope keyed by setting NAME as AAD (row-swap fails decryption); read-side fail-open; idempotent wrap. `settings-overlay-normalizer`: defaults-first builders; unknown enums ⇒ default; numeric clamp to PG int range; legacy mode migration; 15s TTL double-checked cache.
- **LLM client** — `provider-failover-ladder`: priority-sorted providers (+ round-robin cursor) → primary model → codex fallback; blank content raises like an exception; stream buffers whole reply then yields once so SSE disconnects can't skew accounting; clients cached per (key, base_url) signature.
- **Scoring & analysis** — `geo-diagnostic-scoring`: JSON-LD @graph/list flattening; breadth-or-coverage schema score; 20/20/20/20/10/10 content rubric; authority-domain citation ladder; weights normalized at runtime with zero-sum fallback; rule-based degraded recommender emits the SAME JSON contract as the LLM path. `knowledge-page-selection`: same-origin depth≤1 asset-free candidates; ±weighted zh keywords; depth −4/path; forced homepage insert; failed sub-pages recorded not dropped. `keyword-expansion-profiles`: marker-vote profile inference (5 libraries); md5-stable scores clamped 35..99; 8s timeout then template fallback; BYOK callers get failures, never silent downgrade. `retrieval-fallback-scoring`: script-aware tokens; field-weighted match table; +120 preferred anchor; bounded trust boosts.
- **Pipeline integrity** — `pipeline-stage-claims`: `__georank_task_claim__:{stage}:{task_id}:{epoch}` lease in pipeline_error; fresh claim ⇒ StageClaimBusy(retry 60s); real errors are never overwritten; resume ladder re-dispatches next stage when DB shows its transition landed. `task-finalize-boundary`: `_is_final_attempt` gates terminal FAILED writes; every guarded write filters ai_reservation_id; finalize settles quota exactly once; dispatch failures retry 20× before failing. `crawl-persist-verify`: put → byte-equal read-back → only then persist key + dispatch; stale memory-fallback eviction pinned by test. `ssrf-safe-crawl`: normalize → resolve-all-global → route("**/*") revalidates EVERY request with fresh DNS; websockets closed; bot UA declared; page.url re-validated post-load.
- **Storage & profiles** — `graph-write-guard`: closed vocabularies ({Person,Product,Technology,Company} × 4 relation types) validated pre-Cypher; company-scoped MERGE; delete-before-insert idempotent rebuilds. `vector-store-degradation`: EmbeddingNotConfiguredError ⇒ warn-and-skip while count-mismatch ⇒ hard fail; uuid5 point ids; delete-filter-then-upsert replace sets; 409-tolerant collection create; centroid similarity over-fetches +5 for dedupe. `profile-replace-semantics`: replace=True nulls fields absent from the latest crawl (merge mode only for opportunistic hydration); LLM overrides only non-empty keys onto the heuristic base; _provider_succeeded meters but never gates persistence.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
GEOrank / aeo-georank (Apache-2.0), `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94` (= index base_sha, zero upstream drift verified via fetch at pass 1); Codebase Memory project `ext-aeo-georank` (6,941 nodes / 22,314 edges, FULL mode, generation 2026-08-23T10:26:47Z, generation_matches=true; parse_partial = .env.example + nginx conf only, none cited; not_indexed = .git/dist + 8 icon/image suffixes BY DESIGN). First foundation + first learning row for this repo.

## Full view (memory graph)
Revalidate `ext-aeo-georank` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/external/aeo-georank`, branch main, HEAD `424a0cf9` (= base_sha, zero drift at pass 1). Retrieval battery: search_graph resolves cited symbols line-exact (settle_token_reservation :969–1049, claim_async_reservation_stage :1120–1175, estimate_token_count :93–108, PinnedAsyncNetworkBackend :126–135, validate_public_crawl_url :135–152, fallback_select_company_pages :222–273, expand_keywords_with_status :390–424, encrypt_setting_value :101–119, +4 more); adversarial cross-project probes (`ext-aeo-openserp`, `ext-aeo-elmo`) return total:0. check_index_coverage over 12 cited paths: all no_recorded_issue + metadata_match, generation_matches=true.

## Boundaries
Adopt pure contracts (scoring rules, score fusion, token estimation, keyword scoring, retrieval weights, validation grammars, AAD encryption envelope); adapt host integrations (Celery task names, FastAPI dependency wiring, Qdrant/Neo4j clients, MinIO storage, zh-market keyword/profile dictionaries, DeepSeek-default guidance copy); omit product shells (apps/web Next.js UI, apps/admin, packages/{api-sdk,auth,i18n,ui}, cli/, docker-compose/infra, alembic history beyond the migration-contract tests, marketing site pages under app/web). The Chinese-language user-facing strings are product copy, not contract.
