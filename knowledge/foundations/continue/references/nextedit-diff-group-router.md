<!-- capsule-v2 -->
# Full-file diff-group router — cursor group returned, others enqueued as prefetched outcomes

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** When a model rewrites the whole editable region, how is the rewrite split into per-location suggestions and routed between "show now" and "warm for later"?

## Key facts
**Path/Symbol:** `core/nextEdit/providers/BaseNextEditProvider.ts` — `handleFullFileDiff` (:101-159), `processDiffGroups` (:164-203), `addDiffGroupToPrefetchQueue` (:205-271), `createOutcomeFromDiffGroup` (:273-333), `createNextEditOutcome` field assembly (:335-379); helpers in `core/nextEdit/diff/diff.ts` — `groupDiffLines(diffLines, offset, maxGroupSize)` :287-316, `findChangedAreas` :321-343, `processLimitedSizeGroup` :365-416.
**Signature:** `handleFullFileDiff(params): Promise<NextEditOutcome | undefined>` — undefined means NO diff group contains the cursor (nothing shown; groups may still have been prefetched).
**Data Shape:** `DiffGroup = {startLine, endLine, lines: DiffLine[]}` where line numbers are OLD-CONTENT coordinates plus offset (the editable-region start); group content = non-"old" lines joined, original content = non-"new" lines joined.

### Decisive source
```ts
// :125-131 — myers → bounded groups (max 5 same/new lines) → whitespace-only deletions die
const diffLines = myersDiff(fileSlice, nextCompletion);
const diffGroups = groupDiffLines(diffLines, editableRegionStartLine, 5)
  .filter((group) => !isWhitespaceOnlyDeletion(group.lines));

// :186-199 — the ROUTE: exactly one group may contain the cursor;
// every other group becomes a fully-built outcome with its own uuid
for (const group of diffGroups) {
  if (currentLine >= group.startLine && currentLine <= group.endLine) cursorGroup = group;
  else await this.addDiffGroupToPrefetchQueue({ group, helper, startTime, llm,
                                                prefetchQueue, promptMetadata, ide });
}

// :262 — prefetched items get FRESH completion ids, not the request's id
completionId: uuidv4(), // Generate a new ID for this prefetched item.
```

**Flow:** completion replaces the editable-region slice (`fileLines.slice(start, end+1)`) → myers diff old→new → changed areas grouped with maxGroupSize=5 (limited mode counts "same"+"new" lines against the budget, never dedupes consecutive identical lines silently) → whitespace-only-deletion groups filtered → single pass routes each group: cursor-containing group flows through `createOutcomeFromDiffGroup` with `isCurrentCursorGroup=true` (cursor position preserved, final cursor recomputed via `calculateFinalCursorPosition`) while all others are materialized immediately and `enqueueProcessed` into PrefetchQueue with their RangeInFile location and fresh uuids.

**Invariant:** routing happens on INCLUSIVE start/end containment and the LAST matching group wins if ranges overlap (loop overwrites `cursorGroup`). Non-cursor groups are never dropped or lazily recomputed — they are FULLY built (LLM cost already paid) and queued. `calculateFinalCursorPosition` returns the CURRENT cursor unchanged when the new slice is empty (pure deletion ⇒ no cursor move). Outcome assembly spreads `...outcomeCtx.helper.options` LAST, so option fields can overwrite outcome fields of the same name — order-sensitive.

**Probe:** `grep -c 'addDiffGroupToPrefetchQueue' core/nextEdit/providers/BaseNextEditProvider.ts` → 2; `grep -c 'uuidv4(), // Generate a new ID' core/nextEdit/providers/BaseNextEditProvider.ts` → 1; `grep -c 'if (newEditRangeSlice === "")' core/nextEdit/diff/diff.ts` → 1; `grep -c 'isWhitespaceOnlyDeletion(group.lines)' core/nextEdit/providers/BaseNextEditProvider.ts` → 1.

**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "continue", query: "handleFullFileDiff processDiffGroups groupDiffLines prefetch", limit: 8 })`

## Verdict
Adopt diff-then-group-then-route: one immediate suggestion at the cursor, sibling hunks prebuilt into a warmed queue. Adapt group size budget and whitespace-deletion policy; keep fresh completion ids per prefetched item so telemetry stays per-suggestion.
