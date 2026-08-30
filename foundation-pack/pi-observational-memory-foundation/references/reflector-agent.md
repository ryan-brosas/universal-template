<!-- capsule-v2 -->
# Reflector agent — crystallize durable facts with supporting ids; support ids ARE future dropper evidence

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** How do you distill observations into durable reflections such that later pruning can trust the linkage?

## Reflection recording (`src/agents/reflector/agent.ts`)
**Path/Symbol:** `agent.ts:107-206` (`runReflector`), `agent.ts:82-105` (`normalizeSupportingObservationIds`, `normalizeReflectionContent`).
**Signature:** `runReflector(args): Promise<Reflection[] | undefined>`; schema: `reflections[] minItems 1`, each `{ content minLength 1, supportingObservationIds minItems 1 }`.
**Data Shape:** accepted reflection = `{ id: hashId(content), content: trimmed, ≤10k chars, NO \r|\n, supportingObservationIds ⊆ active observation ids (chunk-ordered, deduped), tokenCount }`.

### Decisive source
```ts
function normalizeReflectionContent(content: string): string | undefined {
	const normalized = truncateRecordContent(content.trim());
	if (!normalized || /\r|\n/.test(normalized)) return undefined;   // single-line enforced
	return normalized;
}
```
```ts
for (const id of supportingObservationIds) {
	if (!allowedOrder.has(id)) return undefined;    // unknown id ⇒ whole reflection rejected
	seen.add(id);
}
...
const id = hashId(content);
if (existingReflectionIds.has(id) || accumulated.has(id)) { duplicates++; continue; }
```

**Flow:** input = folded active observations WITH coverage tiers rendered inline (`[coverage: none|partial|strong]`) + existing reflections → model calls `record_reflections` repeatedly → per-record validation (single-line content, allowlisted support ids) → hash-dedupe against BOTH persisted and same-run reflections → progress receipt → coverage transitions summarized before/after for debug telemetry.
**Invariant:** Support ids must cover ALL AND ONLY the observations whose durable meaning is preserved — they become dropper coverage evidence, so sloppy support sets cause wrong drops later. Tiers are review context, not quotas ("coverage as stewardship"). Unknown support id ⇒ atomic rejection of that reflection, mirroring the observer's rule.

## Coverage tier math (`src/agents/dropper/coverage.ts`)
**Path/Symbol:** `coverage.ts:18-42` (`reflectionSupportCounts`, `reflectionCoverageTierForCount`, `reflectionCoverageMap`).
**Signature:** tier = `none` (0 citing reflections) / `partial` (1) / `strong` (≥2), counted over UNIQUE support ids per reflection.
**Data Shape:** `REFLECTION_COVERAGE_DROP_RANK = { strong: 0, partial: 1, none: 2 }` — lower rank = safer to drop.

### Decisive source
```ts
export function reflectionSupportCounts(reflections: readonly Reflection[]): Map<string, number> {
	const counts = new Map<string, number>();
	for (const reflection of reflections) {
		const uniqueIds = new Set(reflection.supportingObservationIds);   // unique per reflection!
		for (const id of uniqueIds) counts.set(id, (counts.get(id) ?? 0) + 1);
	}
	return counts;
}
export function reflectionCoverageTierForCount(count: number): ReflectionCoverageTier {
	if (count <= 0) return "none";
	if (count === 1) return "partial";
	return "strong";
}
```

**Flow:** count how many DISTINCT reflections cite each observation id → map to tiers → tiers render into reflector/dropper prompts and rank drop candidates.
**Invariant:** The Set-per-reflection matters: one reflection listing an id twice must NOT manufacture "strong" coverage. Tier thresholds are deliberately minimal (1 vs ≥2) — coverage breadth, not volume, is the signal.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "runReflector normalizeSupportingObservationIds reflectionCoverageMap reflectionSupportCounts summarizeCoverageTransitionsByRelevance", limit: 10 });
```
(Direct tests: `tests/reflector.test.ts` pins validation/dedupe; `tests/dropper-coverage.test.ts` pins tier boundaries.)

## Verdict
Adopt allowlist-validated support ids with atomic rejection, single-line normalized content, hash-dedupe across runs, per-reflection unique-id coverage counting into none/partial/strong tiers, and prompt-validator semantic alignment. Adapt tier names/thresholds if your pruner needs different granularity. Omit transition-telemetry summaries unless you run structured debug logs.
