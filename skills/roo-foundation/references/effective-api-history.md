<!-- capsule-v2 -->
# Effective-history projection — what does the model actually see after condense/truncate tags exist?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Given a stored history full of condenseParent/truncationParent tags, which messages go into the next API call — including after a rewind deleted their summary/marker?

## getEffectiveApiHistory: existence-keyed filtering, orphan-tolerant
**Path/Symbol:** `src/core/condense/index.ts:539-633` (`getEffectiveApiHistory`); consumption `src/core/task/Task.ts:4083-4089`.
**Signature:** `getEffectiveApiHistory(messages: ApiMessage[]): ApiMessage[]`.
**Data Shape:** Two registries rebuilt on EVERY call: `existingSummaryIds` (from `msg.isSummary && msg.condenseId`) and `existingTruncationIds` (from `msg.isTruncationMarker && msg.truncationId`).

### Decisive source
```ts
return messages.filter((msg) => {
  if (msg.condenseParent && existingSummaryIds.has(msg.condenseParent)) return false
  if (msg.truncationParent && existingTruncationIds.has(msg.truncationParent)) return false
  return true   // ORPHANED parents ⇒ message is ACTIVE again
})
```
With a live summary present, the fresh-start branch returns only `slice(summaryIndex)` and additionally drops orphan `tool_result` blocks whose `tool_use_id` was condensed away (rebuilding the visible `toolUseIds` set first), removing user messages left with empty content entirely.

**Flow:** most-recent summary wins (findLast) → slice from it → prune dangling tool_results → drop messages whose truncationParent marker still exists in the sliced range. No-summary branch applies the same two-parent filter globally, which is exactly what makes rewind work: delete the summary/marker and its children instantly re-enter the API view.
**Invariant:** Visibility is computed from ID EXISTENCE, never from order heuristics or deletion lists — filtering and cleanupAfterTruncation must agree on the same registry construction or rewind resurrects wrong messages.
**Probe:** `src/core/context-management/__tests__/truncation.spec.ts` ("include truncated messages when truncation marker is removed" :118, combined-parents :134); `src/core/condense/__tests__/rewind-after-condense.spec.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "getEffectiveApiHistory condenseParent truncationParent filter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt existence-keyed projection with orphan-tolerance — it is the mechanism that makes non-destructive condense AND truncate reversible. Adapt field names to your message schema. Nothing to omit beyond provider image handling upstream of this layer.
