<!-- capsule-v2 -->
# Fold + projection — first-valid-wins replay, drop tombstones, and the fullFold escape hatch

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** How do you reconstruct current memory state from an append-only ledger that contains invalid, duplicated, superseded, and dropped records?

## Ledger fold (`src/session-ledger/fold.ts`)
**Path/Symbol:** `fold.ts:50-100` (`foldLedger`).
**Signature:** `foldLedger(entries: Entry[], options?: { upToEntryId?: string }): FoldedLedger`.
**Data Shape:** out: `{ observations (incl. dropped), activeObservations, droppedObservationIds:Set, reflections, observationsById, reflectionsById }`.

### Decisive source
```ts
for (let i = 0; i <= endIdx; i++) {
	const entry = entries[i];
	if (!entry) continue;
	if (isCustomEntry(entry, OM_OBSERVATIONS_RECORDED)) {
		if (!isObservationsRecordedData(entry.data)) continue;      // invalid data ignored, not thrown
		for (const observation of entry.data.observations) {
			if (!observationsById.has(observation.id)) {            // FIRST-valid-record-wins
				observationsById.set(observation.id, observation);
			}
		}
		continue;
	}
	...
	if (isCustomEntry(entry, OM_OBSERVATIONS_DROPPED)) {
		if (!isObservationsDroppedData(entry.data)) continue;
		for (const observationId of entry.data.observationIds) {
			droppedObservationIds.add(observationId);               // tombstone, even for unknown ids
		}
	}
}
const activeObservations = observations.filter((o) => !droppedObservationIds.has(o.id));
```

**Flow:** walk entries root→boundary → skip unknown custom types, V2-era entries, and shape-invalid data SILENTLY → first valid record per id wins → drops accumulate as a tombstone Set (retained even when the id has no folded observation yet) → active = all minus tombstones.
**Invariant:** Drops are TOMBSTONES, not deletions — history is never rewritten, and a drop recorded before its target's record still applies (Set membership is order-free). First-valid-wins makes replays deterministic across duplicate appends. `upToEntryId` bounds time-travel folds; unknown ids fold through tip.

## Compaction projection + fullFold (`src/session-ledger/projection.ts`)
**Path/Symbol:** `projection.ts:173-208` (`buildCompactionProjection`), `projection.ts:159-171` (`latestFullFoldBoundaryId`), `projection.ts:141-157` (`fullProjection`, `visibleProjection`).
**Signature:** `buildCompactionProjection(entries, firstKeptEntryId, { observationsPoolMaxTokens }): CompactionProjection`.
**Data Shape:** out: `{ fullFold:boolean, observations, reflections, details:{type:"om.folded",version:1,fullFold,observations,reflections} }`.

### Decisive source
```ts
const fullFoldBoundaryId = latestFullFoldBoundaryId(entries);   // last compaction with details.fullFold===true
const maintenanceBoundary = fullFoldBoundaryId ? entryBoundary(fullFoldBoundaryId) : noneBoundary();
const normalProjection = foldProjection(entries, {
	observationsBoundary: entryBoundary(firstKeptEntryId),       // keep observations up to cut
	reflectionsBoundary: maintenanceBoundary,                    // reflections/drops only to last FULL fold
	dropsBoundary: maintenanceBoundary,
});
const fullFold = observationTokens >= config.observationsPoolMaxTokens;
const projection = fullFold ? fullProjection(entries, firstKeptEntryId) : normalProjection;
```

**Flow:** on compaction, observations fold up to the kept-entry boundary; reflections and drop-tombstones fold only to the last fullFold compaction boundary (they are durable across cuts) → if the surviving observation pool exceeds the pool max, flip to `fullFold`: fold EVERYTHING up to the cut and carry it inside the compaction `details`.
**Invariant:** The three boundaries are deliberately DIFFERENT — porting them as one boundary silently loses post-fold reflections or resurrects dropped observations. The stored `MemoryDetails` snapshot (validated by `isMemoryDetails`) is what FUTURE sessions read via `visibleProjection` when the raw branch is gone. Tombstone application in `foldProjection` filters at the END (`observations.filter(...)`), so a drop covering an observation folded under a different boundary still hides it.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "foldLedger buildCompactionProjection latestFullFoldBoundaryId fullProjection visibleProjection MemoryDetails", limit: 10 });
```
(Direct tests: `tests/session-ledger-fold.test.ts` :14-30 bounded fold + first-valid-wins; `tests/session-ledger-projection.test.ts` :96-125 fullFold=false path, :57+ fullFold boundary selection.)

## Verdict
Adopt first-valid-record-wins folding with silent shape-validation skips, order-free drop tombstones, per-kind projection boundaries (observations=cut point, reflections+drops=last full fold), and the token-triggered fullFold snapshot carried in compaction details for future sessions. Adapt the 20k default pool max and the `om.folded` details envelope to your host. Omit nothing behavioral.
