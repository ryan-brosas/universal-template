<!-- capsule-v2 -->
# API streaming producer — how does one request become stream events, fallbacks, and final usage?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How are requests assembled (betas/cache markers/thinking), streamed via raw SDK events, recovered into non-streaming mode, and finalized without leaking native resources?

## queryModel + addCacheBreakpoints + updateUsage
**Path/Symbol:** `src/services/api/claude.ts` — `queryModel` (:1017-2892), `paramsFromContext` (:1538-1729), streaming loop (:1931-2403), fallback paths (:2404-2594 mid-stream, :2607-2749 404-at-creation), finally/cost (:2808-2831), `cleanupStream` (:2898-2912), `updateUsage` (:2924-2987), `addCacheBreakpoints` (:3063-3211), `buildSystemPromptBlocks` (:3213-3237), `adjustParamsForNonStreaming` (:3364-3392), `stripExcessMediaItems` (:956-1015), `executeNonStreamingRequest` (:818-917); `withStreamingVCR` wraps both public entries (:709-780).
**Signature:** `queryModelWithStreaming(...): AsyncGenerator<StreamEvent | AssistantMessage | SystemAPIErrorMessage, void>`; AssistantMessages yield at EACH content_block_stop (streaming = incremental message emission, not one blob).
**Data Shape:** contentBlocks indexed-by-part-index accumulate deltas (tool_use input as STRING partial_json — raw Stream avoids BetaMessageStream's O(n²) partialParse); usage fields are CUMULATIVE per event with null/0 meaning "keep previous".

### Decisive source
```ts
// :3089 single-marker rule (+ skipCacheWrite shift)
// Exactly one message-level cache_control marker per request. Mycro's
// turn-to-turn eviction frees local-attention KV pages at any cached prefix
// position NOT in cache_store_int_token_boundaries. With two markers the
// second-to-last position is protected ... For fire-and-forget forks we shift
// the marker to the second-to-last message ...
const markerIndex = skipCacheWrite ? messages.length - 2 : messages.length - 1
// :1528-1532 consume-once outside paramsFromContext
// paramsFromContext is called multiple times (logging, retries), so consuming
// inside it would cause the first call to steal edits from subsequent calls.
const consumedCacheEdits = cachedMCEnabled ? consumePendingCacheEdits() : null
// :2464-2468 mid-stream fallback double-execution hazard
// The mid-stream fallback causes double tool execution when streaming tool
// execution is active: the partial stream starts a tool, then the
// non-streaming retry produces the same tool_use and runs it again. See inc-4258.
```

**Flow:** off-switch check (cheap-first ordering: subscriber/non-Opus skip the blocking await) → betas assembled once (advisor header always-on for history parsing; tool-search header provider-split 1P vs Bedrock extraBody) → deferred-tool filtering (only DISCOVERED tools sent; ToolSearch always kept; pending MCP servers keep discovery alive) → model-aware strip of tool-search fields on mid-conversation switches → ensureToolResultPairing repairs resume-session orphan pairs → media cap strips OLDEST items silently (>100 rejected server-side with confusing error) → fingerprint computed BEFORE synthetic deferred-tools prepend → system prompt blocks with attribution header + optional advisor/chrome appends → sticky header latches (afk/fast/cacheEditing/thinkingClear latch ONCE per session so mid-session toggles can't bust 50-70K-token caches; cleared on /clear + /compact) → recordPromptState captures the exact latched send-state for break detection → withRetry loop: per-attempt paramsFromContext (retry-context maxTokensOverride precedence), client_request_id header (first-party only), .withResponse() captures request_id + Response → idle watchdog (90s default, env-tunable; setTimeout kills silently-dropped streams the SDK fetch-timeout doesn't cover) + 30s stall accounting (skips TTFB) → event switch: message_start seeds usage/ttft; content_block_start zeroes mutable fields (SDK duplicates first text/thinking chunks; mutates block objects in place — hence spread-copy); deltas append with type-mismatch telemetry throws; content_block_stop normalizes + YIELDS the message immediately; message_delta writes final usage/stop_reason back into the LAST yielded message via DIRECT MUTATION (transcript write-queue holds the inner reference; object replacement disconnects it) + refusal + max_tokens/model_context_window_exceeded error messages → completion checks: watchdog abort ⇒ non-streaming fallback; no-message_start or (no blocks AND no stop_reason — structured-output turn-2 end_turn is legitimate) ⇒ fallback → catch: APIUserAbortError disambiguated signal-vs-SDK-timeout; disableFallback flag (inc-4258 double-tool-execution) propagates instead; 404-at-creation handled OUTER (raw streams throw there, not during iteration; failed ID pulled from error header since streamRequestId unassigned) → FallbackTriggeredError ALWAYS rethrown (swallowing turns model-fallback into a no-op) → finally: releaseStreamResources cancels stream controller AND Response.body (native TLS/socket buffers live outside V8 heap — GH #32920 leak) + fallback cost tracked here to survive consumer .return().

**Invariant:** (1) Cache-marker count/position IS a contract: exactly one, tail-position, shifted left for fire-and-forget forks (KV-page eviction economics documented against Mycro internals). (2) cache_reference tags go on tool_result blocks strictly BEFORE the marker message, created as NEW objects (mutation contaminates secondary queries on cache-edit-less models); insertion AFTER cache_edits splicing since indices shift. (3) updateUsage treats null-and-zero identically ("keep prior") except output_tokens which accepts 0 — cumulative-vs-delta confusion double-counts. (4) Non-streaming caps: MAX_NON_STREAMING_TOKENS 64k with thinking-budget clamp to cap−1 (max_tokens > budget_tokens invariant); remote sessions shorten timeout to 120s to die under container idle-kill (~5min). (5) Retry taxonomy lives in `withRetry.ts`: DEFAULT_MAX_RETRIES 10; 529 counted only toward Opus-fallback (3 strikes → FallbackTriggeredError); background sources (summaries/classifiers) DROP 529s immediately (gateway-amplification rationale); fast-mode short-retry-after <20s preserves speed, longer enters ≥10min cooldown; persistent unattended mode clamps the loop counter and heartbeats 30s chunks; stale ECONNRESET/EPIPE disables keep-alive; OAuth/Bedrock/Vertex auth errors rebuild client + refresh; x-should-retry honored except ant-5xx; retry-after overrides backoff; jittered exp backoff 500ms·2^n capped 32s.

**Probe:** coverage caveat — no upstream tests for claude.ts/withRetry.ts. Deterministic pins: `grep -n "Exactly one message-level cache_control" src/services/api/claude.ts` (:3078); `grep -n "steal edits from subsequent" src/services/api/claude.ts` (:1530); `grep -n "double tool" src/services/api/claude.ts` (:2465); `grep -n "GH #32920" src/services/api/claude.ts` (:2814); `grep -n "gateway" src/services/api/withRetry.ts` (:59); graph resolves queryModelWithStreaming/executeNonStreamingRequest/addCacheBreakpoints/updateUsage + `src.services.api.withRetry.withRetry` line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "queryModelWithStreaming addCacheBreakpoints updateUsage nonstreaming fallback", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt raw-stream accumulation with incremental yields, direct-mutation writeback, consume-once cache-edits, sticky beta-header latches, the single-marker rule, and resource-release-in-finally; adapt beta/provider vocabularies and retry source lists; omit VCR recording, ant telemetry, and quota-header parsing. Porting trap: replacing direct mutation of the yielded message with object replacement loses final usage/stop_reason in the transcript; consuming pending cache edits inside a multi-called params builder silently drops edits from retried requests.
