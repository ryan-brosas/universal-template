<!-- capsule-v2 -->
# Session context assembly — how do durable entries become the message list the model sees?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter stores summaries as entries — how are they rehydrated into LLM messages without double-counting pruned history?

## Last-compaction-wins, then project each entry type
**Path/Symbol:** `packages/agent/src/harness/session/context.ts:45-57` (`defaultContextEntryTransform`), `:65-88` (`sessionEntryToContextMessages`), `:25-43` (`deriveSessionContextState`), entry point `:90-100` (`buildSessionContext`).
**Signature:** `buildSessionContext(pathEntries: readonly Entry[], options?): { messages: AgentMessage[]; thinkingLevel: string; model; activeToolNames }`.
**Data Shape:** Entry types projected to zero-or-more AgentMessages: `message` → itself (EXCEPT assistant with `stopReason === "deferred"` → dropped); `compaction` → `[compactionSummaryMessage, ...entry.retainedTail]`; `branch_summary` → its synthetic message when summary non-empty; `custom` → whatever a registered projector returns (default none); metadata entries (`model_change`, `thinking_level_change`, `active_tools_change`) → no messages but DO update state.

### Decisive source
```ts
export function defaultContextEntryTransform(pathEntries) {
	let compaction, compactionIndex = -1;
	for (let index = pathEntries.length - 1; index >= 0; index--) {
		if (pathEntries[index].type === "compaction") { compaction = pathEntries[index]; compactionIndex = index; break; }
	}
	return compaction === undefined ? [...pathEntries] : [compaction, ...pathEntries.slice(compactionIndex + 1)];
}
// and in sessionEntryToContextMessages:
if (entry.type === "compaction") {
	return [createCompactionSummaryMessage(entry.summary, ...), ...entry.retainedTail];
}
```

**Flow:** scan backward for the LAST compaction entry → context = that entry + everything after it (earlier history vanishes because it's already inside the summary) → flatten via per-type projection while deriving current thinkingLevel/model/activeToolNames from metadata entries and assistant messages along the path.
**Invariant:** Exactly one compaction summary may appear in context — the newest one — and its retained tail is expanded inline at READ time (never stored as separate message entries), so there is exactly one source of truth for what survived. Deferred assistant placeholders never reach the provider.
**Probe:** `packages/agent/test/harness/compaction.test.ts:336/:359` ("builds session context with a compaction entry" / "tracks model and thinking level changes in built context").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "buildSessionContext defaultContextEntryTransform", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt last-compaction-wins + read-time tail expansion + per-entry-type projection. Adapt the custom-projector hook if your host has extra entry types. Omit nothing. Coverage caveat: none for the two pinned behaviors.
