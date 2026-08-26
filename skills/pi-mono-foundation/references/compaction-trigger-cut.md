<!-- capsule-v2 -->
# Compaction trigger & safe cut selection — when should context auto-compact, and how is a structurally safe cut point chosen?

**Source:** pi-mono MIT `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** what exact threshold fires auto-compaction, and which entries may a cut split on without orphaning tool calls or splitting turns?

## Threshold gate + backward-walk cut finder
**Path/Symbol:** `packages/agent/src/harness/compaction/compaction.ts` — `shouldCompact` (247-250), `estimateContextTokens` (216-244), `findValidCutPoints` (312-344), `findTurnStartIndex` (347-361), `findCutPoint` (374-422).
**Signature:** `shouldCompact(contextTokens: number, contextWindow: number, settings: CompactionSettings): boolean`; `findCutPoint(entries: Entry[], startIndex, endIndex, keepRecentTokens): CutPointResult` where `CutPointResult = { firstKeptEntryIndex, turnStartIndex, isSplitTurn }`.
**Data Shape:** `CompactionSettings = { enabled, reserveTokens, keepRecentTokens }`. Entries are a parent-chained session path; messages carry roles user/assistant/toolResult/bashExecution/custom/branchSummary/compactionSummary.

### Decisive source
```ts
export function shouldCompact(contextTokens: number, contextWindow: number, settings: CompactionSettings): boolean {
	if (!settings.enabled) return false;
	return contextTokens > contextWindow - settings.reserveTokens;
}
// findCutPoint: walk BACKWARD accumulating message tokens until keepRecentTokens,
// then snap FORWARD to the nearest valid cut point >= that index:
let accumulatedTokens = 0;
let cutIndex = cutPoints[0];
for (let i = endIndex - 1; i >= startIndex; i--) {
	const entry = entries[i];
	if (entry.type !== "message") continue;
	accumulatedTokens += estimateTokens(entry.message as AgentMessage);
	if (accumulatedTokens >= keepRecentTokens) {
		for (let c = 0; c < cutPoints.length; c++) {
			if (cutPoints[c] >= i) { cutIndex = cutPoints[c]; break; }
		}
		break;
	}
}
```

**Flow:** `estimateContextTokens` anchors on the LAST assistant usage (`calculateContextTokens(usage)` sums input+output+cacheRead+cacheWrite) and estimates only trailing post-usage messages via `ceil(chars/4)`; with no usage it falls back to pure per-message estimation → `shouldCompact` fires when usage crosses `contextWindow − reserveTokens` → `findValidCutPoints` admits message roles user/**assistant**/bashExecution/custom/branchSummary/compactionSummary and `type === "branch_summary"` entries; ONLY `toolResult` is excluded from message roles → backward token walk → forward snap → pull-back loop moves the cut earlier past non-message/non-compaction neighbors so the kept region starts right after a real boundary → if the cut lands on a user message the turn boundary is clean (`turnStartIndex = -1`); otherwise `findTurnStartIndex` walks back to the nearest branch_summary or user/bashExecution message to mark where the split turn began.
**Invariant:** a cut NEVER lands between a toolCall and its toolResult (toolResult is not a valid cut point), and never mid-turn without recording `turnStartIndex` for separate prefix summarization. Metadata-only ranges (thinking_level_change/model_change/active_tools_change) yield NO cut (`firstKeptEntryIndex = startIndex`). The caller-side stale-usage guard (`coding-agent/src/core/agent-session.ts:2133-2145`) refuses to re-fire when the last usage-bearing assistant message predates the just-created compaction entry — pre-compaction usage would otherwise falsely re-trigger forever.
**Probe:** `packages/agent/test/harness/compaction.test.ts` "checks compaction threshold" (:172-181), "covers cut-point and turn-start edge cases" (:201-243 — metadata-only no-cut, branch_summary turn start, toolResult-only no-cut, cut-after-compaction stays put). EXECUTED this pass: vitest run → 2 files / 24 tests passed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", name_pattern: "find(CutPoint|ValidCutPoints|TurnStartIndex)", file_pattern: "packages/agent/src/harness/compaction/compaction.ts" });
```

## Verdict
Adopt the threshold formula, the role-based valid-cut table, and the backward-walk→forward-snap algorithm verbatim; adopt the stale-usage guard whenever compaction can fire automatically more than once per session. Adapt `estimateTokens`' char heuristic (images = 4800 chars) to your tokenizer if you have one — the structure does not depend on it. Omit the coding-agent fork (`coding-agent/src/core/compaction/compaction.ts`, `shouldCompact` at :235) — porters must pick ONE copy and re-diff before porting either; the graph shows zero inbound CALLS edges for both copies because activation is dynamic wiring in AgentSession.
