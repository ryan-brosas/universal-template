<!-- capsule-v2 -->
# Coverage anchors — every recorded batch points at the source entry it covers; clocks advance only on valid markers

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** How do you know which part of a growing session has already been distilled, without trusting "latest entry wins"?

## Coverage resolution (`src/session-ledger/progress.ts`)
**Path/Symbol:** `progress.ts:36-87` (`isValidCoverageEntry`, `latestCoverageIndex`, `latestCoverageMarkerId`, `earlierCoverageMarkerId`).
**Signature:** `latestCoverageIndex(entries, customType): number` (−1 = nothing covers yet); `latestCoverageMarkerId(...): string | undefined`; `earlierCoverageMarkerId(entries, firstId, secondId): string | undefined`.
**Data Shape:** a coverage marker is valid ONLY when its custom entry's data passes shape validation AND `coversUpToId` resolves to an existing branch index.

### Decisive source
```ts
function isValidCoverageEntry(entry: Entry, customType: V3MemoryCustomType)
	: entry is Entry & { data: { coversUpToId: string } } {
	if (entry.type !== "custom" || entry.customType !== customType) return false;
	if (!isObject(entry.data) || typeof entry.data.coversUpToId !== "string") return false;
	if (customType === OM_OBSERVATIONS_RECORDED) return isNonEmptyArray(entry.data.observations);
	...
}
export function latestCoverageIndex(entries: Entry[], customType: V3MemoryCustomType): number {
	const idToIndex = entryIndexById(entries);
	let latest = -1;
	for (const entry of entries) {
		if (!isValidCoverageEntry(entry, customType)) continue;
		const coveredIndex = idToIndex.get(entry.data.coversUpToId);
		if (coveredIndex === undefined) continue;
		if (coveredIndex > latest) latest = coveredIndex;
	}
	return latest;
}
```

**Flow:** build id→branch-index map once → scan all entries of this custom type → keep MAX covered index (NOT last ledger position) → `latestCoverageMarkerId` returns the winning marker's id.
**Invariant:** "Latest" means max COVERED BRANCH POSITION, not most-recent ledger entry — an out-of-order or stale marker with a higher `coversUpToId` wins. Unresolvable ids (entry pruned by compaction, wrong branch) are silently skipped rather than poisoning the clock. Each stage owns an INDEPENDENT clock (observations / reflections / drops each have their own custom type), so reflector progress never blocks observer progress.

## Backlog extraction + earlier-of guard
**Path/Symbol:** `consolidation-trigger.ts:58-60` (`sourceEntriesAfter`), `consolidation-trigger.ts:464` (`earlierCoverageMarkerId` in dropper append).
**Data Shape:** backlog = source entries strictly after the observation-coverage index.

### Decisive source
```ts
function sourceEntriesAfter(entries: Entry[], index: number): Entry[] {
	return entries.slice(index + 1).filter(isSourceEntry);   // SOURCE_ENTRY_TYPES = message | custom_message | branch_summary
}
```
```ts
const coversUpToId = earlierCoverageMarkerId(entries, observationCoverageId, sameRunReflectionCoverageId);
const data = coversUpToId && droppedIds ? buildObservationsDroppedData(droppedIds, coversUpToId) : undefined;
```

**Flow:** observer serializes only entries after the last valid observation coverage marker; the drop record anchors to the EARLIER of {observation coverage, same-run reflection coverage} so the tombstone never claims coverage beyond what both stages had actually seen.
**Invariant:** Tombstones must not cover entries the reflection that justified them never saw — hence min-of-the-two, resolved by BRANCH INDEX not ledger order. Memory entries themselves are excluded from source backlogs (`isSourceEntry` allowlist).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "latestCoverageIndex latestCoverageMarkerId earlierCoverageMarkerId rawTokensSinceObservationCoverage", limit: 10 });
```
(Direct tests: `tests/session-ledger-progress.test.ts` — :61 independent clocks, :77 `coversUpToId` may point at a memory ledger entry, :89 max covered POSITION vs entry order, :103 earlier-marker-by-index.)

## Verdict
Adopt per-stage independent coverage clocks anchored to source-entry ids, max-covered-position semantics with silent skipping of unresolvable markers, and the earlier-of guard for derived records. Adapt the three custom-type names and source-entry type set to your host ledger. Omit nothing behavioral.
