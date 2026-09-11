<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# litellm: Multi-Provider LLM Gateway Kernel Foundation

## Use this for
Use when building or porting a provider-routing gateway: resolving bare model strings to (provider, key, api_base), mapping vendor failures onto one catchable exception hierarchy, deciding deployment cooldowns and retry counts, normalizing heterogeneous stream chunks, enforcing TPM/RPM budgets, and computing per-request USD cost. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./provider-resolution-ladder.md` — full precedence of `get_llm_provider` incl. prefix reconciliation, JSON providers, proxy default; boundary is the resolution ladder only.
- `./api-base-endpoint-matching.md` — parsed-URL segment-boundary endpoint matching that prevents credential exfiltration via lookalike api_bases.
- `./exception-mapping-status-table.md` — status→exception table every provider maps to plus explicit per-provider deviations; boundary ends at raise time.
- `./ratelimit-unified-error.md` — one RateLimitError carrying vendor + proxy-side limits with quarantined vendor headers.
- `./cooldown-decision-ladder.md` — status filter → per-deployment policy → error-rate statistics; single-deployment safety net.
- `./retry-loop-num-retries-resolution.md` — num_retries precedence chain and the raise-immediately taxonomy inside `should_retry_this_error`.
- `./streaming-chunk-normalization.md` — CustomStreamWrapper dispatch→normalize→gate pipeline incl. finish-reason deferral.
- `./cost-lookup-and-cache-normalization.md` — price-key lookup ladder + cache-token normalization to the "prompt includes cache" contract.
- `./tpm-rpm-minute-window-limiter.md` — local-first minute-window increments with fail-open infrastructure handling.
- `./enforce-model-rate-limit-check.md` — enforcing per-deployment TPM/RPM across all strategies; TPM local-read vs RPM increment-first asymmetry.
- `./itpm-otpm-reservation-ledger.md` — reserve/reconcile/refund protocol for separate input/output token limits incl. forged-sentinel stripping.
- `./router-budget-filter.md` — provider/deployment/tag $ budgets as a filter with window reset choreography and write-behind Redis sync.
- `./write-behind-spend-batching.md` — BaseRoutingStrategy snapshot→compress→pipeline-push→delta-merge substrate.
- `./lowest-latency-scoring.md` — per-token-normalized latency history, TTFT-for-streams split, timeout penalties, buffer-band selection.
- `./lowest-cost-scoring.md` — static price-key scoring with unknown-model default; why cost history is never actually recorded.
- `./weighted-shuffle-least-busy.md` — weighted random pick with zero-total metric skip; advisory in-flight traffic tracking.
- `./deployment-affinity-claim-pins.md` — Lua first-writer-wins stickiness claims keyed by hashed API key / session id with pod-local degradation.
- `./encrypted-content-affinity.md` — cache-free pinning by decoding deployment ids from encrypted-content markers, with encryption-boundary peer fallback.
- `./prompt-caching-pin-and-continuity.md` — prefix-hash pinning for auto-cached prompts (lowest-threshold group gate) + previous_response_id continuity paths.
- `./router-filter-pipeline-order.md` — the ordered candidate-narrowing pipeline from cooldown to weighted-failover exclusion and post-pick checks.
- `./completion-with-fallbacks-loop.md` — standalone fallback chain with per-attempt deepcopy isolation and attempt-index headers.
- `./completion-dispatch-boundary.md` — central `main.completion` elif dispatch plus the single try/except→exception_type boundary that keeps every failure OpenAI-compatible.
- `./optional-params-validation-ladder.md` — non-default-param validation: skip-list → drop-or-UnsupportedParamsError → per-provider `map_openai_params`; forced status-400 subclass invariant.
- `./chunk-aggregation-cursor-reset.md` — ChunkProcessor fold kernel: conditional created_at sort, (index, field) tool-call joins, last-wins usage with the Anthropic message_start cursor=1 reset and token-counter fallback.
- `./response-cache-key-derivation.md` — preset short-circuit, API-params-only key material, sha256-hex + namespace prefixing, semantic tenant scoping.
- `./token-counter-contract.md` — text/messages exclusivity, response-vs-request overhead split, disable kill switch, unknown-model encoding fallback, image-token validation.
- `./custom-callback-hook-surface.md` — CustomLogger hook taxonomy: sync five + async twins, transformation-vs-logging pre-request hook, accounting-vs-content flag.
- `./router-timeout-resolution-chain.md` — three-stage timeout ladder: Router init rungs → per-deployment `_get_timeout` → `CompletionTimeout.resolve` coercion (httpx.Timeout only for openai/azure/bedrock).
- `./logging-callback-fanout.md` — Logging success/failure fan-out: event-typed once-only latch, redact-before-hooks, fail-soft per-callback isolation.
- `./message-redaction-gate.md` — redaction precedence (dynamic param > disable-header > enable-header > global) with in-place dict mutation + deep-copied result split.
- `./prompt-factory-dispatch.md` — messages→provider-prompt dispatch: custom_prompt_dict override inside handlers, provider elifs, HF heuristics, never-raising fallback.
- `./supported-openai-params-ladder.md` — provider→supported-params resolver with additive base_model union, None→openai fallback, allowed_openai_params extension.
- `./optional-params-modality-variants.md` — embeddings/image-gen/transcription validators: per-modality default tables, config-first mapping, empty-value scrub.
- `./logging-callback-gate-and-payload-helpers.md` — per-callback no-log/kill-switch/header gate; shared success/failure helper fns with the four-rung response_cost ladder and fail-before-init tolerance.
- `./async-logging-handler-twins.md` — async handler bodies sharing the sync helpers; fire-and-forget success queue vs inline-sync failure; dispatch plane with final-stream dedup stamp.
- `./hf-chat-template-and-custom-prompt.md` — HF template acquisition with failure memoization, sandboxed jinja render with system-slot trial detection and alternation repair; role-dict bos/eos state machine.
- `./provider-config-manager-resolution.md` — special cases → lazy O(1) factory map → JSON provider fallback → None; base_model threading for Azure deployment names.
- `./provider-specific-params-extra-body.md` — unknown-param fold: extra_body merge for the OpenAI family vs flat copy elsewhere; two-layer drop gate; None-safe normalization.
- `./map-openai-params-provider-tail.md` — per-provider map_openai_params dispatch: model-list / route-prefix / detection-model patterns, specific-before-generic order, caller-sent-only allowed-param forwarding.
- `./logging-worker-bounded-queue.md` — bounded best-effort callback queue: non-blocking enqueue, cooldown-gated aggressive clear, contextvars captured at enqueue, join-not-empty flush, capped atexit drain.
- `./http-client-defaults-plane.md` — cached pooled httpx clients: explicit-global timeout honoring, ownership + refcount close gate, cookie opacity at both transport layers.
- `./model-group-rate-limit-event.md` — special_failure_handlers two-trigger gate (error-vocabulary string match OR single-deployment base case) firing before the double-log latch, with router raise-site cross-check.
- `./passthrough-logging-contract.md` — normalize_logging_result passthrough branch + logging_non_streaming_response: endpoint-gated transform reuse with a sentinel message recovers usage from raw responses.

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
- **Observability** — `logging-callback-gate-and-payload-helpers`: global kill-switch > no-log (with `_PROXY_` cost-tracking exemption) > header disable; zero cost from intermediate retries never preserved, positive pre-computed cost always is.
- **Observability** — `async-logging-handler-twins`: parity via shared helper fns; assembled streams bypass the double-log latch and dedup on the dispatch stamp; success is fire-and-forget while failure keeps an inline sync component retry logic depends on.
- **Request pipeline** — `hf-chat-template-and-custom-prompt`: explicit template > tokenizer_config.json > .jinja file with process-lifetime failure memoization; system support detected by trial render; one-flag bos/eos state machine keyed on role names.
- **Request pipeline** — `provider-config-manager-resolution`: rung order is contract — OpenAI o-series/GPT-5 before the map, Azure before the map for base_model threading, JSON fallback, None means unmapped.
- **Request pipeline** — `provider-specific-params-extra-body`: SDK-wrapped providers fold unknown params into extra_body, others get flat keys; drop list is opt-out and consulted at both extraction and fold layers.
- **Request pipeline** — `map-openai-params-provider-tail`: model-list > route-prefix > detection-model rungs must precede the manager-result and openai-like fallbacks; route prefixes match as path segments, never substrings; allowed params forward only when caller-sent.
- **Observability** — `logging-worker-bounded-queue`: put_nowait never blocks the request path; full queue degrades to a cooldown-gated 50% aggressive clear (semaphore-bypassing) or a delayed retry; flush is join-not-empty; atexit drain caps on iterations AND wall time.
- **Reliability** — `http-client-defaults-plane`: an explicit global timeout reaches cached clients, else the shared 600s sentinel by identity; a handler closes its client only when it owns it AND is sole referrer (refcount ≤ 2 read at the call site); cookies are opaque at both httpx and aiohttp layers.
- **Observability** — `model-group-rate-limit-event`: error-vocabulary string match OR model_group_size==1 base case; fires before the double-log latch so every attempt alerts; both inputs are produced exclusively by the router.
- **Observability** — `passthrough-logging-contract`: raw Response results normalize in the shared success helper via provider config lookup; endpoint-gated transform reuse with a sentinel message recovers usage; no config degrades to the raw result.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question against Codebase Memory project `litellm` (renamed from `ext-litellm`; same checkout and HEAD). Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Candidate seams for future passes live in `$REFERENCE_ROOT/.skill-mining-work/litellm/research.md` NEXT-PASS TARGETS.

## Provenance
litellm (MIT), `litellm_internal_staging@f005afa1`; Codebase Memory project `litellm`, root `$REFERENCE_ROOT/litellm` (FULL mode, 221,689 nodes / 1,318,453 edges, ready; head==base==working-tree HEAD f005afa14603 verified live 2026-08-25 via index_status + git rev-parse; parse_partial ×114 all YAML/Dockerfile/helm/SQL fixtures, none cited). Passes 1–2 (2026-08-24) ran under this project's former name `ext-litellm` at the same HEAD: pass 1 +9, pass 2 +12 (9→21). Pass 3 (2026-08-25, miner-litellm lane): +6 capsule-v2 (21→27) mining the request-lifecycle core — main.completion dispatch boundary (main.py :4902-5796), get_optional_params validation ladder (utils.py :3943-4541 + exceptions.py :911-933), ChunkProcessor aggregation + Anthropic cursor reset (streaming_chunk_builder_utils.py :176-1025), Cache.get_cache_key derivation (caching.py :325-490), token_counter contract (:345-620), CustomLogger hook surface (custom_logger.py :61-1065) — with four executed API probes and the cursor regression module run live (11 passed). Pass 4 (2026-08-26, miner-litellm lane, same pin/generation): +6 capsule-v2 (27→33) mining the cross-cutting planes — router timeout chain (router.py :691-697/:3320-3385 + completion_timeout.py :13-70 + utils.supports_httpx_timeout :2229-2238; tests 10+8 passed live), Logging success/failure fan-out (litellm_logging.py :1850-1873/:2246-2678/:3098-3290; double-log test passed live), message-redaction gate (redact_messages.py :229-375; 35 tests passed live), prompt factory dispatch (factory.py :5156-5173/:5258-5361 + main.py :5398-5402 + vllm handler.py :56-66; 97 unit tests passed live), supported-openai-params ladder (get_supported_openai_params.py :1-290 whole module + utils.py :4051-4060 openai fallback; 10 tests passed live; note: function moved out of utils.py), modality optional-params variants (utils.py :3011-3097/:3117-3239/:3242-3341; 17 adjacent tests passed live; local_testing/test_utils runners blocked by missing vcr/backoff). Pass 5 (2026-08-27, miner-litellm lane, same pin; Codebase Memory MCP not connected — direct source+test reading fallback): +5 capsule-v2 (33→38) mining the logging-plane depth and config/param resolution — callback gate + payload helpers (litellm_logging.py :1875-1897/:1964-2018/:2047-2122/:3022-3064; 4 tests passed live), async handler twins + dispatch plane (litellm_logging.py :1734-1848/:2697-2998/:3311-3375 + utils.py :1137-1166/:1821-1885; 8 dispatch tests passed live), HF chat template + custom_prompt interiors (factory.py :368-441/:498-549/:579-603/:5216-5255 + huggingface_template_handler.py whole file; factory unit suite 97 passed live, direct test vcr-blocked), ProviderConfigManager resolution (utils.py :7823-8121 + json_loader.py; 25+18 tests passed live), provider-specific params extra_body fold (utils.py :4544-4582/:2991-2995 + llm_request_utils.py :6-30; hosted_vllm suite 7 passed live). Pass 6 (2026-08-28, miner-litellm lane, same pin; Codebase Memory MCP not connected — direct source+test reading fallback): +5 capsule-v2 (38→43) closing the request-pipeline tail and three observability depths — map_openai_params provider elif tail (utils.py :4066-4541 + bedrock common_utils.py :926-987 route resolution + :4585-4605 overrides; vertex tool-param suite 8 passed + bedrock route suite 14 passed live), LoggingWorker bounded queue (logging_worker.py whole file + constants.py :475-484; dedicated suite 12 passed live), http-client defaults plane (llms/custom_httpx/http_handler.py :134-169/:542-630/:936-942/:1089-1094/:1128-1182/:1443-1540; timeout/refcount/cookie selection 7 passed live), model-group rate-limit event (litellm_logging.py :3066-3097/:3321 + types/router.py :574/:773-800 + router.py :6667-6672/:10868/:12035-:12212; end-to-end test vcr-blocked, full source chain read), passthrough logging contract (litellm_logging.py :1903-1937/:2078-2088 + utils.py :8618-8646 + azure/bedrock/base passthrough transformations; azure suite 2 passed live).

## Full view (memory graph)
Revalidate project `litellm` before porting: run `index_status(project="litellm", verbose=true)`, `check_index_coverage`, `search_graph`, `trace_path`, `get_code_snippet`. Graph root `$REFERENCE_ROOT/litellm`, branch `litellm_internal_staging`, mode FULL. Freshness proven by resolving drift-introduced test `test_an_upstream_status_maps_to_one_exception_per_provider` (tests/test_litellm/litellm_core_utils/test_exception_mapping_utils.py:891-904) rank-1 via search_graph at the pin; pass-2 seams re-verified live (rank-1 line-exact ×4 incl. `_claim_pin` :344-385); pass-3 seams re-verified live (BM25/name rank-1 ×5 incl. `get_optional_params` :3943-4541 and adversarial cursor-prose query landing rank-1 on the regression test, rank-2 on `_reset_anthropic_cursor_completion_tokens` :881-917). Coverage caveat: BM25 search works on symbol tokens (Function-class nodes); use file-stem needles via search_graph queries like `_endpoint_matches_api_base` rather than prose phrases on doc-heavy paths; semantic_query on cache-key phrasing returns minified proxy UI bundles (`proxy/_experimental/out/**`) — never cite them.

## Boundaries
Adopt the pure contracts: resolution ladder ordering, status-table mapping with explicit deviations, header quarantine, minute-window limiter protocol, finish-reason deferral, reserve/reconcile/refund ITPM-OTPM ledger, first-writer-wins affinity claims, filter-not-picker budget gating, per-token-normalized latency scoring, attempt-indexed fallback headers, and the ordered candidate-narrowing pipeline. Adapt host-specific integrations: provider tables/config classes, redis cache backends, FastAPI detail mirroring, proxy-body error extraction, weight/price field names. Omit product surface: proxy server UI/auth planes (`litellm/proxy/**`), enterprise/, helm/docker packaging, UI dashboard, rust_bridge — none are ported by these capsules.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`api-base-endpoint-matching.md`](./api-base-endpoint-matching.md)
- [`async-logging-handler-twins.md`](./async-logging-handler-twins.md)
- [`chunk-aggregation-cursor-reset.md`](./chunk-aggregation-cursor-reset.md)
- [`completion-dispatch-boundary.md`](./completion-dispatch-boundary.md)
- [`completion-with-fallbacks-loop.md`](./completion-with-fallbacks-loop.md)
- [`cooldown-decision-ladder.md`](./cooldown-decision-ladder.md)
- [`cost-lookup-and-cache-normalization.md`](./cost-lookup-and-cache-normalization.md)
- [`custom-callback-hook-surface.md`](./custom-callback-hook-surface.md)
- [`deployment-affinity-claim-pins.md`](./deployment-affinity-claim-pins.md)
- [`encrypted-content-affinity.md`](./encrypted-content-affinity.md)
- [`enforce-model-rate-limit-check.md`](./enforce-model-rate-limit-check.md)
- [`exception-mapping-status-table.md`](./exception-mapping-status-table.md)
- [`hf-chat-template-and-custom-prompt.md`](./hf-chat-template-and-custom-prompt.md)
- [`http-client-defaults-plane.md`](./http-client-defaults-plane.md)
- [`itpm-otpm-reservation-ledger.md`](./itpm-otpm-reservation-ledger.md)
- [`logging-callback-fanout.md`](./logging-callback-fanout.md)
- [`logging-callback-gate-and-payload-helpers.md`](./logging-callback-gate-and-payload-helpers.md)
- [`logging-worker-bounded-queue.md`](./logging-worker-bounded-queue.md)
- [`lowest-cost-scoring.md`](./lowest-cost-scoring.md)
- [`lowest-latency-scoring.md`](./lowest-latency-scoring.md)
- [`map-openai-params-provider-tail.md`](./map-openai-params-provider-tail.md)
- [`message-redaction-gate.md`](./message-redaction-gate.md)
- [`model-group-rate-limit-event.md`](./model-group-rate-limit-event.md)
- [`optional-params-modality-variants.md`](./optional-params-modality-variants.md)
- [`optional-params-validation-ladder.md`](./optional-params-validation-ladder.md)
- [`passthrough-logging-contract.md`](./passthrough-logging-contract.md)
- [`prompt-caching-pin-and-continuity.md`](./prompt-caching-pin-and-continuity.md)
- [`prompt-factory-dispatch.md`](./prompt-factory-dispatch.md)
- [`provider-config-manager-resolution.md`](./provider-config-manager-resolution.md)
- [`provider-resolution-ladder.md`](./provider-resolution-ladder.md)
- [`provider-specific-params-extra-body.md`](./provider-specific-params-extra-body.md)
- [`ratelimit-unified-error.md`](./ratelimit-unified-error.md)
- [`response-cache-key-derivation.md`](./response-cache-key-derivation.md)
- [`retry-loop-num-retries-resolution.md`](./retry-loop-num-retries-resolution.md)
- [`router-budget-filter.md`](./router-budget-filter.md)
- [`router-filter-pipeline-order.md`](./router-filter-pipeline-order.md)
- [`router-timeout-resolution-chain.md`](./router-timeout-resolution-chain.md)
- [`streaming-chunk-normalization.md`](./streaming-chunk-normalization.md)
- [`supported-openai-params-ladder.md`](./supported-openai-params-ladder.md)
- [`token-counter-contract.md`](./token-counter-contract.md)
- [`tpm-rpm-minute-window-limiter.md`](./tpm-rpm-minute-window-limiter.md)
- [`weighted-shuffle-least-busy.md`](./weighted-shuffle-least-busy.md)
- [`write-behind-spend-batching.md`](./write-behind-spend-batching.md)
