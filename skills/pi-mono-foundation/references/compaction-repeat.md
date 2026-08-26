<!-- capsule-v2 -->
# Repeated-compaction pipeline — how does compaction stay correct the second time it runs on a history that already contains a compaction entry?

**Source:** pi-mono MIT `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** when a session compacts again, how are the previous summary and its retained tail reused without double-counting or losing messages?

## Virtual retained-tail re-chain + split-turn stitch
**Path/Symbol:** `packages/agent/src/harness/compaction/compaction.ts` — `prepareCompaction` (616-687), `compact` (707-794), `getMessageFromEntryForCompaction` (81-86), `completeSimpleWithRetries` (102-122), `CompactResult` interface (89-100).
**Signature:** `prepareCompaction(pathEntries: Entry[], settings): Result<CompactionPreparation | undefined, CompactionError>`; `compact(preparation, models, model, customInstructions?, signal?, thinkingLevel?, retry?, callbacks?): Promise<Result<CompactResult, CompactionError>>`.
**Data Shape:** `CompactionPreparation = { messagesToSummarize, turnPrefixMessages, retainedTail, isSplitTurn, tokensBefore, previousSummary?, fileOps, settings }`; `CompactResult<T> = { summary, tokensBefore, usage?, retainedTail: AgentMessage[], details?: T }`.

### Decisive source
```ts
if (pathEntries.length === 0 || pathEntries[pathEntries.length - 1].type === "compaction") {
	return ok(undefined);                      // nothing to compact / already compacted
}
// ...find prevCompactionIndex...
const virtualRetainedEntries: Entry[] = prevCompaction.retainedTail.map((message, index) => ({
	type: "message",
	id: `${prevCompaction.id}:retained:${index}`,
	parentId: index === 0 ? prevCompaction.id : `${prevCompaction.id}:retained:${index - 1}`,
	seq: prevCompaction.seq,
	timestamp: message.timestamp,
	message,
}));
compactableEntries = [...virtualRetainedEntries, ...pathEntries.slice(prevCompactionIndex + 1)];
// split-turn output stitch:
summary = `${historyText}\n\n---\n\n**Turn Context (split turn):**\n\n${turnPrefixResult.value.text}`;
```

**Flow:** skip entirely if empty or the last entry already IS a compaction → find the latest `compaction` entry; its `retainedTail` messages are re-materialized as VIRTUAL message entries with synthetic parent-chained ids (`<id>:retained:<i>`) prepended to everything after it, so the cut finder sees one continuous list → `findCutPoint` partitions that list into summarize-history / split-turn prefix / retained tail → `extractFileOperations` harvests read/edited files from summarized + prefix messages → `compact()` summarizes history (passing `previousSummary` so the model updates rather than restarts the summary), optionally adds a separate turn-prefix summary ("No prior history." when empty), appends a file-operations footer, and returns everything in a `Result` — never throws.
**Invariant:** the previous compaction's own summary message is excluded from the new compactable list (`getMessageFromEntryForCompaction` maps `type: "compaction"` to undefined) — its information flows through `previousSummary` + the virtual tail instead. Every summarization request is standalone: `completeSimpleWithRetries` forces `cacheRetention: "none"` and a fresh `sessionId: uuidv7()`, and clamps `maxTokens` to the model's output cap. Split-turn usage is combined field-wise via `combineUsage`. Test-pinned identity: `messagesToSummarize ++ turnPrefixMessages ++ retainedTail` equals `[...prevRetainedTail, ...newMessages]` — no message is lost or duplicated across repeated compactions.
**Probe:** `packages/agent/test/harness/compaction.test.ts` "carries a previous compaction's retained tail into the next preparation" (:385-405), "clamps compaction summary maxTokens to the model output cap" (:547-577 — asserts `cacheRetention ["none","none"]` + distinct sessionIds), "combines usage for split-turn compaction summaries" (:598-620). EXECUTED this pass: vitest run → passed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", name_pattern: "(prepareCompaction|completeSimpleWithRetries)", file_pattern: "packages/agent/src/harness/compaction/compaction.ts" });
```

## Verdict
Adopt the virtual-retained-tail re-chain (synthetic `${id}:retained:${i}` ids) as THE mechanism for iterative compaction, the never-throw `Result` envelope, and the no-cache/fresh-session discipline for summary calls. Adapt the split-turn stitch format and file-ops footer to your own summary vocabulary. Omit pi's CompactionEntry persistence details unless porting its session tree. Caveat: activation is dynamic — production wiring lives in `coding-agent/src/core/agent-session.ts` `_runAutoCompaction` (:2166+, with `session_before_compact` extension interception), not in any static CALLS edge.
