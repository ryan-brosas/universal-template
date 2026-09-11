<!-- capsule-v2 -->
# Microcompact producers — when do old tool results get cleared without breaking the cache?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What triggers client-side microcompaction, what does each strategy mutate, and which cross-state resets keep cached-MC honest?

## microcompactMessages + evaluateTimeBasedTrigger + autoCompactIfNeeded
**Path/Symbol:** `src/services/compact/microCompact.ts` — `microcompactMessages` (:253-293), `evaluateTimeBasedTrigger` (:422-444), `maybeTimeBasedMicrocompact` (:446-530), `cachedMicrocompactPath` (:305-399), `TIME_BASED_MC_CLEARED_MESSAGE` (:36), COMPACTABLE_TOOLS (:41-50), pending/pinned cache-edit state (:56-135); `src/services/compact/autoCompact.ts` — thresholds (:28-70), `getAutoCompactThreshold` (:72-91), `calculateTokenWarningState` (:93-145), `shouldAutoCompact` (:160-239), `autoCompactIfNeeded` (:241-351).
**Signature:** `microcompactMessages(messages, toolUseContext?, querySource?) → {messages, compactionInfo?{pendingCacheEdits}}`; `autoCompactIfNeeded(...) → {wasCompacted, compactionResult?, consecutiveFailures?}`.
**Data Shape:** Time-based MC mutates tool_result content IN PLACE to `'[Old tool result content cleared]'`; cached MC leaves messages untouched and queues `{trigger:'auto', deletedToolIds, baselineCacheDeletedTokens}` for API-layer cache_edits.

### Decisive source
```ts
// :261-266 time-based runs FIRST and short-circuits cold-cache logic
// If the gap since the last assistant message exceeds the threshold, the server
// cache has expired and the full prefix will be rewritten regardless — so content-
// clear old tool results now ... Cached MC is skipped when this fires: editing
// assumes a warm cache, and we just established it's cold.
// :461-463 keep-floor
// Floor at 1: slice(-0) returns the full array (paradoxically keeps everything),
// and clearing ALL results leaves the model with zero working context.
const keepRecent = Math.max(1, config.keepRecent)
// :512-517 stale-state reset after content-clear
// If cached-MC runs next turn with the stale state, it would try to cache_edit
// tools whose server-side entries no longer exist. Reset it.
resetMicrocompactState()
```

**Flow:** microcompactMessages order: clearCompactWarningSuppression → time-based trigger (enabled ∧ explicit main-thread querySource ∧ gap ≥ threshold; analysis-only callers passing undefined NEVER trigger) clears all-but-last-N compactable results, suppresses warning, RESETS cached-MC state, notifies cache-break detector (expecting a self-inflicted read drop) → else cached MC (feature-gated, main-thread-only via prefix-matching querySource — bare `=== 'repl_main_thread'` silently excluded custom output styles) registers tool_results grouped by message, picks deletions by count-based config, queues edits + baseline capture (deferred-boundary contract lives in microcompact-deferred-boundary.md) → else no-op (autocompact owns pressure) ‖ autocompact: recursion guards (querySource session_memory/compact forked agents would deadlock; marble_origami ctx-agent shares module-level collapse state) → reactive-only & context-collapse suppression gates → tokenCountWithEstimation minus snipTokensFreed vs threshold (effective window − maxOutputTokens capped at 20k summary reserve − 13k buffer; env % override takes MIN) → trySessionMemoryCompaction EXPERIMENT first (resets lastSummarizedMessageId + postCompactCleanup + notifyCompaction — SM-compact misses compactConversation's internal baseline reset, caused 20% false-positive cache breaks) → compactConversation fallback → failure ladder increments consecutiveFailures (MAX 3 circuit breaker — BQ: sessions burned ~250K doomed calls/day before it) resetting on success; user-abort errors not logged as failures.

**Invariant:** (1) Strategy EXCLUSIVITY follows cache temperature: warm cache ⇒ cache_edits only; cold cache ⇒ content-clear only; running both corrupts server-side delete targets. (2) Cached-MC registration is main-thread-scoped or forks register tools that don't exist in the main conversation. (3) keep floor of 1 guards both the slice(-0) JS quirk and zero-context degenerate. (4) Autocompact ordering: SM-compaction > legacy compaction, each with its own cleanup/baseline obligations; skipping notifyCompaction after SM-compact poisons break detection. (5) Circuit breaker counts CONSECUTIVE failures threaded by the caller (autoCompactTracking) — stateless retries hammer irrecoverably-over-limit contexts.

**Probe:** coverage caveat — no upstream tests. Deterministic pins: `grep -n "paradoxically keeps" src/services/compact/microCompact.ts` (:458); `grep -n "no longer exist. Reset it." src/services/compact/microCompact.ts` (:516); `grep -n "250K API calls/day" src/services/compact/autoCompact.ts` (:69); `grep -n "20% of tengu_prompt_cache_break" src/services/compact/autoCompact.ts` (:300); graph resolves microcompactMessages/evaluateTimeBasedTrigger/autoCompactIfNeeded/shouldAutoCompact line-exact under `src.services.compact`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "microcompactMessages evaluateTimeBasedTrigger autoCompactIfNeeded consecutiveFailures", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the warm/cold strategy split, main-thread scoping, keep-floor, stale-state reset after content-clears, and the 3-strike compaction circuit breaker; adapt thresholds/token estimators to host models; omit GrowthBook feature gates and ant-only context-collapse interplay. Porting trap: reusing cached-MC delete lists after a content-clear sends cache_edit deletions for KV entries that no longer exist; forgetting SM-compact's baseline reset flags every subsequent response as a cache break.
