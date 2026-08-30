<!-- capsule-v2 -->
# Recall TUI rendering — aligned-row receipts, expanded/collapsed evidence, honest failure notes

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** How do you render an evidence-recovery tool's result so the agent-facing text and the human-facing TUI stay truthful about partial failures?

## Tool-result text vs details split (`src/tools/recall-observation.ts`)
**Path/Symbol:** `recall-observation.ts:191-197` (`aggregateStatus`), `:222-261` (`renderObservationOnlyTextFromResult`, `renderMemoryText`), `:263-284` (`resultDetails`), `:317-329` (`formatRecallHeaderForTui`), `:383-405` (`memoryRows`, `noteRows`), `:407-424` (`formatRecallResultForTui`).
**Signature:** every path returns `{ content:[{type:"text",text}], details: RecallObservationToolDetails }`; status ∈ `ok | partial | invalid_id | not_found | no_source | source_unavailable`.
**Data Shape:** details carry the SAME facts twice — structured (`sourceEntries[]` with `{id,origin,timestamp,tokens,qualifiers,content?}`, `missingSourceEntryIds[]`, `nonSourceEntryIds[]`, `unavailableSupportingObservations[]`) for programmatic/agent use, plus rendered rows for the TUI.

### Decisive source
```ts
function aggregateStatus(details): RecallObservationToolStatus {
	const observationOnly = details.reflections.length === 0
		&& details.unavailableSupportingObservations.length === 0;
	if (details.partial) return "partial";                 // ANY missing evidence wins first
	if (observationOnly && details.observations.some((m) => m.status === "source_unavailable"))
		return "source_unavailable";
	if (observationOnly && details.observations.length > 0 && details.sourceEntries.length === 0
		&& details.matches.every((m) => (m.sourceEntries ?? []).length === 0))
		return "no_source";
	return "ok";
}

function observationMatchDetails(match, includeSourceContent = true) {
	const unavailable = match.missingSourceEntryIds.length > 0 || match.nonSourceEntryIds.length > 0;
	const status = unavailable ? "source_unavailable"
		: match.sourceEntries.length === 0 ? "no_source"
		: match.status;                                      // "active" | "dropped"
	...
}
```
```ts
// Agent-facing text branches on kind:
const text = result.kind === "observation"
	? renderObservationOnlyTextFromResult(result)   // raw sources only + friendly per-failure lines
	: renderMemoryText(result);                     // Reflections/Observations/Unavailable/Sources sections
```

**Flow:** execute → id-pattern gate (`invalid_id`, message includes received value) → `recallMemorySources(branchEntries, memoryId)` → not_found ⇒ empty details with explanatory message → found ⇒ per-kind rendering with collision preamble when one id matches multiple records; TUI layer renders memory rows then note rows (`[invalid id] / [not found] / [id collision] / [dropped] / [missing support] / [missing source] / [non-source] / [unavailable evidence]`) then source metadata rows with content INDENTED ONLY when `expanded` (Ctrl+O), else a trailing `(Ctrl+O to expand)` hint.
**Invariant:** Failure honesty is structural: a dropped observation still recalls but is LABELED `[dropped]`; missing vs non-source ids are distinguished (pruned by compaction vs not renderable); `partial` beats every other status in the aggregate so no result can look fully-ok while evidence is missing; the header counts sources/tokens from DETAILS not from the text body. Dropped-but-recallable is stated explicitly ("dropped from active memory but remains recallable") because recall reads the ledger, not active memory.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "formatRecallResultForTui formatRecallHeaderForTui aggregateStatus observationMatchDetails renderMemoryText", limit: 10 });
```
(Direct tests: `tests/recall-tool.test.ts` pins invalid-id/not-found/dropped-labels/partial-status paths over fixture ledgers; `tests/session-ledger-recall.test.ts` pins the underlying union incl. collision + partial flags. The TUI row formatters are exercised via `tests/recall-tool.test.ts` details assertions rather than string-snapshot.)

## Verdict
Adopt the dual-channel result (agent text + structured details), the aggregate-status precedence `partial > source_unavailable > no_source > ok`, dropped-still-recallable labeling, and expanded-gated content indentation. Adapt row widths/status vocabulary to your TUI. Omit pi-tui `Text` objects; keep the invariant that rendered success can never hide partial evidence.
