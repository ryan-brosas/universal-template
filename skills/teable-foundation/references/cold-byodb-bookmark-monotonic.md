<!-- capsule-v2 -->
**Source:** teable `record-history-flusher.service.ts` advanceBookmark @ pin `06a4461e`
**Question:** When may the BYODB flush bookmark advance, and what keeps it monotonic?
**Path/Symbol:** `advanceBookmark(bindingId, cutoff)`, runFlush bookmark block
**Signature:** conditional updateMany: `WHERE id = bindingId AND (lastHistoryFlushedAt IS NULL OR lastHistoryFlushedAt < cutoff)` SET lastHistoryFlushedAt = cutoff — monotonic high-water mark; a manual wide-horizon run with an OLDER cutoff cannot regress it ("a regressed bookmark only costs an extra reconnect, but staying monotonic keeps 'everything at or before the bookmark is flushed' trivially true").
**Data Shape:** four conjunctive preconditions for advancing after a group: kind==='byodb' AND bindingId present AND !groupFailed AND deferredInGroup===0 AND deleteEnabled AND groupFullyDrained (every result has no deleteSkippedReason and [rows===0 OR deletedRows>0]).
**Decisive source:** :183-187 — "the bookmark asserts 'everything at or before the cutoff left the buffer', so it may only advance when this run actually deleted what it flushed: an upload-only run (delete or read gate off) or a deferred/failed/skipped table leaves rows behind, and advancing would let a then-idle space strand them forever."
**Flow/Invariant:** Bookmark semantics = completeness certificate, not activity marker. Monthly safety sweep (UTC day 1) passes ignoreBookmarks so a missed activity signal strands a space ≤ a month, not forever.
**Probe (direct test):** `grep -c 'lastHistoryFlushedAt: null }, { lastHistoryFlushedAt: { lt: cutoff } }' apps/nestjs-backend/src/features/record-history-cold/record-history-flusher.service.ts` → `1`; processor: `grep -c 'getUTCDate() === 1' apps/nestjs-backend/src/features/record-history-cold/record-history-cold.processor.ts` → `1`.
**Retrieve:** `echo '{"project":"teable","pattern":"advanceBookmark","limit":5}' | codebase-memory-mcp cli search_code`
**Verdict:** adopt — delete-gated monotonic bookmarks transfer to any buffer-drain design.
