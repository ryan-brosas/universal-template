<!-- capsule-v2 -->
# Cache-sharing compact fork — how do you summarize a conversation while reusing the MAIN conversation's prompt cache, and why must the fork never set maxOutputTokens?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the exact contract for a cache-piggybacking forked summarizer with a streaming fallback?

## cache-sharing-compact-fork
**Path/Symbol:** `src/services/compact/compact.ts` (`streamCompactSummary` :1136-1396, `createCompactCanUseTool` :1125-1134, feature read :435-438).
**Signature:** `streamCompactSummary({messages, summaryRequest, appState, context, preCompactTokenCount, cacheSafeParams}): Promise<AssistantMessage>` — fork-first, streaming fallback.
**Data Shape:** flag `tengu_compact_cache_prefix` default TRUE for 3P (experiment: false-path = 98% cache miss ≈ 0.76% fleet cache_creation ≈ 38B tok/day; flag kept as kill-switch). Fork call: `{promptMessages:[summaryRequest], cacheSafeParams, canUseTool: deny-all, maxTurns:1, skipCacheWrite:true, overrides:{abortController}}`.

### Decisive source
```ts
// DO NOT set maxOutputTokens here. The fork piggybacks on the main thread's
// prompt cache by sending identical cache-key params (system, tools, model,
// messages prefix, thinking config). Setting maxOutputTokens would clamp
// budget_tokens via Math.min(budget, maxOutputTokens-1) in claude.ts,
// creating a thinking config mismatch that invalidates the cache.
// The streaming fallback path (below) can safely set maxOutputTokensOverride
// since it doesn't share cache with the main thread.
const result = await runForkedAgent({
  promptMessages: [summaryRequest],
  ...
  skipCacheWrite: true,
})
```
and the abort-classification guard:
```ts
// Guard isApiErrorMessage: query() catches API errors (including
// APIUserAbortError on ESC) and yields them as synthetic assistant
// messages. Without this check, an aborted compact "succeeds" with
// "Request was aborted." as the summary — the text doesn't start with
// "API Error" so the caller's startsWithApiErrorPrefix guard misses it.
if (assistantMsg && assistantText && !assistantMsg.isApiErrorMessage) {
```

**Flow:** if flag on → runForkedAgent reuses main thread's cached prefix (system+tools+model+message prefix identical) → success returns last assistant message; ANY failure (no text / throw) logs `tengu_compact_cache_sharing_fallback` and drops to the plain streaming path (own minimal system prompt "You are a helpful AI assistant tasked with summarizing conversations.", thinking disabled, tools = FileReadTool [+ToolSearchTool+MCP tools when tool search is on], optional 2-attempt retry behind a second flag).
**Invariant:** the fork's summary request rides the SAME cache key as the live conversation, so EVERY cache-key param must stay byte-identical — adding maxOutputTokens silently changes thinking-config math and voids the cache; `skipCacheWrite` keeps the fork from polluting the shared prefix. Synthetic-error classification needs the MESSAGE FLAG, not text prefix matching, because "Request was aborted." contains no "API Error" prefix. Compaction's agent denies ALL tool calls by contract ("compaction agent should only produce text summary") even though FileReadTool is declared in fallback mode.
**Probe:** no upstream test. Deterministic pins: `grep -n "DO NOT set maxOutputTokens" src/services/compact/compact.ts` → :1181; `grep -n "isApiErrorMessage" src/services/compact/compact.ts` → :1210; `grep -n "compaction agent should only produce text" src/services/compact/compact.ts` → :1131.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "runForkedAgent streamCompactSummary createCompactCanUseTool", limit: 10 });
```

## Verdict
Adopt fork-with-fallback and the identical-cache-key discipline. Adapt flag names/tool sets. Omit telemetry fields. Coverage caveat: no unit tests upstream.
