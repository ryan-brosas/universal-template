<!-- capsule-v2 -->
# Partial-compact direction algebra — when the user picks a pivot message, why does "summarize after" keep stale boundaries while "summarize before" must strip them, and how do preserved messages relink?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you implement pivot-based partial compaction with correct boundary/summary filtering and chain re-linking?

## partial-compact-directions
**Path/Symbol:** `src/services/compact/compact.ts` (`partialCompactConversation` :772-1106; direction filter :781-800; anchor :1077-1087) + `annotateBoundaryWithPreservedSegment` :349-367.
**Signature:** `partialCompactConversation(allMessages, pivotIndex, context, cacheSafeParams, userFeedback?, direction: 'from'|'up_to' = 'from'): Promise<CompactionResult>`.
**Data Shape:** 'from' = summarize `slice(pivotIndex)`, keep earlier (prefix-preserving → kept cache stays valid); 'up_to' = summarize `slice(0,pivotIndex)`, keep later (summary precedes kept → cache invalidated). Boundary gains `compactMetadata.preservedSegment = {headUuid: keep[0], anchorUuid, tailUuid: keep.at(-1)}`.

### Decisive source
```ts
// 'up_to' must strip old compact boundaries/summaries: for 'up_to',
// summary_B sits BEFORE kept, so a stale boundary_A in kept wins
// findLastCompactBoundaryIndex's backward scan and drops summary_B.
// 'from' keeps them: summary_B sits AFTER kept (backward scan still
// works), and removing an old summary would lose its covered history.
const messagesToKeep =
  direction === 'up_to'
    ? allMessages
        .slice(pivotIndex)
        .filter(
          m =>
            m.type !== 'progress' &&
            !isCompactBoundaryMessage(m) &&
            !(m.type === 'user' && m.isCompactSummary),
        )
    : allMessages.slice(0, pivotIndex).filter(m => m.type !== 'progress')
```
and:
```ts
// 'from': prefix-preserving → boundary; 'up_to': suffix → last summary
const anchorUuid =
  direction === 'up_to'
    ? (summaryMessages.at(-1)?.uuid ?? boundaryMarker.uuid)
    : boundaryMarker.uuid
```

**Flow:** API-side asymmetry too — 'up_to' sends ONLY the summarized prefix (it hits cache directly); 'from' sends ALL messages because its tail wouldn't cache. Kept messages keep original parentUuids on disk (loader dedup-skips them); the annotated boundary tells the loader to patch head→anchor and the anchor's other children→tail. Discovered-tools union scans allMessages in both directions ("set union is idempotent, simpler than tracking which half each tool lived in"). Progress messages are excluded from both halves AND from lastPreCompactUuid because forkSessionImpl nulls a logicalParentUuid pointing at one.
**Invariant:** boundary-filtering polarity follows the backward-scan semantics of `findLastCompactBoundaryIndex`: whichever half contains an OLD boundary before a NEW summary breaks the scan. The summary message's shape is conditional: with keeps it carries `summarizeMetadata` (count/userContext/direction); without keeps it is transcript-only-visible.
**Probe:** no upstream test. Deterministic pins: `grep -n "must strip old compact boundaries" src/services/compact/compact.ts` → :785; `grep -n "preservedSegment" src/services/compact/compact.ts` → :360/:364; `grep -n "summarizeMetadata:" src/services/compact/compact.ts` → :1037.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "partialCompactConversation annotateBoundaryWithPreservedSegment", limit: 10 });
```

## Verdict
Adopt both directions' filter/cache/anchor rules and the boundary relink annotation. Adapt message-type names. Omit telemetry. Coverage caveat: no unit tests upstream.
