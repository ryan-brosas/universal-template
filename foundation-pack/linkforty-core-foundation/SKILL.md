---
name: linkforty-core-foundation
description: "Use when porting short-link redirect engines, deferred install attribution (click→install fingerprint matching), mobile fallback chains (Universal Links / App Links / app scheme / store / web), link-safety gating (warn interstitial vs indistinguishable block), write-time bot classification feeding analytics filters, HMAC-signed webhook delivery with capped exponential backoff, or Fastify+Postgres additive-schema bootstrap for an embeddable service — self-hosted deep-link engine foundation."
disable-model-invocation: true
---
# LinkForty core: Self-hosted deep-link engine Foundation

## Use this for
Use when porting short-link redirect engines, deferred install attribution (click→install fingerprint matching), mobile fallback chains (Universal Links / App Links / app scheme / store / web), link-safety gating (warn interstitial vs indistinguishable block), write-time bot classification feeding analytics filters, HMAC-signed webhook delivery with capped exponential backoff, or Fastify+Postgres additive-schema bootstrap for an embeddable service. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/redirect-fallback-chain.md` — Which URL wins per device and why in-app browsers swap store-vs-web order.
- `references/click-id-pregen-async-tracking.md` — Click UUID minted before the 302; row written fire-and-forget with the same id.
- `references/link-safety-gate.md` — allow/warn/block precedence and the response-indistinguishability invariant under block.
- `references/owner-suspension-probe-factory.md` — Memoised information_schema probe returning a shared SQL fragment for optional columns.
- `references/app-scheme-interstitial.md` — Scheme-then-store HTML page that preserves the URL fragment servers never see.
- `references/warning-interstitial-xss-posture.md` — Protocol allowlist beats HTML escaping when rendering flagged destinations.
- `references/fingerprint-attribution-scoring.md` — Weighted factor scoring, NAT-range exclusion, per-link attribution windows.
- `references/write-time-bot-classification.md` — edge > method > ua authority ladder persisted on the click row.
- `references/trusted-client-ip-resolution.md` — One choke-point IP resolver with a documented proxy-trust precondition.
- `references/resolution-cache-invalidation.md` — Dual-key Redis invalidation wired into every link mutation path.
- `references/social-scraper-preview-hook.md` — preHandler content negotiation serving OG meta to crawler UAs.
- `references/targeting-rules-semantics.md` — AND-of-dimensions audience rules with data-absent-fails and 404 camouflage.
- `references/webhook-hmac-delivery-engine.md` — sha256= signature envelope, 30s-capped backoff, unawaited fan-out.
- `references/event-fk-recovery-insert.md` — Constraint-name-scoped FK recovery: only the stale attributed-link FK degrades.
- `references/additive-schema-bootstrap.md` — CREATE TABLE IF NOT EXISTS + guarded ALTERs as the whole migration plane.
- `references/liveness-readiness-split.md` — /health touches nothing; only the store of record flips readiness.
- `references/well-known-verification-endpoints.md` — AASA + assetlinks.json shapes and their serving constraints.
- `references/sdk-resolve-twin.md` — Non-redirecting resolve for OS-intercepted clicks enforcing the same block gate.
- `references/realtime-click-streaming.md` — Process-local EventEmitter broadcast; single-node by construction.
- `references/analytics-bot-free-aggregation.md` — is_bot=false on every rollup; LEFT-JOIN filters in the JOIN clause.
- `references/short-code-collision-retry.md` — Bounded regenerate-and-probe over a UNIQUE-constraint backstop.
- `references/dynamic-update-query-builder.md` — Schema-key camelCase→snake_case partial updates with JSONB arm.
- `references/template-defaults-exclusivity.md` — Preset settings as middle-tier defaults; one default template per scope.
- `references/qr-generation-plane.md` — Full-param cache keys and PNG-buffer/SVG-text dual encoding.
- `references/debug-simulate-replay.md` — Read-only redirect-decision replay with per-dimension match detail.

## Capsule map
- **Redirect decision** — `redirect-fallback-chain`: UL/AppLink > scheme > browser-aware store/web > original; in-app browsers reorder step 3 only.
- **Click accounting** — `click-id-pregen-async-tracking`: pre-generated UUID on the destination URL matches the async-written row id.
- **Safety gate** — `link-safety-gate`: suspension > inactive > warn > allow; block answers as unknown code everywhere.
- **Schema probe** — `owner-suspension-probe-factory`: per-registration memoised column probe returns SQL fragment; fail-open empty.
- **Scheme handoff** — `app-scheme-interstitial`: client-side hash re-append onto scheme URL; 1.5s replace() to browser-aware fallback.
- **Flagged-page XSS** — `warning-interstitial-xss-posture`: http(s) protocol allowlist for hrefs; no-JS no-dependency warn page.
- **Install attribution** — `fingerprint-attribution-scoring`: 40/30/10/10/10 weights, NAT IPs score zero, ≥70 threshold, per-link windows.
- **Bot flagging** — `write-time-bot-classification`: classify once at ingestion; edge tier behind env trust opt-in.
- **Client IP** — `trusted-client-ip-resolution`: authoritative header only when origin is proxy-only; ::ffff: unwrap always.
- **Cache coherence** — `resolution-cache-invalidation`: old+new template keys deleted on update/delete; errors swallowed.
- **Crawler previews** — `social-scraper-preview-hook`: UA-class preHandler serves static OG HTML; fail-open to redirect.
- **Audience rules** — `targeting-rules-semantics`: dimensions AND, values OR; missing visitor data fails present rules.
- **Outbound webhooks** — `webhook-hmac-delivery-engine`: HMAC over raw body; min(2^n s, 30s) backoff; deliveries not awaited.
- **FK triage** — `event-fk-recovery-insert`: recover only the named constraint's 23503; rethrow all others.
- **Schema lifecycle** — `additive-schema-bootstrap`: guarded-additive DDL only; minimal seed tables must be clobber-proof.
- **Health probes** — `liveness-readiness-split`: liveness dependency-free; optional-cache failure reports degraded-not-unready.
- **OS verification** — `well-known-verification-endpoints`: AASA without .json suffix; assetlinks fingerprints list; env-driven.
- **SDK resolve** — `sdk-resolve-twin`: same cache keys, same SELECT fragment, same block gate as the redirect.
- **Live stream** — `realtime-click-streaming`: emitter singleton + unsubscribe-on-disconnect; multi-node needs external pub/sub.
- **Analytics reads** — `analytics-bot-free-aggregation`: stored bot flag filtered in every count; join-clause window filters.
- **Identifier minting** — `short-code-collision-retry`: ≤10 regenerations then hard error; UNIQUE index is the real guarantee.
- **Partial updates** — `dynamic-update-query-builder`: undefined-skips, empty-guard, JSONB stringify arm, parametrized ownership.
- **Preset defaults** — `template-defaults-exclusivity`: scope-exact is_default clearing; delete guard before FK SET NULL matters.
- **QR rendering** — `qr-generation-plane`: every render param inside the cache key; encode the short URL, not the destination.
- **Decision replay** — `debug-simulate-replay`: read-only simulation with enumerated would-404 warnings; language-match divergence noted.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
LinkForty core (AGPL-3.0-only), `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory project `ext-core` (FULL mode, 1,053n/1,530e, generated 2026-08-23T11:42:46Z, generation_matches=true, parse_partial ×0, coverage stdin-JSON ×20 cited paths all no_recorded_issue+metadata_match; best-effort caveat applies). First pass mined at this pin 2026-08-24.

