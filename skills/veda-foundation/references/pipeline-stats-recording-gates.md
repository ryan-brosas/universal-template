<!-- capsule-v2 -->
# Pipeline stats recording gates — how do you make in-run telemetry writes mode-gated, era-stamped, and unable to fail the run?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A judge stage produces learnable signal (which module/prompt won). Where in the pipeline do you record it, under what gates, with what identity, so that (a) runs without a module signal never pollute the store, (b) learned state is invalidated when prompts change, and (c) a disk failure can never kill an otherwise-successful run?

## Two gated, fire-and-forget appends inside runDeepThink
**Path/Symbol:** `src/pipelines/deep-think.ts:runDeepThink` judge-stage recording block (:1488-1585): pairwise entry build + append (:1488-1545), single-judge entry build + append (:1548-1585); identity input `options.runIdentityHash` (DeepThinkOptions :127), computed by `computeRunIdentityHash` in `src/commands/deep.ts` (:386-395) and checked against existing checkpoints at resume (:194-215); store side pinned by `src/stats/store.ts` / `pairwise-store.ts`.
**Signature:** inline in the generator; entries are `PairwiseStatEntryV2 {version:2, timestamp, promptHash, runId, judgeMode:'pairwise', candidates, votes, pairResults, era}` and `StatEntryV3 {version:3, timestamp, promptHash, runId, judgeMode:'single', judge, winner, participants, confidence}`; both appended via `new <Store>().append(entry).catch(() => {})`.
**Data Shape:** `promptHash = Bun.hash(prompt).toString(16).padStart(16,'0').slice(0,16)` (16-hex); pairwise `runId = ${timestamp}-${promptHash}`; single-judge `runId = options.runIdentityHash ?? ${timestamp}-${promptHash}`; confidence tiered `>= 0.7 high / >= 0.4 medium / else low`.

### Decisive source
```ts
// Record pairwise judge decisions for statistics (best-effort, never fails pipeline)
// Only record for pairwise mode - single/multi are not recorded
if (effectiveMode === 'pairwise' && judgeResult.pairwiseVotes && judgeResult.pairResults) {
```
```ts
// Record single-judge stats for win rate tracking
// Module win rates drive Thompson sampling in module mode, so uniform-prompt
// (listed mode) runs must never enter this store: they carry no module signal.
if (effectiveMode === 'single' && !solver.uniformPrompt && trace.solve.candidates.length > 0) {
```
```ts
          const pairwiseEntry: PairwiseStatEntryV2 = {
            version: 2,
            timestamp,
            promptHash,
            runId: `${timestamp}-${promptHash}`,
            judgeMode: 'pairwise',
            candidates: candidatesMeta,
            votes,
            pairResults,
            era: getCurrentEra(),
          };

          new PairwiseStatsStore().append(pairwiseEntry).catch(() => {});
```
and the single-judge twin ends with `new StatsStore().append(singleJudgeEntry).catch(() => {});` (:1585).

**Flow:** recording happens INSIDE the judge stage, after the trace is populated but before the `selected` event → pairwise gate requires effective mode `'pairwise'` AND both `pairwiseVotes` and `pairResults` present (a degraded pairwise run with missing vote data records nothing) → single-judge gate requires effective mode `'single'` AND NOT uniform-prompt AND at least one candidate, plus an inner check that the winner carries a module descriptor (no winner module ⇒ no entry) → the pairwise entry is stamped `era: getCurrentEra()` (content-addressed catalog digest — see catalog-era-rotation.md) so ratings derived from it live in a namespace that dies with any prompt change → the single-judge entry prefers `runIdentityHash` (the checkpoint-validation identity over prompt+context+shape options) as its `runId`, so a resumed run keeps ONE stats identity instead of minting a new one per process start → both appends are fire-and-forget promises with swallowed rejections.
**Invariant:** Telemetry can NEVER fail a run (`.catch(() => {})` on both appends); runs without a module signal (uniform/listed mode) must NEVER enter the single-judge store or Thompson Sampling learns from noise; every recorded entry is versioned (`version: 2|3`) so the lenient reader (stats-jsonl-lenient-log.md) can skip what it does not understand; era stamping means stale learning cannot leak across prompt-portfolio revisions.
**Probe:** NO dedicated upstream test for the in-pipeline gating (grep over `tests/` finds no reference to these blocks; the full generator has no end-to-end test). Store-side behavior IS pinned: `tests/stats/store.test.ts` — EXECUTED pass 8: 7 pass / 0 fail (malformed-line skip, unknown-version skip, v1 judgeMode normalization). Source-pinned probe: `grep -n "\.catch(() => {})" src/pipelines/deep-think.ts` → exactly two hits, :1545 and :1585.
**Coverage caveat:** the gating conditions themselves are source-derived contracts; a porting test should assert "uniform run ⇒ zero StatsStore writes" since that invariant has no upstream pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "PairwiseStatEntryV2 StatEntryV3 append catch runIdentityHash", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-part contract: mode-gated recording (record only where the signal exists), fire-and-forget persistence (telemetry failures are silent), and content-addressed era stamping (learning namespaces die with the prompts they were learned from). Adapt entry schemas to your stores. Omit the era stamp only if you have no learned-state plane at all.
