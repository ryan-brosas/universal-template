---
name: litellm-foundation
description: "Use when porting multi-provider LLM gateway machinery — provider routing, exception mapping, cooldown/retry ladders, streaming normalization, cost ledgers. Source code and direct tests are ground truth."
---

# litellm: Multi-Provider LLM Gateway Kernel Foundation

## Use this for
Use when building or porting a provider-routing gateway: resolving bare model strings to (provider, key, api_base), mapping vendor failures onto one catchable exception hierarchy, deciding deployment cooldowns and retry counts, normalizing heterogeneous stream chunks, enforcing TPM/RPM budgets, and computing per-request USD cost. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/provider-resolution-ladder.md` — full precedence of `get_llm_provider` incl. prefix reconciliation, JSON providers, proxy default; boundary is the resolution ladder only.
- `references/api-base-endpoint-matching.md` — parsed-URL segment-boundary endpoint matching that prevents credential exfiltration via lookalike api_bases.
- `references/exception-mapping-status-table.md` — status→exception table every provider maps to plus explicit per-provider deviations; boundary ends at raise time.
- `references/ratelimit-unified-error.md` — one RateLimitError carrying vendor + proxy-side limits with quarantined vendor headers.
- `references/cooldown-decision-ladder.md` — status filter → per-deployment policy → error-rate statistics; single-deployment safety net.
- `references/retry-loop-num-retries-resolution.md` — num_retries precedence chain and the raise-immediately taxonomy inside `should_retry_this_error`.
- `references/streaming-chunk-normalization.md` — CustomStreamWrapper dispatch→normalize→gate pipeline incl. finish-reason deferral.
- `references/cost-lookup-and-cache-normalization.md` — price-key lookup ladder + cache-token normalization to the "prompt includes cache" contract.
- `references/tpm-rpm-minute-window-limiter.md` — local-first minute-window increments with fail-open infrastructure handling.
- `references/enforce-model-rate-limit-check.md` — enforcing per-deployment TPM/RPM across all strategies; TPM local-read vs RPM increment-first asymmetry.
- `references/itpm-otpm-reservation-ledger.md` — reserve/reconcile/refund protocol for separate input/output token limits incl. forged-sentinel stripping.
- `references/router-budget-filter.md` — provider/deployment/tag $ budgets as a filter with window reset choreography and write-behind Redis sync.
- `references/write-behind-spend-batching.md` — BaseRoutingStrategy snapshot→compress→pipeline-push→delta-merge substrate.
- `references/lowest-latency-scoring.md` — per-token-normalized latency history, TTFT-for-streams split, timeout penalties, buffer-band selection.
- `references/lowest-cost-scoring.md` — static price-key scoring with unknown-model default; why cost history is never actually recorded.
- `references/weighted-shuffle-least-busy.md` — weighted random pick with zero-total metric skip; advisory in-flight traffic tracking.
- `references/deployment-affinity-claim-pins.md` — Lua first-writer-wins stickiness claims keyed by hashed API key / session id with pod-local degradation.
- `references/encrypted-content-affinity.md` — cache-free pinning by decoding deployment ids from encrypted-content markers, with encryption-boundary peer fallback.
- `references/prompt-caching-pin-and-continuity.md` — prefix-hash pinning for auto-cached prompts (lowest-threshold group gate) + previous_response_id continuity paths.
- `references/router-filter-pipeline-order.md` — the ordered candidate-narrowing pipeline from cooldown to weighted-failover exclusion and post-pick checks.
- `references/completion-with-fallbacks-loop.md` — standalone fallback chain with per-attempt deepcopy isolation and attempt-index headers.
- `references/completion-dispatch-boundary.md` — central `main.completion` elif dispatch plus the single try/except→exception_type boundary that keeps every failure OpenAI-compatible.
- `references/optional-params-validation-ladder.md` — non-default-param validation: skip-list → drop-or-UnsupportedParamsError → per-provider `map_openai_params`; forced status-400 subclass invariant.
- `references/chunk-aggregation-cursor-reset.md` — ChunkProcessor fold kernel: conditional created_at sort, (index, field) tool-call joins, last-wins usage with the Anthropic message_start cursor=1 reset and token-counter fallback.
- `references/response-cache-key-derivation.md` — preset short-circuit, API-params-only key material, sha256-hex + namespace prefixing, semantic tenant scoping.
- `references/token-counter-contract.md` — text/messages exclusivity, response-vs-request overhead split, disable kill switch, unknown-model encoding fallback, image-token validation.
- `references/custom-callback-hook-surface.md` — CustomLogger hook taxonomy: sync five + async twins, transformation-vs-logging pre-request hook, accounting-vs-content flag.
- `references/router-timeout-resolution-chain.md` — three-stage timeout ladder: Router init rungs → per-deployment `_get_timeout` → `CompletionTimeout.resolve` coercion (httpx.Timeout only for openai/azure/bedrock).
- `references/logging-callback-fanout.md` — Logging success/failure fan-out: event-typed once-only latch, redact-before-hooks, fail-soft per-callback isolation.
- `references/message-redaction-gate.md` — redaction precedence (dynamic param > disable-header > enable-header > global) with in-place dict mutation + deep-copied result split.
- `references/prompt-factory-dispatch.md` — messages→provider-prompt dispatch: custom_prompt_dict override inside handlers, provider elifs, HF heuristics, never-raising fallback.
- `references/supported-openai-params-ladder.md` — provider→supported-params resolver with additive base_model union, None→openai fallback, allowed_openai_params extension.
- `references/optional-params-modality-variants.md` — embeddings/image-gen/transcription validators: per-modality default tables, config-first mapping, empty-value scrub.

## Capsule map
- **Provider routing** — `provider-resolution-ladder`: ordered model-string→(model, provider, key, api_base) ladder where rung order decides which credentials attach to traffic.
- **Provider routing** — `api-base-endpoint-matching`: exact-host + `/`-anchored path match; substring matching reopens a credential-forwarding hole.
- **Error surface** — `exception-mapping-status-table`: 9 statuses × providers map to one class+status each; deviations are explicit table entries.
- **Error surface** — `ratelimit-unified-error`: unified 429 with category/dimension attributes; vendor response headers never auto-copy to `e.headers`.
- **Reliability** — `cooldown-decision-ladder`: cool down 429/401/404/408/5XX, skip other 4XX unless an explicit named-type policy opts in; error-rate statistics as base case.
- **Reliability** — `retry-loop-num-retries-resolution`: request > deployment-hint > policy > router-default > 0; context-window/content-policy/not-found/auth-single raise now.
- **Streaming** — `streaming-chunk-normalization`: finish_reason only on the trailing empty-delta chunk; suppress empty chunks; flush holding chunk at finish.
- **Usage & spend** — `cost-lookup-and-cache-normalization`: region-prefixed > provider-prefixed > bare price keys; Anthropic-style prompt totals adjusted before pricing helpers.
- **Budgets** — `tpm-rpm-minute-window-limiter`: `{id}:{name}:rpm:{HH-MM}` keys, local short-circuit then shared increment, redis outage degrades to no limiting.
- **Enforcement** — `enforce-model-rate-limit-check`: TPM reads local post-hoc counters while RPM increments first; whole check fails open on infra errors.
- **Enforcement** — `itpm-otpm-reservation-ledger`: atomic reserve-with-rollback, same-key reconcile-delta, refund-on-failure; bare `total_tokens` never resolves usage.
- **Budgets** — `router-budget-filter`: spend keys `{kind}_spend:{id}:{duration}` with anchored windows reset on expiry; filter contract composes with any picker.
- **Substrate** — `write-behind-spend-batching`: in-memory-first increments, periodic compressed Redis pipeline push, snapshot-based delta merge.
- **Strategies** — `lowest-latency-scoring`: ≤10-sample sliding latency/TTFT lists normalized per completion token; 1000s timeout penalty; random within buffer band of best.
- **Strategies** — `lowest-cost-scoring`: static input+output price-key pick (5.0+5.0 default); handler records only tpm/rpm counters, never cost history.
- **Strategies** — `weighted-shuffle-least-busy`: weight/rpm/tpm weighted random skipping zero-total metrics; least-busy seeds unseen deployments to zero traffic.
- **Affinity** — `deployment-affinity-claim-pins`: previous_response_id > session > user-key pins via Lua get-or-set-or-refresh; delete-before-set local writes keep TTLs honest.
- **Affinity** — `encrypted-content-affinity`: decode model_id from encitem_/litellm_enc: markers; fall back to (api_base, api_key) boundary peers; else fail fast mirroring cooldown status.
- **Affinity** — `prompt-caching-pin-and-continuity`: pin by hash of messages-as-they-will-be-sent behind a lowest-min-token group gate; deprecated Responses-API check folds into the unified affinity callback.
- **Wiring** — `router-filter-pipeline-order`: team → web-search → health → cooldown → callback filters → strategy checks → tag → plugin → order → failover-exclusion, then semaphore-scoped per-deployment pre-call checks.
- **Fallbacks** — `completion-with-fallbacks-loop`: `[original] + fallbacks` chain, safe_deep_copy per attempt, first non-None response annotated with attempted-fallbacks index.
- **Request pipeline** — `completion-dispatch-boundary`: provider-specific branches before the openai-compatible catch-all; unknown provider raises inside try and still surfaces as BadRequestError/400 via exception_type.
- **Request pipeline** — `optional-params-validation-ladder`: only user-set OpenAI params validated; openai supported-list fallback for unknown providers; UnsupportedParamsError always 400 regardless of raise-site code.
- **Streaming** — `chunk-aggregation-cursor-reset`: truthy-but-stale usage must not suppress text-based estimation; heuristics gated on `_hidden_params.custom_llm_provider`.
- **Caching** — `response-cache-key-derivation`: litellm_params never enter key material; keys are sha256 hex optionally namespace-prefixed; semantic caches append tenant scope and exclude scope params.
- **Usage & spend** — `token-counter-contract`: overhead tokens added only for request-side counting; every estimation path degrades to 0, never raises through callers.
- **Observability** — `custom-callback-hook-surface`: log hooks observe, `async_pre_request_hook` transforms; content-judging hooks opt in via class flag or batch uploads get charged per record.
- **Reliability** — `router-timeout-resolution-chain`: first-non-None-wins with truthy `or` (0 never wins); httpx.Timeout survives only for openai/azure/bedrock; explicit 6000 honored, only unset falls back to the 600 sentinel.
- **Observability** — `logging-callback-fanout`: four independent once-only event flags; result redacted before hooks; every sink failure swallowed and counted, never raised.
- **Observability** — `message-redaction-gate`: dynamic param > disable-header > enable-header > global; shared dict mutated in place, returned response is a redacted deepcopy; async/opaque shapes collapse to a sentinel.
- **Request pipeline** — `prompt-factory-dispatch`: handler-level custom_prompt_dict override precedes provider elifs → HF model-name heuristics → chat-template fallback → default_pt on exception; function_call_prompt mutates messages in place.
- **Request pipeline** — `supported-openai-params-ladder`: manager-first resolution with order-preserving base_model union; None means unmapped and triggers the consumer's openai retry; allowed_openai_params appends last.
- **Request pipeline** — `optional-params-modality-variants`: each modality owns its default table + config lookup; drop-or-UnsupportedParamsError(→400) contract holds across modalities; empty values scrubbed before send.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question against Codebase Memory project `litellm` (renamed from `ext-litellm`; same checkout and HEAD). Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Candidate seams for future passes live in `/mnt/hdd/utopia/inspo/litellm-work/research.md` NEXT-PASS TARGETS.

## Provenance
litellm (MIT), `litellm_internal_staging@f005afa1`; Codebase Memory project `litellm`, root `/mnt/hdd/utopia/inspo/litellm` (FULL mode, 221,689 nodes / 1,318,453 edges, ready; head==base==working-tree HEAD f005afa14603 verified live 2026-08-25 via index_status + git rev-parse; parse_partial ×114 all YAML/Dockerfile/helm/SQL fixtures, none cited). Passes 1–2 (2026-08-24) ran under this project's former name `ext-litellm` at the same HEAD: pass 1 +9, pass 2 +12 (9→21). Pass 3 (2026-08-25, miner-litellm lane): +6 capsule-v2 (21→27) mining the request-lifecycle core — main.completion dispatch boundary (main.py :4902-5796), get_optional_params validation ladder (utils.py :3943-4541 + exceptions.py :911-933), ChunkProcessor aggregation + Anthropic cursor reset (streaming_chunk_builder_utils.py :176-1025), Cache.get_cache_key derivation (caching.py :325-490), token_counter contract (:345-620), CustomLogger hook surface (custom_logger.py :61-1065) — with four executed API probes and the cursor regression module run live (11 passed). Pass 4 (2026-08-26, miner-litellm lane, same pin/generation): +6 capsule-v2 (27→33) mining the cross-cutting planes — router timeout chain (router.py :691-697/:3320-3385 + completion_timeout.py :13-70 + utils.supports_httpx_timeout :2229-2238; tests 10+8 passed live), Logging success/failure fan-out (litellm_logging.py :1850-1873/:2246-2678/:3098-3290; double-log test passed live), message-redaction gate (redact_messages.py :229-375; 35 tests passed live), prompt factory dispatch (factory.py :5156-5173/:5258-5361 + main.py :5398-5402 + vllm handler.py :56-66; 97 unit tests passed live), supported-openai-params ladder (get_supported_openai_params.py :1-290 whole module + utils.py :4051-4060 openai fallback; 10 tests passed live; note: function moved out of utils.py), modality optional-params variants (utils.py :3011-3097/:3117-3239/:3242-3341; 17 adjacent tests passed live; local_testing/test_utils runners blocked by missing vcr/backoff).

## Full view (memory graph)
Revalidate project `litellm` before porting: run `index_status(project="litellm", verbose=true)`, `check_index_coverage`, `search_graph`, `trace_path`, `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/litellm`, branch `litellm_internal_staging`, mode FULL. Freshness proven by resolving drift-introduced test `test_an_upstream_status_maps_to_one_exception_per_provider` (tests/test_litellm/litellm_core_utils/test_exception_mapping_utils.py:891-904) rank-1 via search_graph at the pin; pass-2 seams re-verified live (rank-1 line-exact ×4 incl. `_claim_pin` :344-385); pass-3 seams re-verified live (BM25/name rank-1 ×5 incl. `get_optional_params` :3943-4541 and adversarial cursor-prose query landing rank-1 on the regression test, rank-2 on `_reset_anthropic_cursor_completion_tokens` :881-917). Coverage caveat: BM25 search works on symbol tokens (Function-class nodes); use file-stem needles via search_graph queries like `_endpoint_matches_api_base` rather than prose phrases on doc-heavy paths; semantic_query on cache-key phrasing returns minified proxy UI bundles (`proxy/_experimental/out/**`) — never cite them.

## Boundaries
Adopt the pure contracts: resolution ladder ordering, status-table mapping with explicit deviations, header quarantine, minute-window limiter protocol, finish-reason deferral, reserve/reconcile/refund ITPM-OTPM ledger, first-writer-wins affinity claims, filter-not-picker budget gating, per-token-normalized latency scoring, attempt-indexed fallback headers, and the ordered candidate-narrowing pipeline. Adapt host-specific integrations: provider tables/config classes, redis cache backends, FastAPI detail mirroring, proxy-body error extraction, weight/price field names. Omit product surface: proxy server UI/auth planes (`litellm/proxy/**`), enterprise/, helm/docker packaging, UI dashboard, rust_bridge — none are ported by these capsules.
