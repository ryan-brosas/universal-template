<!-- capsule-v2 -->
# Branch summarization — when the user abandons a branch and returns, what gets summarized?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter must summarize a session-tree jump without re-reading the shared trunk — exactly which entries belong to "the detour"?

## Summarize only old-leaf → deepest-common-ancestor, reversed
**Path/Symbol:** `packages/agent/src/harness/compaction/branch-summarization.ts:82-111` (`collectEntriesForBranchSummary`), budget `:132-171` (`prepareBranchEntries` w/ 90% rule), generation `:208-280` (`generateBranchSummary`).
**Signature:** `collectEntriesForBranchSummary(session, oldLeafId: string | null, targetId): Promise<{ entries, commonAncestorId }>`; `prepareBranchEntries(entries, tokenBudget = 0): BranchPreparation`.
**Data Shape:** No oldLeafId → empty summary. Entries walked via `parentId` from old leaf up to (excluding) the common ancestor, then REVERSED to chronological order.

### Decisive source
```ts
const oldPath = new Set((await session.findEntriesOnBranch({ start: oldLeafId })).map(e => e.id));
const targetPath = await session.findEntriesOnBranch({ start: targetId });
let commonAncestorId: string | null = null;
for (const entry of targetPath) {
	if (oldPath.has(entry.id)) { commonAncestorId = entry.id; break; }   // first hit walking target→root = DEEPEST ancestor
}
while (current && current !== commonAncestorId) {
	const entry = await session.getEntry(current);
	entries.push(entry);
	current = entry.parentId;
}
entries.reverse();
```
The budget rule (:149-168): select NEWEST-FIRST (walk backward, unshift); when the next message would overflow the budget, prior compaction/branch_summary entries still fit if total stays under 90% of budget — dense summaries earn their place over raw messages; then STOP.

**Flow:** compute both root paths → find deepest shared ancestor → collect exactly the abandoned side → budget-select newest-first with the summary-preference rule → serialize → generate with fixed `{ maxTokens: 2048 }` → prepend the preamble "The user explored a different conversation branch before returning here." → APPEND `<read-files>`/`<modified-files>` ledgers extracted from the branch.
**Invariant:** Only divergent history is summarized — nothing on the shared path to the common ancestor is paid for twice; nested prior summaries are preserved preferentially because they compress more information per token than raw messages. Empty branch → `"No content to summarize"`, not an error.
**Probe:** `packages/agent/test/harness/branch-summarization.test.ts:11/:31` ("collects the abandoned side of a branch in chronological order" / "returns no entries when there was no previous leaf").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "collectEntriesForBranchSummary prepareBranchEntries", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ancestor-delimited collection + newest-first selection + the 90% dense-summary preference. Adapt budget constants to your window math. Omit the replaceInstructions option if your host never swaps prompts. Coverage caveat: generation-side error paths are typed-error tested only at unit level.
