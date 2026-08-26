<!-- capsule-v2 -->
# Coverage summary plane — per-relevance count/token buckets and before→after transitions that never expose ids

**Source:** pi-observational-memory MIT `master@ce9fc982b3a219a7839f07c9f4a3e054e81a2b21`; Codebase Memory `pi-observational-memory`. **Question:** How do you show an LLM worker (and your own logs) the pool's reflection-coverage state — as prompt evidence and telemetry — without tiers becoming quotas or logs leaking memory ids?

## Path/Symbol
**Path:** `src/agents/dropper/coverage.ts` :44-128; consumers `src/agents/reflector/agent.ts` :112-117, :196, :205 (+ its duplicate line renderer :51-56) and `src/agents/dropper/agent.ts` :140-152, :262-284.
**Symbols:** `summarizeCoverageByRelevance` :61-73, `summarizeCoverageByRelevanceForIds` :75-86, `summarizeCoverageTransitionsByRelevance` :97-114, `observationToDropperLine` :116-121, `coverageTierForObservation` :123-128. (Tier math :18-42 is owned by reflector-agent.md.)

**Signature:** `summarizeCoverageByRelevance(observations, coverageById): Record<relevance, Record<tier, {count,tokens}>>`; `summarizeCoverageTransitionsByRelevance(observations, beforeMap, afterMap): Record<relevance, Record<"none->partial"|…, {count,tokens}>>`.

**Data Shape:** buckets are count+token aggregates keyed relevance × tier; transition keys are `"${before}->${after}"` strings, emitted ONLY for observations whose tier actually changed. Missing ids default to `"none"` (`?? "none"`), never throw.

### Decisive source
```ts
export function summarizeCoverageByRelevance(observations, coverageById) {
	const summary = emptyCoverageSummaryByRelevance();
	for (const observation of observations) {
		const tier = coverageById.get(observation.id) ?? "none";
		const bucket = summary[observation.relevance][tier];
		bucket.count++;
		bucket.tokens += observation.tokenCount;
	}
	return summary;
}

export function summarizeCoverageTransitionsByRelevance(observations, beforeCoverageById, afterCoverageById) {
	const summary = emptyCoverageTransitionSummaryByRelevance();
	for (const observation of observations) {
		const before = beforeCoverageById.get(observation.id) ?? "none";
		const after = afterCoverageById.get(observation.id) ?? "none";
		if (before === after) continue;
		const key = `${before}->${after}`;
		...
	}
	return summary;
}

export function observationToDropperLine(observation, coverage) {
	return `[${observation.id}] ${observation.timestamp} [${observation.relevance}] [coverage: ${coverage}] ${observation.content}`;
}
```

**Flow:** `reflectionCoverageMap` computes each observation's tier once → BOTH consumers render pool lines with inline `[coverage: tier]` tags (reflector input via its own byte-identical `observationToReflectorLine`, dropper input via `observationToDropperLine`) → reflector logs a before-map at start (:113-117), recomputes after accepted reflections (:196), and emits `coverageTransitionsByRelevance` (:205); dropper logs `coverageSummaryByRelevance` at start and `selectedCoverageSummaryByRelevance` over final drops via `...ForIds` (:282).

**Invariant:** Summaries carry counts/tokens ONLY — never ids — so structured debug logs describe the pool without dumping its content. The `[coverage: …]` tag is EVIDENCE DISPLAY for the model; enforcement stays in deterministic code (`selectDropCandidates` ranks by tier; prompts say tiers are review context, not a quota). The two line-renderer copies are an intentional duplication to note when refactoring: identical format, one file per consumer, no shared import from the prompts side.

**Probe (direct tests):**
```bash
cd /mnt/hdd/utopia/inspo/pi-observational-memory && \
npx vitest run tests/dropper-coverage.test.ts   # 5 passed: tier boundaries 0/1/2+, unique-id counting
# (a reflection listing an id twice must not manufacture strong), bucket shape
# {low:{none:{count,tokens}}|...}, transitions "none->partial"/"partial->strong" with unchanged
# pairs omitted, and the model-facing line carrying id/relevance/[coverage: strong]/content but
# NO drop-priority/drop-resistance vocabulary
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "summarizeCoverageByRelevance summarizeCoverageTransitionsByRelevance observationToDropperLine", limit: 10 });
// resolves all three symbols in src/agents/dropper/coverage.ts (61-73, 97-114, 116-121)
```

**Verdict:** Adopt aggregate-only coverage telemetry (counts/tokens, no ids), changed-only transition keys, `?? "none"` defaults, and inline `[coverage: tier]` evidence tags rendered identically into every consumer's pool lines. Adapt relevance/tier vocabularies and bucket shapes to your domain. Omit transition telemetry if you lack structured logging — the prompt tags are the load-bearing half.
