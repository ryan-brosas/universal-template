<!-- capsule-v2 -->
# Report prompt selection — how does a one-shot report pick 70 prompts from candidates it already paid for?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** What is the candidate→select→reuse pipeline for a whitelabel/report run?

## Over-sample 20%, sort by mention signal, reuse paid runs
**Path/Symbol:** `apps/worker/src/report-worker.ts:TARGET_PROMPTS_COUNT` (L22), `WHITELABEL_REPORT_RUNS_PER_MODEL` (L30–34), `selectOptimalPrompts` (L83–158), `processReportJob` (L243–420).
**Signature:** `selectOptimalPrompts(candidateResults, brandName, brandWebsite): string[]` (target 70, candidates = ceil(70 × 1.2) = 84).
**Data Shape:** per candidate: brandMentionRate + competitorMentionRate over its runs; `isActuallyBranded = isPromptBranded(value, brandName, website)` recomputed (LLM's branded flag OR-ed in). Non-branded sorted: prompts WITHOUT brand mentions first (organic discovery is the test), then competitor-rate desc (0.1 bucket), then brand-rate desc. Whitelabel sample counts are a fixed map `{chatgpt:2, claude:1, google-ai-mode:1}` — an unlisted model THROWS ("configuration error"), other modes use RUNS_PER_PROMPT.

### Decisive source
```ts
nonBrandedPrompts.sort((a, b) => {
	if (a.hasBrandMention !== b.hasBrandMention) return a.hasBrandMention ? -1 : 1;
	if (Math.abs(a.competitorMentionRate - b.competitorMentionRate) > 0.1) return b.competitorMentionRate - a.competitorMentionRate;
	return b.brandMentionRate - a.brandMentionRate;
});
…
// Reuse the paid candidate runs when assembling the final report.
const selectedPromptResults = candidateResults.filter((result) => selectedPromptValues.includes(result.promptValue));
```

**Flow:** analyzeBrand (shared with onboarding) → candidates tested in batches of 20 with 1s inter-batch sleep and per-candidate error isolation (failed candidate keeps its slot with empty runs) → select 70 → final report REUSES the selected candidates' paid runs rather than re-running → progress persisted via `updateProgress` writes that never throw.
**Invariant:** the selection budget targets ~14–28 estimated brand mentions (MIN/MAX_BRAND_MENTIONS) so reports are comparable across brands; candidate failures must not abort the batch (progress still advances).
**Probe:** no dedicated unit file for selection; behavior pinned indirectly by tag-utils tests (`isPromptBranded`) and the shared analyzeBrand suite. State this caveat when porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "selectOptimalPrompts WHITELABEL_REPORT_RUNS_PER_MODEL processReportJob", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt over-sample→score→reuse; adapt target counts and the fixed per-model sampling map; omit the whitelabel throw-on-unknown-model only if your model set is closed.
