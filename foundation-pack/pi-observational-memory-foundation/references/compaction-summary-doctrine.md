<!-- capsule-v2 -->
# Compaction summary doctrine — the instructions that ride WITH projected memory so a fresh context reads it correctly

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** When projected memory REPLACES an LLM compaction summary, what text must accompany the records so post-compaction turns interpret them — conflicts, completed work, and recall handles — correctly?

## Path/Symbol
**Path:** `src/session-ledger/render-summary.ts`
**Symbols:** `CONTEXT_USAGE_INSTRUCTIONS` :3-10, `observationToSummaryLine` :12-14, `reflectionToSummaryLine` :16-18, `renderSummary` :20-31.

**Signature:** `renderSummary(reflections: Reflection[], observations: Observation[]): string` — `""` exactly when both arrays are empty (which flips the compaction hook into decline-ownership; see empty-summary-decline.md).

**Data Shape:** output = `[instructions] + "## Reflections\n[id] content"? + "## Observations\n[id] timestamp [relevance] content"?` joined by blank lines. Line formats are the recall handle contract: every memory line starts with its bracketed id; raw `sourceEntryIds`/`supportingObservationIds`/token counts are deliberately NOT rendered.

### Decisive source
```ts
const CONTEXT_USAGE_INSTRUCTIONS = `These are condensed memories from earlier in this session.

- Reflections: stable, long-lived facts about the user, project, decisions, and constraints. New reflection lines may include ids in brackets.
- Observations: timestamped events from the conversation history, in chronological order. Observation lines include ids in brackets.

Treat these as past records. When entries conflict, the most recent observation reflects the latest known state. Work that prior observations describe as completed should not be redone unless the user explicitly asks to revisit it.

When exact source context is needed for precision or traceability, use the recall tool with the relevant observation or reflection id. This is especially useful when a reflection materially affects a decision or is too compressed to continue confidently. Do not use recall as broad search or inject raw source unless it is needed.`;

export function renderSummary(reflections: Reflection[], observations: Observation[]): string {
	if (reflections.length === 0 && observations.length === 0) return "";
	const parts: string[] = [CONTEXT_USAGE_INSTRUCTIONS];
	if (reflections.length > 0) parts.push(`## Reflections\n${reflections.map(reflectionToSummaryLine).join("\n")}`);
	if (observations.length > 0) parts.push(`## Observations\n${observations.map(observationToSummaryLine).join("\n")}`);
	return parts.join("\n\n");
}
```

**Flow:** compaction hook projects the ledger → `renderSummary` becomes the ENTIRE replacement summary (no model call in the hot path) → the instructions head teaches the fresh context four things: records-are-past, observation-recency-wins conflict resolution, completed-work-do-not-redo, and exact-id recall discipline with its anti-pattern (not broad search).

**Invariant:** The reader doctrine pairs with the writer doctrine (memory-prompt-doctrine.md): prompts make workers RECORD truthfully; these instructions make future contexts CONSUME records truthfully. Conflict resolution is asymmetric BY DESIGN — reflections are stable facts, but when they disagree with events, the most recent OBSERVATION wins ("latest known state"). Ids in brackets are load-bearing: they are the only handles `recall` accepts after raw turns are gone, so a summary that omitted them would ship unusable memory. Empty input returns `""` rather than bare instructions — an instructions-only summary would claim ownership of a compaction that has nothing to remember.

## Probe (direct tests)
```bash
cd /mnt/hdd/utopia/inspo/pi-observational-memory && \
npx vitest run tests/session-ledger-render-summary.test.ts   # 5 passed: empty⇒"", instructions kept,
# id-tagged Reflections/Observations sections, and NO provenance leak (no sourceEntryIds /
# supportingObservationIds / entry ids / "[object Object]" anywhere in output)
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "renderSummary observationToSummaryLine reflectionToSummaryLine CONTEXT_USAGE_INSTRUCTIONS", limit: 5 });
// rank1 resolves pi-observational-memory.src.session-ledger.render-summary.renderSummary Function src/session-ledger/render-summary.ts 20-31
```

**Verdict:** Adopt the instructions-head + id-tagged-sections shape as a single unit — porting the record lines without the doctrine text (or vice versa) ships memory the next context misreads. Adapt section names, the recall tool's name, and the conflict rule to your semantics. Omit nothing behavioral: the no-provenance-leak property is test-pinned.
