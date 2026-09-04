<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# OpenSERP Foundation

## Use this for
Build a multi-engine SERP API/CLI without API keys: one typed engine contract implemented by per-engine adapters (Google/Bing/Yandex/Baidu/DuckDuckGo/Ecosia), organic-rank-stable result normalization, a shared captcha/soft-block/no-results classifier used by BOTH live-browser and raw-HTML parse paths, a resilience pipeline (per-engine rate limiter + retry budget + circuit breaker + tagged proxy pool with quarantine), mega-search fan-out with cross-engine clustering, and an auto/fast/rendered URL extractor with llms.txt short-circuit. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./engine-contract.md` — what a new engine must implement and how the pipeline wraps it.
- `./error-taxonomy.md` — sentinel errors: which degrade proxies, which are challenges, which map to which HTTP status.
- `./rank-state.md` — ads never shift organic rank; absolute-rank interleaving and negative-rank feature convention.
- `./result-normalization.md` — SearchResult→v2 Result enrichment, Bing click-tracking unwrap, stable IDs.
- `./response-envelope.md` — Envelope/Finalize pagination semantics and the four output formats.
- `./dual-parser.md` — one selector table + one classifier feeding both rod and goquery parsers.
- `./google-adapter.md` — canonical-result selector ladder, PAA expansion polling, virtualized image grid harvesting.
- `./serp-features.md` — declarative SerpFeatureSelector specs, SingleMatch, placeholder filtering, mirror-to-feature.
- `./url-builders.md` — per-engine query-param dialects (gl/hl/uule, kl inversion, lr, freshness buckets).
- `./region-uule.md` — dependency-free region resolution and Google UULE v1 encoding.
- `./resilient-pipeline.md` — circuit gate → policy resolve → limiter → proxy mode switch → recovered invocation.
- `./retry-budget.md` — non-retryable sentinels, jittered backoff, derived request timeout.
- `./circuit-breaker.md` — closed/open/half-open FSM plus avg-success-latency for fastest-engine mode.
- `./proxy-policy.md` — off/request_url/tag_pool resolution and the X-Use-Proxy / X-Proxy-URL override ladder.
- `./proxy-registry.md` — round-robin with challenged-skip, failure-disable threshold, tag quarantine + probe recovery.
- `./browser-lifecycle.md` — persistent connection hygiene (never bake a deadline), isolated contexts, ordered teardown.
- `./proxy-auth-listener.md` — persistent CDP Fetch auth listener and its exclusivity with HijackRequests.
- `./fingerprint-profiles.md` — weighted profile catalog, runtime version patching, full CDP emulation set, lane cookies.
- `./raw-tls-client.md` — tls-client Chrome profiles picked by salted hash, header order, guarded redirect loop.
- `./server-routing.md` — route registration with aliases, dedicated-endpoint flow, middleware order.
- `./cache-contract.md` — cache-key composition with market fields and every BYPASS rule.
- `./extract-auto.md` — fast/rendered escalation, only-rendered-is-longer guard, thin-article fallback to full body.
- `./llms-txt.md` — root-only /llms-full.txt→/llms.txt probe with HTML-sniff rejection.
- `./mega-clusters.md` — balanced/any/fastest modes, partial results on deadline, dedupe, cross-engine agreement score.
- `./server-browser-pool.md` — per-authenticated-proxy Chrome pooling with LRU + idle eviction.
- `./batch-extract.md` — Open WebUI-compatible bare-array batch contract with per-item error isolation.
- `./fingerprint-check.md` — Detector SPI and the debug fingerprint endpoint's validation ladder.
- `./yandex-partial-success-funnel.md` — mid-pagination captcha degrades to partial results; only first-page failure propagates.
- `./yandex-hydration-re-poll.md` — selector-wait then count-to-target grace re-poll for progressively rendered rows.
- `./yandex-image-state-json.md` — image results harvested from data-state JSON blobs with three-tier selector fallback.
- `./yandex-lr-region-policy.md` — lr-only region targeting; rstr deliberately dropped to cut captcha frequency.
- `./baidu-mu-canonical-url.md` — mu= canonical swap over opaque /link?url= redirects; relative links rejected as non-organic.
- `./baidu-hashed-class-prefix.md` — prefix-match build-rotated CSS hashes on unique stems; exact pins only on generic stems.
- `./raw-status-gate.md` — HTTP status→sentinel table (401/403→blocked, 429→rate-limited, ≥5xx→blocked) gating body reads.
- `./raw-offset-rebase.md` — skip→rebase→offset post-passes make one-page raw fetches rank as if started at #35.
- `./fpcheck-detection-kernel.md` — normalize→classify→escalate grammar turning five incompatible detector DOMs into one verdict map.
- `./fpcheck-rebrowser-verdicts.md` — JSON+table fusion with last-write-wins keyed merge and emoji→rating fallback ladder.
- `./yandex-neuro-answer-exclusion.md` — AI answer cards skipped from ranks but captured as ai_summary features with allowlisted citations.

## Capsule map
- **Engine SPI** — `engine-contract`: SearchEngine interface + Init defaults + shared rate limiter + receiver-scoping idiom; panics become ErrEngineInternal at exactly one point.
- **Sentinel errors** — `error-taxonomy`: errors.Is-driven policy everywhere; IsProxyNetworkError ≠ IsProxyChallengeError decides proxy health.
- **Rank math** — `rank-state`: three counters (organic/ad/absolute); ads keep their own rank stream; features carry negative internal ranks; sort by absolute then ad-last.
- **Normalization** — `result-normalization`: lowercase scheme/host, strip tracking params, unwrap bing.com/ck/a u=a1base64, ID = md5(engine|url)[:16].
- **Envelope** — `response-envelope`: has_more counts non-ad rows only; NextStart = Start+Limit; json/markdown/text/ndjson renderers; only JSON envelopes are cached.
- **Dual parsing** — `dual-parser`: Selectors struct is single source of truth; classify*Document shared by live page, raw body, and POST /parse.
- **Google adapter** — `google-adapter`: div.tF2Cxc innermost-only selector; broad data-hveid/data-ved fallback requires data-ved filter; right-click materializes image hrefs.
- **SERP modules** — `serp-features`: spec-driven extraction emits only content-bearing containers; AI-summary placeholder/CSS-shell filters; answer-box rows mirror into serp_features.
- **URL dialects** — `url-builders`: site:/filetype: folded into q; num only >10; pws=0; DDG kl = inverted region-language; Yandex mime:/lang: operators; Ecosia day/week/month freshness.
- **Geotargeting** — `region-uule`: numeric = Yandex lr passthrough; country ⇒ gl/lr only (no UULE); city canonical table; UULE = prefix + length char + base64(canonical).
- **Resilience** — `resilient-pipeline`: one protection wrapper for browser/raw/image paths; tag-pool-only single challenged-proxy rotation; fallback skips uninitialized engines and never runs on ErrProxyUnavailable.
- **Retries** — `retry-budget`: captcha/blocked/429/parser/engine-internal/proxy-unavailable/context are non-retryable; backoff ×(0.5+rand); request timeout = attempts + worst backoffs + 5s slack.
- **Circuit breaker** — `circuit-breaker`: 5 failures open, 60s recovery, 2 half-open successes close; AvgSuccessLatency powers fastest mode.
- **Proxy policy** — `proxy-policy`: X-Use-Proxy direct/tag overrides engine policy; request URL wins only when AllowRequestProxyURL; global proxy implies tag_pool.
- **Proxy registry** — `proxy-registry`: two-pass rotation (skip challenged, then relax); threshold-disable; all-exhausted tag quarantines 5m then probes least-failed; success clears quarantine.
- **Browser lifecycle** — `browser-lifecycle`: no browser.Timeout on persistent conns; Version() ping skipped within 5s of last OK; close page BEFORE disposing context; bounded ClosePageWithTimeout.
- **CDP proxy auth** — `proxy-auth-listener`: credentials stripped from --proxy-server, re-injected via Fetch.handleAuthRequired with concurrent acks; blocks HijackRequests on the same page.
- **Fingerprints** — `fingerprint-profiles`: embedded catalog, swiftshader-only on headless Linux, FNV(salt) weighted pick, runtime Chrome-major patch into UA+UA-CH brands, per-lane cookie save/restore/drop.
- **Raw TLS path** — `raw-tls-client`: Chrome_133/144/146 profiles hashed from lane salt; fixed header order; 64-entry LRU client cache; manual redirect loop validates every hop; dial-guard kills private IPs.
- **HTTP surface** — `server-routing`: /{engine}/search|image (+duck alias), POST /{engine}/parse, /mega/*, /extract*; RequestContext→RequestTimeout(exempt mega/extract)→CORS→logger.
- **Response cache** — `cache-contract`: SHA-256 of query + market triple; bypass on proxy-without-market, fallback responses, empty results; meta refreshed on HIT.
- **Extraction** — `extract-auto`: auto = fast pass then render only if <minRunes; rendered accepted only if longer than raw; trafilatura thin (<250 runes) falls back to whole readable body.
- **llms.txt** — `llms-txt`: site roots only, /llms-full.txt then /llms.txt, ≥200 non-HTML runes else silent fallthrough, mode_used="llms_txt".
- **Mega search** — `mega-clusters`: balanced parallel / any sequential-first / fastest by avg latency; deadline returns partials with failed engines listed; cluster score Σ(1/rank)/enginesQueried capped at 1.
- **Browser pool** — `server-browser-pool`: pool key scheme|host|user|sha16(userinfo); async close outside the mutex; idle sweeper at idleTTL/4.
- **Batch extract** — `batch-extract`: bare [{page_content, metadata}] array; bad URL ⇒ error item, never non-2xx; ≤20 URLs, bounded waves.
- **Self-check** — `fingerprint-check`: sequential detectors on a fresh browser, screenshot-on-failure artifacts, route disabled by default.
- **Yandex browser pagination** — `yandex-partial-success-funnel` + `yandex-hydration-re-poll`: mid-run captcha returns collected pages (error only when zero organic); 2s grace re-poll gated on element-list growth.
- **Yandex images** — `yandex-image-state-json`: data-state JSON entity harvest, three-tier selector fallback, rank=pos+1, no partial-success funnel.
- **Yandex URL policy** — `yandex-lr-region-policy`: p-page pagination; lang: language-subtag operator; rstr deliberately dropped (captcha cost).
- **Yandex AI-answer exclusion** — `yandex-neuro-answer-exclusion`: neuro_answer li skipped from ranks, captured as ai_summary feature with allowlisted Futuris citations.
- **Baidu organic admission** — `baidu-mu-canonical-url`: mu= canonical swap over /link?url= redirects; relative /s? links refused; h3-first row gate.
- **Baidu CSS-hash survival** — `baidu-hashed-class-prefix`: [class*='stem_'] prefixes for unique stems, exact hash pins for generic stems like text_.
- **Raw transport gates** — `raw-status-gate` + `raw-offset-rebase`: HTTP status→sentinel table before body read; skip→rebase→offset rank post-passes (ads immune).
- **fpcheck kernel** — `fpcheck-detection-kernel` + `fpcheck-rebrowser-verdicts`: normalize→emoji-first classify→keyword severity; JSON+table last-write-wins merge with rating>=1 fallback.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. For a new engine, copy the package shape from `engine-contract` (selectors.go / url.go / search.go / search_raw.go / parse_html.go / features.go) and register it in cmd/serve.go.

## Provenance
OpenSERP (github.com/karust/openserp, MIT), `main@29c7b0fb` (head == base_sha == origin/main after fetch rev-list=0, zero drift; re-verified at pass-3 entry); Codebase Memory project `ext-aeo-openserp` (2414 nodes / 12578 edges, index_mode FULL @2026-08-23T10:26Z, generation complete; parse_partial confined to testdata HTML fixtures). Direct tests exist and RUN here as of pass 2 (test-probe-runner lane): Go toolchain materialized at `$HOME/osrp-lane-go/go` (go1.24.6 = go.mod's toolchain line; lane-unique GOCACHE/GOTMPDIR because /tmp hits disk-quota and shared caches get sibling toolchain pollution) → **REAL GATE-5 RUNNER: `go test ./...` = 12 packages ok / 0 fail / 375 top-level tests passed (716 incl. subtests) / 1 env-skip** (`TestFindMoreResultsButton`, needs OPENSERP_INTEGRATION_TESTS=1; live-Chrome integration tests tag-gated off by design). All 27 capsule Probes were executed against this suite; five written probe patterns matched zero real test names and were REPAIRED to executed-green commands inside their capsules (probe-anchor lesson: derive from the live test inventory, never from file-name guesses). PASS-3 ADDENDUM: all 8 new capsules' planes re-executed under the same runner — `go test ./yandex/ ./baidu/ ./core/fpcheck/...` ok, targeted `-run 'TestParseYandexHTML|TestYandexPageTypeSelectors|TestYandexClassifyRawHTML|TestParseBaiduHTML|TestBuildURL' -v` all PASS (incl. subtests TestBuildURLLanguageOperator ×4, TestBuildURLRegionLR ×5); Python-equivalent probes in the 8 new capsules executed byte-exact pre-write with expectations derived from live grep.

## Full view (memory graph)
Revalidate `ext-aeo-openserp` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Coverage check on all 63 cited paths returned no_recorded_issue/metadata_match at the pinned commit. Pass-2 upgrade: gate-5 is no longer deterministic-probes-only — the repo's own `go test ./...` suite runs green at the pin (12 pkgs / 375 tests), and every capsule carries both its original Python-equivalent probe and an executed real-runner line.

## Boundaries
Adopt the engine contract, sentinel-error policy, rank-state math, dual-parser classification, retry/CB/proxy pipelines, cache bypass rules, extraction escalation ladders, cluster scoring, and (pass 3) the partial-success captcha funnel + fpcheck detection kernel — they are engine-neutral. Adapt per-engine selectors, URL dialects, locale tables, profile catalogs, detector-site markup, and hashed-CSS class names (they rot; re-derive against live SERPs). Omit openserp.org cloud specifics and the hosted-version branding; treat core/fpcheck detector markup as diagnostic-only even though its kernel logic is portable.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`baidu-hashed-class-prefix.md`](./baidu-hashed-class-prefix.md)
- [`baidu-mu-canonical-url.md`](./baidu-mu-canonical-url.md)
- [`batch-extract.md`](./batch-extract.md)
- [`browser-lifecycle.md`](./browser-lifecycle.md)
- [`cache-contract.md`](./cache-contract.md)
- [`circuit-breaker.md`](./circuit-breaker.md)
- [`dual-parser.md`](./dual-parser.md)
- [`engine-contract.md`](./engine-contract.md)
- [`error-taxonomy.md`](./error-taxonomy.md)
- [`extract-auto.md`](./extract-auto.md)
- [`fingerprint-check.md`](./fingerprint-check.md)
- [`fingerprint-profiles.md`](./fingerprint-profiles.md)
- [`fpcheck-detection-kernel.md`](./fpcheck-detection-kernel.md)
- [`fpcheck-rebrowser-verdicts.md`](./fpcheck-rebrowser-verdicts.md)
- [`google-adapter.md`](./google-adapter.md)
- [`llms-txt.md`](./llms-txt.md)
- [`mega-clusters.md`](./mega-clusters.md)
- [`proxy-auth-listener.md`](./proxy-auth-listener.md)
- [`proxy-policy.md`](./proxy-policy.md)
- [`proxy-registry.md`](./proxy-registry.md)
- [`rank-state.md`](./rank-state.md)
- [`raw-offset-rebase.md`](./raw-offset-rebase.md)
- [`raw-status-gate.md`](./raw-status-gate.md)
- [`raw-tls-client.md`](./raw-tls-client.md)
- [`region-uule.md`](./region-uule.md)
- [`resilient-pipeline.md`](./resilient-pipeline.md)
- [`response-envelope.md`](./response-envelope.md)
- [`result-normalization.md`](./result-normalization.md)
- [`retry-budget.md`](./retry-budget.md)
- [`serp-features.md`](./serp-features.md)
- [`server-browser-pool.md`](./server-browser-pool.md)
- [`server-routing.md`](./server-routing.md)
- [`url-builders.md`](./url-builders.md)
- [`yandex-hydration-re-poll.md`](./yandex-hydration-re-poll.md)
- [`yandex-image-state-json.md`](./yandex-image-state-json.md)
- [`yandex-lr-region-policy.md`](./yandex-lr-region-policy.md)
- [`yandex-neuro-answer-exclusion.md`](./yandex-neuro-answer-exclusion.md)
- [`yandex-partial-success-funnel.md`](./yandex-partial-success-funnel.md)
