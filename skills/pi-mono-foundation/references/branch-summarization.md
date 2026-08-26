<!-- capsule-v2 -->
# Branch summarization — how do I fold an abandoned conversation branch into one chronological summary entry without losing prior summaries or file context?

**Source:** pi-mono MIT `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** when the user switches from leaf A to an older sibling B, what exactly gets summarized and under which token budget?

## Tree-diff collection + newest-first budget packing
**Path/Symbol:** `packages/agent/src/harness/compaction/branch-summarization.ts` — `collectEntriesForBranchSummary` (82-111), `prepareBranchEntries` (132-171), `generateBranchSummary` (208-280); types `CollectEntriesResult` (54-59), `BranchSummaryDetails` (34-39).
**Signature:** `collectEntriesForBranchSummary(session, oldLeafId: string | null, targetId): Promise<CollectEntriesResult>`; `prepareBranchEntries(entries, tokenBudget = 0): BranchPreparation`; `generateBranchSummary(entries, options): Promise<Result<BranchSummaryResult, BranchSummaryError>>`.
**Data Shape:** `BranchPreparation = { messages: AgentMessage[], fileOps, totalTokens }`; `BranchSummaryResult = { summary, usage?, readFiles: string[], modifiedFiles: string[] }` — the file lists are persisted on the `branch_summary` entry as `details` and harvested back by later passes.

### Decisive source
```ts
// collect: diff old-leaf path vs target path through their common ancestor,
// then walk parents from the old leaf and reverse into chronological order:
const oldPath = new Set((await session.findEntriesOnBranch({ start: oldLeafId })).map((e) => e.id));
const targetPath = await session.findEntriesOnBranch({ start: targetId });
for (const entry of targetPath) {
	if (oldPath.has(entry.id)) { commonAncestorId = entry.id; break; }
}
// prepareBranchEntries: NEWEST-FIRST walk; boundary entries are admitted even over
// budget while the pack is still under 90% of the budget:
if (tokenBudget > 0 && totalTokens + tokens > tokenBudget) {
	if (entry.type === "compaction" || entry.type === "branch_summary") {
		if (totalTokens < tokenBudget * 0.9) {
			messages.unshift(message);
			totalTokens += tokens;
		}
	}
	break;
}
```

**Flow:** no previous leaf → empty result with `commonAncestorId: null` → collect computes both root paths, finds the deepest common ancestor, walks parent links from the abandoned leaf back to (excluding) that ancestor, reverses into chronological order → `prepareBranchEntries` first harvests readFiles/modifiedFiles from EVERY prior branch_summary entry's details, then packs messages newest-first under `tokenBudget = contextWindow − reserveTokens`, unshifting so the result is chronological → `generateBranchSummary` serializes the conversation inside `<conversation>` tags plus `BRANCH_SUMMARY_PROMPT` (custom instructions appended as "Additional focus:" unless `replaceInstructions`), calls `completeSimpleWithRetries` at `maxTokens: 2048`, prepends a preamble and appends the aggregated file-operations footer.
**Invariant:** entries already carrying a `compaction` or `branch_summary` marker are always admitted into the pack while usage stays below 90% of budget — prior summaries survive branch abandonment. Empty selection short-circuits to `ok({ summary: "No content to summarize", ... })`. Aborted/error stopReasons become typed `BranchSummaryError`s via `Result` — never thrown. The direct suite covers only the collector; the 90% boundary rule and prompt assembly are source-visible but have NO upstream direct test (recorded caveat).
**Probe:** `packages/agent/test/harness/branch-summarization.test.ts` "collects the abandoned side of a branch in chronological order" (:11-29 — asserts commonAncestorId and that root/common entries stay out), "returns no entries when there was no previous leaf" (:31-38). EXECUTED this pass: vitest run → passed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", name_pattern: "(collectEntriesForBranchSummary|prepareBranchEntries|generateBranchSummary)", file_pattern: "branch-summarization.ts" });
```

## Verdict
Adopt the common-ancestor tree diff and the newest-first pack with the 90% boundary-admission rule. Adapt the `<conversation>` wire format and preamble text to your summarizer. Omit pi's session-lane machinery (`Session.findEntriesOnBranch`, `createLane`) — any parent-chained store works. Porting trap: this module exists in TWO diverging copies — the agent copy takes `models/model` (auth owned by Models), while the coding-agent fork (`coding-agent/src/core/compaction/branch-summarization.ts`, generate at :293) takes `model/apiKey/headers/env/streamFn`. Production activation is `agent-session.ts:3056/:3122` behind the `session_before_tree` extension hook, invisible to static graph CALLS edges.