## Full view (memory graph)
Revalidate `ext-core` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Graph notes: BM25 search_graph resolves Function-class symbols line-exact (e.g. evaluateLinkSafety :39-44, calculateConfidenceScore :182-255); Route nodes exist but carry no file spans. Direct-test inventory at pin: 13 co-located vitest suites (~2,300 lines) under src/lib/*.test.ts + src/routes/*.test.ts — safety gate, SDK event FK recovery, SDK cache cross-path bypass, health routing regression, fingerprint scoring, client-ip ladder, webhook signing/delivery, link-resolution invalidation are test-pinned; preview.ts, templates.ts, qr.ts, debug.ts, well-known.ts, analytics.ts have NO dedicated suites (capsules record this honestly and pin behavior by byte-exact source greps instead).

## Boundaries
Adopt the pure contracts: safety-state machine, fallback-chain ordering, fingerprint scoring with NAT exclusion, signature/backoff webhook envelope, additive DDL guards, liveness/readiness asymmetry, constraint-scoped FK recovery. Adapt host-specific integration: Fastify plugin registration order, Redis key grammar, geoip/ua-parser library choices, env-var names, Postgres dialect details. Omit source-specific product behavior: @linkforty/cloud upsell callouts, the debug/live WebSocket surface in multi-node deployments (process-local by design), fixture endpoints, and any schema surface your deployment does not model (owner suspension is probed, never assumed).
