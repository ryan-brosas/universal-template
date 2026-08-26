<!-- capsule-v2 -->
# Search-semantics comparison — how does teable prove an n-gram (bigram/trigram) substring index preserves ILIKE results before rollout?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** A GIN trigram/bigram index changes substring semantics subtly. How do you compare each candidate strategy against the ILIKE baseline — match counts, sampled record overlap, plan cost — and hand the decision to an LLM with a redacted probe?

## ILIKE baseline + per-strategy deltas + LLM review input
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/searchVector.ts` — `analyzeSearchSemantics` (1704–1758), `analyzeIlikeSemantics` (1760–1796), `analyzeNgramSemantics` (1798–1830), `addSearchSemanticsBaselineDeltas` (1832–1873), `semanticDeltaReasonCodes` (1875–1890), `countIlikeMatches` (2009–2024), `sampleIlikeMatches`/`sampleSearchMatches` (2026–2081), `buildIlikeWhere` (2083–2093), `buildNgramTokenPreview` (1941–1957), `truncatePreview` (2095–2115), `failedSemanticsComparison` (1892–1917).
**Signature:** `analyzeSearchSemantics(db, {physical, fields, providerCapabilities, searchProbe, includeResultSamples, sampleResultLimit}): Promise<TableQuerySearchSemanticsReport | undefined>`.
**Data Shape:** report = `{searchProbeLengthBucket, comparedStrategies, baselineStrategy:'ilike', comparisons[], llmEvaluationInput:{status:'needs_llm_review', redaction:'ephemeral_operator_probe_not_persisted', searchProbe, instruction, criteria[], strategies[]}}`. Comparison = `{strategy:'ilike'|'bigram'|'trigram', semantics, available, indexSupport, tokenPreview[], tokenCount, explainStatus, cost, planNode, usesIndex, matchCount, matchCountDeltaFromIlike?, matchCountDeltaPctFromIlike?, sampleOverlapWithIlike?, sampleResults[], reasonablenessAssessment}`.

### Decisive source
```ts
const baseline = await analyzeIlikeSemantics(db, {...});   // EXPLAIN + count(*) + LIMIT samples
const comparisons = addSearchSemanticsBaselineDeltas([baseline, ...providerCapabilities.map(cap => analyzeNgramSemantics({capability: cap, baseline, searchProbe}))]);
// n-gram strategy is derived from the provider; token preview = sliding n-grams capped at 16:
const strategy = cap.provider === 'pg_bigm' ? 'bigram' : 'trigram';
// deltas vs ILIKE:
const matchCountDeltaPctFromIlike = baseline.matchCount > 0 ? (comparison.matchCount - baseline.matchCount)/baseline.matchCount*100 : undefined;
const sampleOverlapWithIlike = baselineIds.size > 0 ? comparison.sampleResults.filter(s => s.recordId && baselineIds.has(s.recordId)).length : undefined;
// reason codes from the delta magnitude:
if (Math.abs(deltaPct) >= 50) return ['large_match_count_delta'];
if (Math.abs(deltaPct) >= 10) return ['moderate_match_count_delta'];
return ['match_count_close_to_ilike'];
```

**Flow:** if no fields or no probe, return undefined → clamp sample limit to 3 → run the ILIKE baseline (EXPLAIN cost, `count(*)`, up to 3 sampled rows with `__id` + up to 4 field previews truncated to 120 chars, whitespace-normalized) → for each usable provider build a bigram/trigram comparison reusing the baseline cost/match/samples (n-gram semantics are identical to ILIKE substring) → compute deltas and overlap → tag reason codes → assemble an LLM-evaluation input with a redacted probe (`ephemeral_operator_probe_not_persisted`) and explicit criteria (match-count parity, probe length, index use, cost improvement).
**Invariant:** the ILIKE baseline is the ground truth for substring semantics; every n-gram comparison is judged against it by match-count delta and sampled-record overlap, and the whole thing is explicitly marked `needs_llm_review` — the advisor never auto-rolls out an n-gram path on its own; the probe is never persisted (redaction marker).
**Probe:** `searchVector.spec.ts:89` `describe('addSearchSemanticsBaselineDeltas')` — `:90` 'adds match-count and sample-overlap deltas against the ILIKE baseline', `:114` 'marks identical n-gram match counts as compatible with the ILIKE baseline'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "analyzeSearchSemantics addSearchSemanticsBaselineDeltas analyzeIlikeSemantics buildNgramTokenPreview", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ILIKE-baseline + per-strategy delta + sample-overlap comparison with explicit LLM-review handoff and redacted probe; adapt the n-gram lengths and criteria to host; omit teable's provider capability plumbing if the host has a single access method. Coverage: fully indexed in cited ranges.
