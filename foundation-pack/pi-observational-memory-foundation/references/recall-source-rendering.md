<!-- capsule-v2 -->
# Recall-source rendering — the second serialization dialect that shows raw evidence without leaking redacted thinking

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** After compaction destroys the raw turns, how do you render a ledger-referenced source entry back into text for the model and TUI — honestly, including what was never text?

## Renderer family (`src/serialize.ts`)
**Path/Symbol:** `serialize.ts:18-25` (`formatRecallTimestamp`), `serialize.ts:27-60` (`textAndPlaceholders`), `serialize.ts:238-257` (`renderRecallMessage`), `serialize.ts:259-267` (`renderRecallSourceEntry`), `serialize.ts:269-274` (`renderRecallSourceEntries`).
**Signature:** `renderRecallSourceEntry(entry: RenderableEntry): string | null`; `renderRecallSourceEntries(entries): string`; `formatRecallTimestamp(...values: Array<number|string|undefined>): string`.
**Data Shape:** `RenderableEntry = { type, id?, timestamp?, message?, customType?, content?, summary? }` — a structural duck over host branch entries; unknown types yield `null`, not a throw.

### Decisive source
```ts
// serialize.ts:18-25 — first-PARSEABLE-value-wins across candidate timestamps
export function formatRecallTimestamp(...values: Array<number | string | undefined>): string {
	for (const v of values) {
		if (v === undefined) continue;
		const d = new Date(v);
		if (!Number.isNaN(d.getTime())) return fmtLocal(d);
	}
	return "Unknown time";            // NOT "????-??-?? ??:??" — that marker belongs to the OTHER dialect
}
```
```ts
// serialize.ts:242-256 — assistant bodies keep thinking as labeled evidence, drop redacted
const body = textAndPlaceholders(msg.content, { includeThinking: true, omitRedactedThinking: true })
	.split("\n").filter(Boolean).join("\n");
if (!body) return null;             // empty assistant turn renders as nothing, not "[Assistant @ t]:"
```
```ts
// serialize.ts:269-274 — null AND blank-filtered join
return entries.map(renderRecallSourceEntry)
	.filter((block): block is string => block !== null && block.trim().length > 0)
	.join("\n\n");
```

**Flow:** `recallMemorySources` resolves a memory id to its `sourceEntries` → each entry goes through `renderRecallSourceEntry`: `message` → role triage (`[User @ t]` / `[Assistant @ t]` / `[Tool result: name @ t]`), `custom_message` → `[Custom message (customType) @ t]: text`, `branch_summary` → `[Branch summary @ t]` — anything else returns `null`. The tool layer (`tools/recall-observation.ts:127,164,235,257,281`) uses the joined text both as the model-visible `sourceText` and as the character count reported in tool details.

**Invariant:** This is the SECOND serialization dialect and must not be confused with the observer-input one (`serializeBranchEntries` / `serializeSourceAddressedBranchEntries`). Differences are load-bearing: (1) timestamp fallback — recall tries MULTIPLE candidates first-parseable-wins ending `"Unknown time"`; observer-input `formatTimestamp` renders one value ending `"????-??-?? ??:??"`; (2) content fidelity — recall keeps placeholders for non-text blocks (`[non-text content omitted]`, `[toolName({...})]`) and includes thinking as `[thinking: …]` while OMITTING redacted thinking entirely; observer-input strips to text-only lines; (3) labels — `Custom message (<type>)` vs `Custom (<type>)`. The recall dialect must show enough provenance for the model to trust evidence while never resurrecting redacted reasoning blobs. Unknown/blank entries vanish silently rather than emitting `[object Object]` garbage into context.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "renderRecallSourceEntry renderRecallMessage formatRecallTimestamp textAndPlaceholders renderRecallSourceEntries", limit: 10 });
```
(Direct tests: `tests/recall-tool.test.ts:48-97` pins the rendered TUI/evidence surface end-to-end through the tool (`✓ observation` rows, dropped-but-recallable, reflection-with-supporting-observations); `formatRecallTimestamp` itself sits below unit-test granularity — pinned to `serialize.ts:18-25`.)

## Verdict
Adopt the two-dialect split (observer-input vs recall rendering) with distinct timestamp fallbacks and label vocabularies, first-parseable-wins multi-candidate timestamps, placeholder-preserving non-text handling, redacted-thinking omission, and null-for-unknown entry types. Adapt label wording to your host's entry taxonomy. Omit nothing behavioral — silently dropping unknown entry kinds is the contract, not an oversight.
