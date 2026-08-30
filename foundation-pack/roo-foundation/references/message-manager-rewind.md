<!-- capsule-v2 -->
# Rewind reconciliation — when the user deletes/edits/restores a message, how do BOTH histories stay consistent?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Roo keeps a UI log (clineMessages) and an API log (apiConversationHistory) — what is the single choke point that rewinds both without orphaning summaries/markers/artifacts?

## MessageManager.rewindToTimestamp: collect IDs → cut UI log → reconcile API log in ONE write
**Path/Symbol:** `src/core/message-manager/index.ts:48-246` (`rewindToTimestamp` → `performRewind` → `truncateApiHistoryWithCleanup`); artifact sweep :252-270.
**Signature:** `rewindToTimestamp(ts: number, { includeTargetMessage? = false, skipCleanup? = false }): Promise<void>` (throws if ts not found); `rewindToIndex(toIndex)` variant.
**Data Shape:** Context-event IDs harvested from the REMOVED tail: `say === "condense_context"` → `contextCondense.condenseId`; `say === "sliding_window_truncation"` → `contextTruncation.truncationId`.

### Decisive source
```ts
// timestamp race: a user_feedback clineMessage can carry a ts BEFORE the assistant
// API message that triggered it (tool exec runs concurrent with stream completion),
// so snap the boundary to the first API USER message at-or-after cutoff:
if (!hasExactMatch && hasMessageBeforeCutoff) {
  const i = apiHistory.findIndex(m => m.ts !== undefined && m.ts >= cutoffTs && m.role === "user")
  if (i !== -1) actualCutoff = apiHistory[i].ts!
}
apiHistory = apiHistory.filter(m => !m.ts || m.ts < actualCutoff)
// then: drop Summary rows whose condenseId was removed, drop markers whose
// truncationId was removed, run cleanupAfterTruncation (unless skipCleanup),
// fire-and-forget OutputInterceptor.cleanupByIds(validTsStrings)
```
Write gate: persists ONLY if length changed or any slot differs by reference (`historyChanged`) — avoids pointless disk churn.

**Flow:** find index by exact `m.ts` match → cutoff (+1 if includeTargetMessage, i.e. edit vs delete) → collect context-event ids from the doomed tail → overwrite clineMessages with prefix → single filtered rewrite of api history (cutoff + orphan summary/marker removal + tag cleanup) → async artifact GC keyed on surviving timestamps.
**Invariant:** The API-log boundary snaps to a USER message because assistant messages may legally precede their own user_feedback twin in wall-clock ts; cutting at the naive cutoff would strand the triggering assistant turn. skipCleanup exists for callers that will clean up themselves (checkpoint flows).
**Probe:** `src/core/message-manager/index.spec.ts` — Summary removed iff condense_context removed (:166), checkpoint restore before/after condense (:431/:473) and truncation (:515/:551), skipCleanup matrix (:588-639).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "MessageManager rewindToTimestamp truncateApiHistoryWithCleanup", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-entry-point rewind manager with id-collection BEFORE mutation and user-message-snapped cutoffs. Adapt event kinds (condense/truncation) to your own context-event vocabulary. Omit the VS Code artifact directory layout.
