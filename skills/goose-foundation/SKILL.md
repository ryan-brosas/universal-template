---
name: goose-foundation
description: "Use when porting Block's goose AI-agent provider machinery — provider trait + collect_stream fold kernel, sanitized/migrating conversation model with audience projection, bounded think-tag stream filter, thinking-effort negotiation, declarative prompt-cache semantics, fail-safe NDJSON request logging, RFC 8628 device flows, typed provider error taxonomy with URL redaction, a retry/backoff ladder with transient-only gating, and the full formats/* payload-mapping layer (Anthropic request/SSE fold, OpenAI chat replay coherence + stream triage, dual-dialect Databricks dispatch, shared format SPI with tool-schema sanitization, Google thought-signature continuity + request mapping + thinking-config table + SSE fold, OpenAI Responses input-item mapper + typed-event stream fold, Ollama XML tool-call fallback with below-the-buffer timeout). Source code and direct tests are ground truth."
---

# goose: AI-Agent Provider Foundation

## Use this for
Use when building an LLM-provider adapter layer or agent-runtime core: shaping a minimal provider trait with defaulted capability surfaces, folding partial streams into whole messages without corrupting signed-thinking boundaries, loading untrusted persisted history safely, projecting content per audience, stripping inline reasoning tags from token streams under bounded memory, negotiating harness-advertised thinking effort, centralizing prompt-cache breakpoint policy, adding optional request logging that cannot fail inference, implementing OAuth device flows that tolerate server quirks, typing provider failures with secret-free diagnostics, and gating retries on transient classes. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/provider-retry.md` — capped exponential backoff with jitter, transient-only retry gating, permanent-failure substring markers, rate-limit `retry_delay` override, one-shot independent auth-refresh retry.
- `references/provider-errors.md` — typed provider error taxonomy with stable telemetry tags, reqwest/anyhow mapping that strips URL credentials/query secrets.
- `references/provider-base.md` — provider trait where only `stream()` is required, and the `collect_stream` fold kernel: equal-audience text merge, signature-gated single-block thinking merge, multi-block chunks as structured units, usage/empty-stream fallbacks.
- `references/message-model.md` — load-time migration+Unicode sanitization deserializer, assistant-only thinking audience rule, preserve-empty tool-response envelopes, same-audience text rejoining, metadata visibility/usage/operation notes.
- `references/think-stream-filter.md` — bounded (8 KiB) streaming <think>/<thinking> tag filter: chunk-boundary buffering, quoted-`>` attributes, self-closing no-ops, nesting depth, oversized-candidate release.
- `references/thinking-effort.md` — effort vocabulary with tolerant aliases and the Unspecified/Unsupported/Options support model with applied-vs-legacy handshake.
- `references/cache-semantics.md` — declarative (provider,model)→cache-regime table defaulting unknown pairs to safe strict-prefix mode, plus Anthropic-dialect breakpoint injection onto last-two-user/system/last-tool.
- `references/request-log.md` — one-shot global logger SPI where absence is a silent no-op and every call site stays total.
- `references/oauth-device-flow.md` — RFC 8628 polling with parse-before-status classification, +5s slow_down backoff, omitted-field fallbacks, keep-prior refresh-token rule.
- `references/anthropic-request-mapping.md` — Anthropic Messages serialization: provenance-gated signed thinking, placeholder tool_use pairing, null→object input coercion, media whitelist, thinking-config ladder with budget clamp.
- `references/anthropic-sse-stream.md` — Anthropic SSE fold: event grammar, field-presence cumulative usage merge, refusal flushes usage before erroring, truncated-tool-call and max-tokens tail guarantees.
- `references/openai-chat-replay.md` — reasoning_content propagation across split tool-call messages, same-turn remerge keyed on matching reasoning, ordered inline rewrite passes for strict endpoints.
- `references/openai-stream-triage.md` — choice-less SSE frame triage (prose ≠ error; status/detail = error), index-keyed tool-call drain immune to interleaved metadata, exactly-once output-limit marker.
- `references/databricks-dual-dialect.md` — one OpenAI-compatible builder serving Claude and reasoning models: reused stale-thinking gate, reasoning-summary shapes, deferred-image ordering, CacheSemantics-gated breakpoints.
- `references/format-spi-contract.md` — the seven-function format-module SPI plus tool-schema sanitizer (oneOf→anyOf, nullable normalization, name sanitation to 128 chars) and reserved-param filtering.
- `references/google-thought-signatures.md` — Gemini thought-signature continuity: active-loop window, single synthetic sentinel per model turn, cross-part signature inheritance.
- `references/google-request-mapping.md` — Messages→Gemini contents: user/model role collapse, nested-vs-sibling media flag, non-empty functionResponse guarantee, gemini-3 temperature ban.
- `references/google-thinking-config.md` — two-knob family split: ThinkingLevel ladder for gemini-3, budget table (default 8192) for 2.5, disable-expressibility per family.
- `references/google-sse-fold.md` — Gemini SSE fold: eof-buffered partial JSON, one stream-id across deltas, thoughtsTokenCount folded into output tokens.
- `references/responses-request-mapper.md` — Responses API input-item grammar (annotations-always output_text, text flushed before tool items) with effort-suffix and gpt-5.6 reasoning_mode gating.
- `references/responses-stream-fold.md` — Responses typed-event fold: unknown events ignored, deltas-now/structured-later dedup latch, truncated function-call filter, exactly-once limit marker.
- `references/ollama-xml-fallback.md` — XML `<function=>` tool-call fallback: JSON-first precedence, detect-once buffer-all streaming, timeout placed below the buffering wrapper.

## Capsule map
- **Retry/backoff ladder** — `provider-retry`: `RetryConfig` capped exponential backoff+jitter, transient-only `should_retry` gating, permanent-failure markers, rate-limit override, blanket `ProviderRetry` with one-shot auth refresh.
- **Provider error taxonomy** — `provider-errors`: typed `ProviderError` with `telemetry_type`, network classification, reqwest/anyhow cause-chain mapping, credential-free URL sanitization.
- **Provider trait + stream fold** — `provider-base`: required-method-minimal trait, MessageStream item contract, collect_stream coalescing rules and fallback ladder.
- **Sanitized message model** — `message-model`: migrating/sanitizing content deserializer, audience projection with thinking-assistant-only and empty-tool-response preservation, metadata visibility plane.
- **Think-tag stream filter** — `think-stream-filter`: ThinkFilter push/finish machine with bounded partial-tag buffering and five regression-tested edge rules.
- **Thinking-effort negotiation** — `thinking-effort`: effort parsing aliases, harness-advertised Options capability, set_thinking_effort boolean handshake, watch-channel subscription.
- **Prompt-cache semantics** — `cache-semantics`: four-regime enum, unknown→ImplicitStrict default, breakpoint placement (last two users + system + last tool).
- **Request logger SPI** — `request-log`: OnceLock one-shot install, NDJSON line schema, Option-handle no-op extension.
- **OAuth device flow** — `oauth-device-flow`: device-code request/poll/refresh with RFC tolerance rules and replaceable announce hook.
- **Anthropic request mapping** — `anthropic-request-mapping`: stale-thinking provenance gate, placeholder tool_use pairing, thinking-config ladder (adaptive/enabled/explicit-disabled) with ≥1024 answer-token budget clamp.
- **Anthropic SSE fold** — `anthropic-sse-stream`: content-block event grammar, cumulative field-presence usage merge, refusal-then-usage ordering, sorted truncated-tool-call tail.
- **OpenAI chat replay coherence** — `openai-chat-replay`: pending/turn reasoning carriers with boundary clears, matching-reasoning split remerge, post-merge inline rewrite.
- **OpenAI stream triage** — `openai-stream-triage`: metadata-vs-error frame classifier with 500-char cap, drain-until-finish tool accumulator, deduplicated length marker + synthetic usage guarantee.
- **Databricks dual dialect** — `databricks-dual-dialect`: family-branched payload keys over one wire dialect, reused staleness gate, deferred-image tool-role consecutiveness.
- **Format SPI contract** — `format-spi-contract`: seven-function module surface, schema sanitizer ladder, function-name sanitation, reserved/internal param filtering.
- **Google thought signatures** — `google-thought-signatures`: last-user-loop signature window, `skip_thought_signature_validator` sentinel on the first unsigned model tool call, cross-part inheritance.
- **Google request mapping** — `google-request-mapping`: contents serialization, media nesting by model family, tool-name resolution map, "Tool call is done." fallback, parametersJsonSchema tools.
- **Gemini thinking config** — `google-thinking-config`: level-vs-budget family table, disable clamps (Minimal / budget-0 / None), negative-budget warn-and-default.
- **Google SSE fold** — `google-sse-fold`: eof-buffered chunk parsing, shared stream id, thoughts-token output fold with input+output==total reconciliation.
- **Responses request mapper** — `responses-request-mapper`: input-item grammar, flush-before-tool ordering, effort suffix ladder, gpt-5.6 boundary-gated reasoning_mode, strict:false tools.
- **Responses stream fold** — `responses-stream-fold`: SSE field/type gates, delta/structured dedup latch, incomplete-response truncation filter and limit marker, fail-closed ID collision checks.
- **Ollama XML fallback** — `ollama-xml-fallback`: JSON-first XML recovery parser, monotonic detect-and-buffer streaming latch, raw-line timeout below the buffer.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question against project `goose`. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Candidate seams for future passes live in the goose-work record next-pass targets.

## Provenance
goose (Apache-2.0), `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory project `goose` (FULL, 118185 nodes / 316888 edges, ready, root/HEAD match; 10 parse-partial files, 0 skipped, 4 excluded dirs, 378 intentionally-excluded files).

## Full view (memory graph)
Revalidate `goose` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: fold/coalescing rules, sanitizing+migrating deserialization, audience projection, bounded tag filtering, effort vocabulary, cache-policy table, no-op-capable logger SPI, RFC tolerance rules, redacting error taxonomy, transient-gated retries. Adapt provider tables (cache regimes, permanent markers, effort aliases, device-flow headers/encoding) and the announce/logger backends to the host. Omit goose-specific plumbing you do not port: CanonicalModelRegistry filtering, ACP/session hooks, rmcp tool types, provider-specific variants (CreditsExhausted/Refusal/GoogleErrorCode), and CLI/browser announce details.