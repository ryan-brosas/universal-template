<!-- capsule-v2 -->
# Experiment arms & calibrated projection — how to compare benchmark runs fairly while they are still running

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you group comparable benchmark runs into experiments and project a still-running arm's final pass rate without being fooled by a decided subset that isn't difficulty-representative?

## Decided-population stats + sibling-calibrated (Rasch) projection
**Path/Symbol:** `packages/metaharness/src/experiments.ts`:`summarizeArm` (91-127), `calibratedFinalPassPct` (147-190), `pickMergedTrials` (265-278), `canonicalArmOf` (249-256), `experimentOf`/`armOf` (59-68).
**Signature:** `summarizeArm(run: RunRow, traces: TraceRow[]): ArmSummary`; `calibratedFinalPassPct({decided: {task,passed}[], siblings: Map<task,{passes,decided}>, remaining: string[], nTotal}): number | null`; `pickMergedTrials(traces: TraceRow[]): TraceRow[]`; `canonicalArmOf(jobName): string`.
**Data Shape:** experiment id = first `-`-token of the job name (`sb2-n8` → `sb2`); rerun suffixes `-fix|-backfill|-refill|-retry|-rerun|-bf\d*` fold into the canonical arm. Trial statuses: `pass|fail|error|running`; "decided" = pass/fail/error for spend math, but merge precedence treats only pass/fail as reward-decided.

### Decisive source
```ts
// Every observed stat is computed over DECIDED trials only — numerator and
// denominator from the same population. `run.costUsd` includes in-flight
// trials' accumulating spend, so dividing it by the decided count wildly
// overstates $/task early in a run; per-trial trace costs don't.
const decided = traces.filter(t => t.status === "pass" || t.status === "fail" || t.status === "error");
const decidedCost = decided.reduce((sum, t) => sum + (t.costUsd || 0), 0);
const costPerTask = decided.length > 0 ? decidedCost / decided.length : null;

// One pseudo-task of mean difficulty, "passed" at the sibling base rate,
// shrinks the fit toward sibling-average skill — a perfect (or zero)
// decided record would otherwise drive the shift to ±∞ (separation) and
// project near-certainty everywhere.
const fitLogits = [...decidedLogits, logit(meanP)];
const target = passes + meanP;
let lo = -6; let hi = 6;
for (let i = 0; i < 50; i++) { /* bisection on monotone Σ σ(logit(p_t)+b) */ }
```

**Flow:** group runs by `experimentOf(jobName)` → per arm, strip rerun suffixes (`canonicalArmOf`) and merge member runs' trials with `pickMergedTrials` — one row per task where a decided trial always beats an undecided one and, within the same class, latest `updatedAt` wins (a `-fix` replaces an error, never a genuine earlier pass) → `summarizeArm` computes pass%/cost-per-task over decided trials only and adds a linear projection (ETA from observed completion rate, total cost = committed + decided-rate × remaining) → `experimentDetail` replaces each running arm's naive pass projection with `calibratedFinalPassPct`: per-task difficulty p_t=(passes+1)/(n+2) from every OTHER arm's outcomes, clamped logit, one-parameter skill shift b moment-matched on the decided set by bisection, remaining tasks scored through σ(logit(p_t)+b), unknown tasks at mean difficulty.
**Invariant:** (1) denominators come from the same population as numerators — never divide whole-run `costUsd` by decided count; (2) projections must be difficulty-aware: an arm that only decided easy tasks so far may NOT project its 100%, yet can never project below what it already banked; (3) merging never downgrades a decided result to an error/running one.
**Probe:** `packages/metaharness/test/experiments.test.ts:77-239` — `computes observed and projected stats from decided trials, not total spend` ($0.50 vs $1.50 per task), `discounts a perfect score earned on tasks every sibling also passes` (<70% but ≥37.5%), `projects the sibling mean when the arm performs exactly at sibling level`, `prefers decided re-runs over errors but never downgrades a decided result`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "calibratedFinalPassPct summarizeArm pickMergedTrials canonicalArmOf", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt wholesale: the decided-population accounting rule and the smoothed-logit sibling calibration transfer to any A/B benchmark dashboard with in-flight trials (the +1/+2 smoothing, clamped logits, and mean-difficulty pseudo-task are what keep the fit finite). Adapt the job-name prefix grammar and the specific suffix regex to your naming scheme; omit the prewalk config-label rendering (host-specific display). Direct bun:test probes pin all four behaviors.
