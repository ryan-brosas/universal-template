<!-- capsule-v2 -->
# Dropper agent — propose-then-select with a hard drop cap and deterministic safety ranking

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** How do you let an LLM shrink the memory pool while making it structurally unable to over-drop or drop unsafely?

## Pool readiness + cap math (`src/agents/dropper/pool.ts`)
**Path/Symbol:** `pool.ts:16-71` (`observationTokenSum`, `maxDropCountForPool`, `observationPoolMetrics`).
**Signature:** `observationPoolMetrics(observations, targetTokens): { observationTokens, tokensOverTarget, fullness, maxDropsAllowed, overTarget, ready }`.
**Data Shape:** token sum counts FULL RENDERED LINES (id+timestamp+relevance+content), not bare content.

### Decisive source
```ts
const tokensOverTarget = observationTokens - targetTokens;
if (tokensOverTarget <= 0) return 0;
const averageObservationTokens = observationTokens / activeObservationCount;
const estimatedDrops = Math.ceil(tokensOverTarget / averageObservationTokens);
return Math.min(activeObservationCount, Math.max(1, estimatedDrops));
```
```ts
// tokens.ts — why full-line counting:
// Pool budgets that only count bare content undercount every line's
// metadata overhead ... so the configured pool target was reached later
// than the rendered memory actually allowed.
export function observationLineTokenCount(observation) {
	return estimateStringTokens(`[${o.id}] ${o.timestamp} [${o.relevance}] ${o.content}`);
}
```

**Flow:** dropper runs only when `ready` (= over target AND maxDropsAllowed > 0); the cap is sized to move the pool TOWARD target in one run, clamped to ≥1 and ≤ active count.
**Invariant:** Budget on rendered footprint — metadata overhead is real context. The prompt frames the maximum as "a hard upper bound, not a target; drop fewer or none if fewer are clearly safe" — model freedom lives INSIDE the cap.

## Propose → select (`src/agents/dropper/agent.ts`)
**Path/Symbol:** `agent.ts:133-284` (`runDropper`), `agent.ts:78-94` (`normalizeDropObservationIds`), `agent.ts:101-131` (`selectDropCandidates`).
**Signature:** `runDropper(args): Promise<string[] | undefined>` — proposals collected via tool, FINAL selection is code.
**Data Shape:** sort key tuple: `(coverageTierRank, relevanceRank, timestampAge, proposalIndex)` ascending.

### Decisive source
```ts
return Array.from(firstProposalIndex.entries())
	.map(([id, index]) => ({ id, index, observation: byId.get(id) }))
	.filter((c) => c.observation !== undefined)
	.sort((a, b) => {
		const coverageDelta = REFLECTION_COVERAGE_DROP_RANK[coverageTierForObservation(a.observation, coverageById)]
			- REFLECTION_COVERAGE_DROP_RANK[...b...];
		const relevanceDelta = RELEVANCE_DROP_RANK[a.observation.relevance] - RELEVANCE_DROP_RANK[b.observation.relevance];
		const ageDelta = timestampRank(a.observation.timestamp) - timestampRank(b.observation.timestamp);
		return coverageDelta || relevanceDelta || ageDelta || a.index - b.index;
	})
	.slice(0, maxDrops)
	.map((candidate) => candidate.id);
```
```ts
// unparseable timestamps rank LAST for dropping (keep them):
function timestampRank(timestamp: string): number {
	const parsed = Date.parse(timestamp);
	return Number.isFinite(parsed) ? parsed : Number.POSITIVE_INFINITY;
}
```

**Flow:** metrics gate → model proposes ids via `drop_observations` (validated against ACTIVE observations only; unknown/dup counted not applied) → after the loop, CODE selects final drops: dedupe keeping first-proposal order, filter unknowns, rank by (weakest reflection coverage → lowest relevance → oldest → earliest proposal), cut at `maxDropsAllowed` → append tombstone record anchored to earlier-of coverage marker.
**Invariant:** The LLM proposes but never decides the final set — selection, capping, and ranking are deterministic code, so identical proposals yield identical drops. Critical relevance does NOT lock an observation (it can still drop under strong evidence), but it ranks last. Dropping removes from ACTIVE memory only — ledger history and recall stay intact. `runDropper` re-checks metrics itself (`maxDropsAllowed <= 0 ⇒ undefined`) so it's safe standalone, not just via pipeline.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "selectDropCandidates normalizeDropObservationIds maxDropCountForPool observationPoolMetrics runDropper", limit: 10 });
```
(Direct tests: `tests/dropper.test.ts` :42 cap-from-token-excess, :122 coverage→relevance→age→stable ordering (:147/:160 precedence pins), :170 capped selection; `tests/dropper-pool.test.ts` pins fullness/cap math.)

## Verdict
Adopt propose-then-deterministically-select, the hard upper-bound cap derived from token excess over average line size, the four-key safety ranking with unparseable-timestamp protection, full-rendered-line budget counting, and active-memory-only drop semantics. Adapt relevance vocabulary and ranking weights to your domain. Omit the debug telemetry fields if you lack structured logging.
