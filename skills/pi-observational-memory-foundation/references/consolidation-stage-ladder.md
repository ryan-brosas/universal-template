<!-- capsule-v2 -->
# Consolidation stage ladder — which stage may fire when, and how later stages see earlier stages' same-run writes

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** In a multi-stage LLM pipeline appending to ONE shared mutable ledger, what gates each stage — and how does a downstream stage consume records an upstream stage appended seconds ago?

## Path/Symbol
**Path:** `src/hooks/consolidation-trigger.ts`
**Symbols:** `ReflectorStageResult` :52-56, `mergeReflections` :66-75, `runReflectorStage` :360-403 (observation-coverage precondition :372-373; reflection anchor :395-397), `runDropperStage` :405-477 (same-run-only gate :413-416; merge :455; earlier-of tombstone anchor :467-468).

**Signature:** `runDropperStage(…, sameRunReflections: Reflection[], sameRunReflectionCoverageId?: string)`; `mergeReflections(existing, additional): Reflection[]` dedupes by content-hash id.

**Data Shape:** reflector returns `{outcome, sameRunReflections, effectiveReflectionCoverageId}` where the coverage id is the OBSERVATION coverage marker (`data.coversUpToId === observationCoverageId`), never the freshly appended entry's id.

### Decisive source
```ts
// runReflectorStage — reflections require an existing observation coverage marker
const observationCoverageId = latestCoverageMarkerId(entries, OM_OBSERVATIONS_RECORDED);
if (!observationCoverageId) return { outcome: "continue", sameRunReflections: [] };

// runDropperStage — pool pressure alone NEVER launches the dropper
if (!sameRunReflectionCoverageId || sameRunReflections.length === 0) {
	debugLog("dropper.waiting_for_reflection", { sameRunReflections: sameRunReflections.length });
	return "continue";
}
...
const reflectionsForDropper = mergeReflections(folded.reflections, sameRunReflections);
...
const coversUpToId = earlierCoverageMarkerId(entries, observationCoverageId, sameRunReflectionCoverageId);
```

**Flow:** observer appends observations → reflector runs only if an observation coverage marker exists AND its own token clock is due; its record anchors AT that marker → dropper runs ONLY when THIS RUN produced non-empty reflections; it re-folds the branch and MERGES same-run reflections over the fold (id-dedupe makes double-count impossible whether or not the branch snapshot already contains the just-appended record) → tombstone anchors at the EARLIER of the two coverage ids resolved by branch index.

**Invariant:** The gating asymmetry is the design: a full pool with no fresh reflection does no work (tests pin "does not launch dropper-only work when active pool is over target" and "waits for successful reflection even when active observation pool is over target") because drops are justified by coverage evidence, not by space pressure. Anchors are MARKER ids resolved through the id→index map — deliberately independent of `appendEntry`'s return value ("does not use appended reflection entry id for drop coverage when appendEntry returns no id"). Stage failures stay contained: observer/reflector abort the pipeline; a dropper failure leaves its reflection append intact.

**Probe (direct tests):**
```bash
cd /mnt/hdd/utopia/inspo/pi-observational-memory && \
npx vitest run tests/consolidation-trigger.test.ts   # 34 passed; decisive pins:
# :438 observer append unblocks reflector SAME RUN (append calls [obs,coversUpToId=raw-1] then
#   [refl,coversUpToId=raw-1]); :474/:589 dropper after same-run reflections;
# :494/:507/:558 pool-over-target alone ⇒ launchConsolidationTask not called / dropper skipped;
# :575 no reflect/drop append without observation coverage; :609 appendEntry returning no id
#   changes nothing; :627 empty reflection/drop sets append nothing; :639 failure boundaries.
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "runReflectorStage runDropperStage mergeReflections sameRunReflectionCoverageId", limit: 5 });
```

**Verdict:** Adopt evidence-gated staging: each downstream stage requires an upstream ARTIFACT from this run (not merely accumulated state), merges same-run writes over stale snapshots by id, and anchors derived records at resolved marker ids rather than append receipts. Adapt stage names and artifact types to your pipeline. Omit nothing behavioral — every gate maps to a named test.
