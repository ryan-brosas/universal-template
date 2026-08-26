<!-- capsule-v2 -->
# Iterative compaction state — how does the next compaction build on the previous one without reading the pruned history?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** After history is replaced by a summary, where do the inputs for the NEXT compaction come from?

## Persist the tail ON the compaction entry; reconstruct it virtually
**Path/Symbol:** `packages/agent/src/harness/compaction/compaction.ts:616-687` (`prepareCompaction`), result shape `:88-100` (`CompactResult`), file-op accumulation `:44-67` (`extractFileOperations`); entry type `packages/agent/src/harness/session/types.ts:44-51`.
**Signature:** `prepareCompaction(pathEntries, settings): Result<CompactionPreparation | undefined, CompactionError>`; `compact(preparation, …): Promise<Result<CompactResult, CompactionError>>` with `CompactResult = { summary, tokensBefore, usage?, retainedTail, details }`.
**Data Shape:** `CompactionEntry = { type:"compaction", summary, retainedTail: AgentMessage[], tokensBefore, details?: {readFiles, modifiedFiles} }`. Guard: no entries, or LAST entry already a compaction → `ok(undefined)` (nothing to do).

### Decisive source
```ts
if (prevCompactionIndex >= 0) {
	const prevCompaction = pathEntries[prevCompactionIndex] as CompactionEntry;
	previousSummary = prevCompaction.summary;
	const virtualRetainedEntries: Entry[] = prevCompaction.retainedTail.map((message, index) => ({
		type: "message",
		id: `${prevCompaction.id}:retained:${index}`,
		parentId: index === 0 ? prevCompaction.id : `${prevCompaction.id}:retained:${index - 1}`,
		seq: prevCompaction.seq,
		timestamp: message.timestamp,
		message,
	}));
	compactableEntries = [...virtualRetainedEntries, ...pathEntries.slice(prevCompactionIndex + 1)];
}
```
And the accumulation rule (`extractFileOperations`, :44-67): seed `fileOps` from the PREVIOUS compaction's `details.readFiles/modifiedFiles`, then add ops from the newly summarized messages — file history accumulates across successive compactions instead of resetting. Split-turn prefixes feed their ops in too (:671-675).

**Flow:** find last compaction → rebuild its retainedTail as virtual message ENTRIES (synthetic parent-chained ids) → prepend to everything after it → run cut-point logic over that virtual list → summarize history (feeding `<previous-summary>` into the UPDATE prompt) → new entry carries the NEW retainedTail + accumulated details.
**Invariant:** Future compactions reason over summary + virtual tail + post-compaction entries — never the pruned past. The retained tail rides ON the compaction entry (one durable unit), and file-operation ledgers are cumulative, so "which files did we touch?" survives any number of compactions.
**Probe:** `packages/agent/test/harness/compaction.test.ts:369/:385/:407` ("prepares compaction using the latest compaction summary as previousSummary" / "carries a previous compaction's retained tail into the next preparation" / "prepares split-turn compaction with prior file-operation details").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "prepareCompaction virtualRetainedEntries", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt persist-tail-on-entry + virtual reconstruction + accumulating file ledgers. Adapt detail fields to your tool surface. Omit nothing. Coverage caveat: none — all three behaviors directly pinned.
