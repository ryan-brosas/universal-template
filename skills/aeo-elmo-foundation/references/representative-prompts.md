<!-- capsule-v2 -->
# Representative prompt selection — how do you pick 4 prompts that don't flatter or slander?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How does a report choose which prompts to feature without cherry-picking bias?

## 2 strengths + 2 opportunities with a zero-SoV cap
**Path/Symbol:** `packages/lib/src/report-metrics.ts:selectRepresentativePrompts` (L162–236).
**Signature:** `selectRepresentativePrompts(promptSoVs: PromptSoV[], isBrandedFn: (promptId) => boolean): SelectedPrompt[]`.
**Data Shape:** strengths = sov > 0 sorted by has-competitor-activity first then sov desc ("winning against nobody isn't compelling"); opportunities = competitor-active prompts, non-zero-sov first sorted by lowest brand SoV then most competitor activity; zero-sov candidates capped at 1 total "to avoid making the brand look invisible".

### Decisive source
```ts
const pool = nonBranded.length >= 4 ? nonBranded : promptSoVs;   // prefer organic-discovery prompts
let zeroSovCount = 0;
for (const o of [...nonZeroOpportunities, ...zeroSovOpportunities]) {
	if (selected.filter((s) => s.category === "opportunity").length >= 2) break;
	if (usedIds.has(o.promptId)) continue;
	const isZero = o.sov === null || o.sov === 0;
	if (isZero && zeroSovCount >= 1) continue;
	…
}
```

**Flow:** pick ≤2 strengths → fill opportunities preferring non-zero → if fewer than 4 selected, backfill from the merged remaining list applying the same zero-cap. Output is exactly `slice(0, 4)` of `{ promptId, category: "strength"|"opportunity", sov }`.
**Invariant:** the zero-SoV cap is an honesty rule in BOTH directions — at most one prompt may show a total absence, and strengths must have real competition to beat. UsedIds prevents one prompt appearing in both categories.
**Probe:** `packages/lib/src/report-metrics.test.ts:159` describe — "allows at most 1 zero-SoV prompt", "prefers non-zero SoV opportunities over zero SoV", "prefers non-branded prompts", "fills from other bucket when one has fewer than 2".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "selectRepresentativePrompts strengths opportunities zeroSovCount", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bucket structure + single-rounding + zero-cap wholesale — it is a reusable editorial-integrity algorithm for any benchmark report; adapt the 2+2 counts and the non-branded-pool threshold; omit nothing else.
