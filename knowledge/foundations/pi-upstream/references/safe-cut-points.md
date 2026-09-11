<!-- capsule-v2 -->
# Safe cut points — where may compaction cut history without orphaning tool results or splitting turns?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter must choose the first retained entry after summarization — which entries are legal cuts?

## Cut between turns, never between a call and its result
**Path/Symbol:** `packages/agent/src/harness/compaction/compaction.ts:312-344` (`findValidCutPoints`), `:374-422` (`findCutPoint`), `:347-361` (`findTurnStartIndex`).
**Signature:** `findCutPoint(entries, startIndex, endIndex, keepRecentTokens): { firstKeptEntryIndex, turnStartIndex, isSplitTurn }`.
**Data Shape:** Valid cut = message entries whose role ≠ `toolResult` (user / assistant / bashExecution / custom / branchSummary / compactionSummary), plus `branch_summary` ENTRIES. Metadata entries (`thinking_level_change`, `model_change`, `active_tools_change`) and prior `compaction` entries are NEVER cut points.

### Decisive source
```ts
// walk backward accumulating estimated tokens until >= keepRecentTokens,
// then pick the FIRST cut point at-or-after that index
for (let i = endIndex - 1; i >= startIndex; i--) {
	if (entry.type !== "message") continue;
	accumulatedTokens += estimateTokens(entry.message);
	if (accumulatedTokens >= keepRecentTokens) {
		for (const c of cutPoints) if (c >= i) { cutIndex = c; break; }
		break;
	}
}
// back up over non-message/non-compaction neighbors
while (cutIndex > startIndex) {
	const prev = entries[cutIndex - 1];
	if (prev.type === "compaction" || prev.type === "message") break;
	cutIndex--;
}
const isUserMessage = ...;
const turnStartIndex = isUserMessage ? -1 : findTurnStartIndex(entries, cutIndex, startIndex);
```

**Flow:** budget satisfied at index i → first valid cut ≥ i → backup sweep → if the cut entry is not a user/bashExecution turn-opener, walk back to the turn start and mark `isSplitTurn`. A split turn is NOT forbidden: its prefix is summarized separately (turn-prefix capsule) while the kept tail still begins at a turn boundary.
**Invariant:** A cut must never separate a toolCall from its toolResult (that orphans the pair against provider APIs) and must never leave the retained tail starting mid-turn without special handling. Cutting AT a metadata entry would drop state changes (model/thinking/tools) from context silently.
**Probe:** `packages/agent/test/harness/compaction.test.ts:183/:201` ("finds a cut point based on token differences" / "covers cut-point and turn-start edge cases").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "findValidCutPoints findTurnStartIndex", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the role-based cut legality table + backward token accumulation + split-turn detection. Adapt role names to your schema. Omit nothing. Coverage caveat: none.
