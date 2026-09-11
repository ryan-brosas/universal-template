<!-- capsule-v2 -->
# MAD confidence scoring — how do you separate a real improvement from benchmark noise?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** How is the confidence number computed, when is it deliberately null, and why must it never gate the loop?

## computeConfidence — |best kept − first valid| / MAD(all valid)
**Path/Symbol:** `harness/server.ts:169–198` + twin `extensions/pi-autoresearch/src/utils/stats.ts:28–58`.
**Signature:** `computeConfidence(results: ExperimentResult[], direction: 'lower'|'higher'): number | null`.
**Data Shape:** input = all logged results of the CURRENT process lifetime (no segment filter); filters `r.metric > 0`; needs ≥3 valid rows; output = ratio or null.

### Decisive source
```ts
const validResults = results.filter((r) => r.metric > 0);
if (validResults.length < 3) return null;
const values = validResults.map((r) => r.metric);
const median = sortedMedian(values);
const deviations = values.map((v) => Math.abs(v - median));
const mad = sortedMedian(deviations);
if (mad === 0) return null;
const baseline = validResults[0]?.metric ?? null;
// best across status==='keep' rows only, compared via isBetter(direction)
if (bestKept === null || bestKept === baseline) return null;
return Math.abs(bestKept - baseline) / mad;
```

**Flow:** five null gates in order — fewer than 3 positive-metric results ⇒ null; MAD = 0 (all values identical) ⇒ null; no baseline ⇒ null; no kept result ⇒ null; best kept EQUALS baseline (zero improvement) ⇒ null. Otherwise ratio = |bestKept − baseline| / MAD. Displayed as `≥2.0× green / 1.0–2.0× yellow / <1.0× red`, computed after EVERY log (`updateStateAfterLog` :317–322 sets `experiment.confidence = state.confidence`) so each JSONL row carries the score at log time for post-hoc analysis.
**Invariant:** ADVISORY ONLY — nothing reads confidence to block a keep, revert, or stop; low confidence just changes message text ("Consider re-running to confirm") and widget color. Crashes contribute NOTHING (metric 0 filtered out, not counted toward the 3 minimum). Segment boundaries ignored intentionally: noise floor pools across re-inits (test 'considers all results (no segment filtering)'). `bestKept === baseline` uses strict equality — a kept run at exactly the baseline value yields null, not 0×.
**Probe:** direct test `extensions/pi-autoresearch/__tests__/unit/utils.test.ts` describe('computeConfidence') :243–338 pins all five null gates plus lower(≈4.0)/higher(≈2.0) calculations and crash filtering; anchor `grep -rn 'function computeConfidence' harness/server.ts extensions/pi-autoresearch/src/utils/stats.ts` → both copies (:169, stats.ts:28).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "computeConfidence sortedMedian deviations bestKept", limit: 10 });
```

## Verdict
Adopt the formula and all five null gates verbatim (MAD choice is load-bearing: robust to outlier crashes that std-dev would inflate); adapt thresholds/colors to host UI conventions; omit pi widget plumbing. Direct tests exist for the stats.ts copy only — keep the server copy byte-equal when porting.
