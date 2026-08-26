<!-- capsule-v2 -->
# EditAggregator clustering FSM — how do keystroke-level edits become finalized before/after snapshots without capturing whitespace churn or runaway clusters?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** What are the exact cluster open/extend/finalize rules (time, line, count, duration, structural), and which edits are deliberately dropped?

## Per-file queue + cluster lifecycle
**Path/Symbol:** `core/nextEdit/context/aggregateEdits.ts:EditAggregator` (whole, 628L).
**Signature:** `processEdit(edit, timestamp?)`; `findSuitableCluster(fileState, editLine, timestamp): ClusterState | null`; `finalizeCluster(filePath, cluster, fileState)`; `getInProgressDiff(filePath): string | null`.
**Data Shape:** config defaults `{deltaT: 1.0s, deltaL: 5 lines, maxEdits: 500, maxDuration: 100s, contextSize: 5, contextLines: 3}`; per-file `FileState = {activeClusters[], currentContent, priorComparisons[], processingQueue[], isProcessing}`.

### Decisive source
```ts
// extend rule — same-line ALWAYS joins; otherwise time AND proximity
if ((isOnSameLine || (isWithinTimeWindow && isWithinLineRange)) &&
    isWithinEditLimit &&   // cluster.edits.length < maxEdits
    isWithinDurationLimit) // firstTimestamp age <= maxDuration
  return cluster;
// finalize triggers (identifyClustersToFinalize)
shouldFinalizeByLineNumber = movedLine && timeSinceLastEdit > deltaT;
shouldFinalizeByNewline    = edit.editText.includes("\n") && timeSinceLastEdit > deltaT * 1.5;
shouldFinalizeByCount      = cluster.edits.length >= maxEdits;
shouldFinalizeByDuration   = age > maxDuration;
shouldFinalizeByStructural = isStructuralEdit && (movedLine || newline);
```
```ts
// drop rules in finalizeCluster
const isWhitespaceOnlyDiff =
  beforeContent.replace(/\s+/g, "") === afterContent.replace(/\s+/g, "");
const changedLineCount = this.countChangedLines(diff);
if (changedLineCount > this.config.deltaL * 2) { /* silently drop cluster */ }
// batched drain with event-loop yield
while (fileState.processingQueue.length > 0) {
  const tasks = fileState.processingQueue.splice(0, 5);
  await Promise.all(tasks.map((task) => task()));
  await new Promise((resolve) => setTimeout(resolve, 0));
}
```
Backpressure twin: `processEdits` processes ONLY the last edit once the queue exceeds **50** entries ("Only process the last edit during rapid typing").

**Flow:** enqueue → drain 5-at-a-time with a macrotask yield between batches → finalize stale/oversized clusters → find or create a cluster (beforeState = `edit.fileContentsBefore ?? currentContent`) → extend its range by ±contextLines UNLESS the edit is whitespace-only → structural edits (newline or multi-line range) also finalize OVERLAPPING sibling clusters (`minLine ≤ other.maxLine + deltaL`) → on finalize: whitespace-only and >`deltaL×2` changed lines are DROPPED; survivors push into `priorComparisons` ring of `contextSize` and emit `onComparisonFinalized(beforeAfterDiff, firstBeforeCursor, lastAfterCursor)`.
**Invariant:** Whitespace-only edits don't EXTEND a cluster's range and whitespace-only diffs never FINALIZE into history; `countChangedLines` returns `max(added.size, removed.size)` from position-keyed sets so a rewrite of the same lines counts ONCE. File switch finalizes the previous file's clusters immediately. `getInProgressDiff` diffs the EARLIEST active cluster's beforeState against current content (null when equal or whitespace-only) so unfinalized typing still surfaces.
**Probe:** coverage caveat recorded honestly: no direct vitest suite for aggregateEdits.ts at this pin — behavior pinned by decisive source ranges above plus deterministic pins `grep -n 'splice(0, 5)\|> 50' core/nextEdit/context/aggregateEdits.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "EditAggregator finalizeCluster findSuitableCluster", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-trigger cluster lifecycle, whitespace filtering at BOTH extend and finalize time, the changed-lines cap tied to deltaL, and batched-with-yield draining; adapt thresholds (all configurable via getInstance partial-merge); omit the unused `priorComparisons` consumers if your model takes only the final diff.
