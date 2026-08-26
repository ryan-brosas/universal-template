<!-- capsule-v2 -->
# Recall evidence tool — exact-source recovery by memory id with honest partial-failure statuses

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** After compaction discards raw turns, how do you recover EXACT source evidence behind a compressed memory id?

## Ledger lookup (`src/session-ledger/recall.ts`)
**Path/Symbol:** `recall.ts:172-237` (`recallMemorySources`), `recall.ts:93-122` (`indexLedger`), `recall.ts:124-154` (`resolveObservationSources`).
**Signature:** `recallMemorySources(entries: Entry[], memoryId: string): RecallResult` — discriminated union `not_found | found`.
**Data Shape:** found result carries `kind: "observation"|"reflection"|"mixed"`, per-match `{status: "active"|"dropped", sourceEntries[], missingSourceEntryIds[], nonSourceEntryIds[]}`, aggregate `collision: boolean`, `partial: boolean`, `missingSupportingObservationIds[]`.

### Decisive source
```ts
const directObservationMatches = indexedObservations.filter(({ observation }) => observation.id === memoryId);
const reflectionMatches = indexedReflections.filter(({ reflection }) => reflection.id === memoryId);
...
for (const { reflection } of reflectionMatches) {
	for (const observationId of uniqueStrings(reflection.supportingObservationIds)) {
		const indexed = observationsById.get(observationId);
		if (!indexed) { missingSupportingObservationIds.push(observationId); continue; }
		addObservation(indexed);       // reflection id expands to its supporting observations' sources
	}
}
...
kind: directObservationMatches.length > 0 && reflectionMatches.length > 0 ? "mixed"
	: reflectionMatches.length > 0 ? "reflection" : "observation",
collision: matchCount > 1,
partial: missingSourceEntryIds.length > 0 || nonSourceEntryIds.length > 0 || uniqueMissingSupportingObservationIds.length > 0,
```

**Flow:** index every recorded entry once (with record indexes for stable keys `entryId:recordIndex`) → match the id against observation ids AND reflection ids → reflections expand to their supporting observations → resolve each observation's `sourceEntryIds` against the CURRENT branch, classifying misses as missing (pruned/other branch) vs non-source (wrong type) → dedupe sources by entry id.
**Invariant:** A reflection id yields the SOURCES of its supporting observations — evidence recovery traverses the support graph. Dropped observations remain recallable (`status:"dropped"`), because tombstones remove from active memory, not from history. Id COLLISIONS (hash prefix clash) return all matches plus `collision:true` instead of guessing. Every incompleteness surfaces as data (`partial`, missing arrays), never as a silent gap.

## Tool layer (`src/tools/recall-observation.ts`)
**Path/Symbol:** `recall-observation.ts:438-483` (`recallObservationTool`, `execute`), `:191-197` (`aggregateStatus`), `:317-329` (`formatRecallHeaderForTui`).
**Data Shape:** tool statuses `ok | partial | invalid_id | not_found | no_source | source_unavailable`; parameter pattern-enforced `^[a-f0-9]{12}$`.
### Decisive source
```ts
if (!MEMORY_ID_PATTERN.test(memoryId)) return textResult(message, emptyDetails("invalid_id", memoryId, message));
const branchEntries = ctx.sessionManager.getBranch() as Entry[];
const result = recallMemorySources(branchEntries, memoryId);
if (result.status === "not_found") return textResult(message, emptyDetails("not_found", ...));
return renderFoundResult(result);
```
```
promptGuidelines: [
	"Use recall before making an important decision that depends on a compacted observation or reflection...",
	"Do not use recall as semantic search or transcript browsing; you must already have a specific 12-character memory id.",
	"Do not recall every id preemptively..."],
```

**Flow:** schema-level regex rejects malformed ids cheaply → branch-scoped lookup → observation-only hits render sources directly; mixed/reflection hits render sections (reflections / observations / unavailable supporting / unavailable sources / full source blocks) → TUI renderer shows aligned rows + expandable content.
**Invariant:** The tool is deliberately NOT semantic search — it requires an exact id and says so in its prompt guidance; ids arrive via summary lines, `/om:view`, or prior recalls. Statuses distinguish "no source ever existed" from "source unavailable on this branch".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "recallMemorySources indexLedger resolveObservationSources recallObservationTool aggregateStatus", limit: 10 });
```
(Direct tests: `tests/session-ledger-recall.test.ts`, `tests/recall-tool.test.ts` pin kinds, collisions, partials, dropped-recallable.)

## Verdict
Adopt exact-id evidence recovery over the support graph, current-branch re-resolution with missing/non-source classification, collision honesty, and anti-pattern prompt guidance (id required, not search). Adapt the render formats to your UI; keep the status taxonomy. Omit TUI-specific rendering if your host has none.
