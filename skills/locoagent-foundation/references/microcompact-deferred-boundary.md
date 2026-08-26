<!-- capsule-v2 -->
# Deferred microcompact boundary — why is a compaction message withheld until AFTER the next API response?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you report exact deleted-token counts when the authoritative number only exists in the NEXT response's usage payload?

## pendingCacheEdits handoff
**Path/Symbol:** `src/query.ts` capture (:420-426), settlement after streaming (:866-892); producer `deps.microcompact()` (`src/services/compact/microCompact.ts` via `src/query/deps.ts`).
**Signature:** `microcompactResult.compactionInfo?.pendingCacheEdits: { trigger; baselineCacheDeletedTokens; deletedToolIds } | undefined`.
**Data Shape:** the API usage field `cache_deleted_input_tokens` is cumulative/sticky across requests, so the delta must be computed against a pre-request baseline.

### Decisive source
```ts
// For cached microcompact (cache editing), defer boundary message until after
// the API response so we can use actual cache_deleted_input_tokens.
const pendingCacheEdits = feature('CACHED_MICROCOMPACT')
  ? microcompactResult.compactionInfo?.pendingCacheEdits : undefined
// ...after streaming:
const cumulativeDeleted = usage ? (usage.cache_deleted_input_tokens ?? 0) : 0
const deletedTokens = Math.max(0, cumulativeDeleted - pendingCacheEdits.baselineCacheDeletedTokens)
if (deletedTokens > 0) {
  yield createMicrocompactBoundaryMessage(pendingCacheEdits.trigger, 0, deletedTokens, pendingCacheEdits.deletedToolIds, [])
}
```

**Flow:** microcompact runs pre-request and returns edits + baseline instead of yielding a boundary → the whole block is gated behind `feature('CACHED_MICROCOMPACT')` so the string is eliminated from external builds → post-stream, read the LAST assistant message's usage, subtract the baseline, yield the boundary message only when delta > 0.
**Invariant:** (1) never report client-side token ESTIMATES when the API will report the real deletion count next round-trip; (2) the sticky-cumulative field requires a captured baseline — computing from zero double-counts earlier compactions; (3) `Math.max(0, …)` guards against counter quirks where the cumulative value didn't move.
**Probe:** coverage caveat (no upstream tests). Deterministic probes: `grep -n "pendingCacheEdits\|baselineCacheDeletedTokens\|cache_deleted_input_tokens" src/query.ts src/services/compact/microCompact.ts`; `sed -n '866,892p' src/query.ts` pins the settlement block verbatim.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createMicrocompactBoundaryMessage cache deleted tokens", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt defer-until-authoritative-data-exists for any usage-derived reporting; adapt field names to your provider's usage schema; omit if your microcompaction reports synchronously. Porting trap: emitting the boundary at microcompact time bakes an estimate into the transcript that later contradicts the API-reported number.
