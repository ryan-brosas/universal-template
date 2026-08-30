<!-- capsule-v2 -->
# Density-estimator calibration — how do you learn real token-per-char density from provider usage without chasing your own corrections?

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** When your chars/4 token estimate under-reports (CJK under-reports ~20–40%), what is the contract for learning a per-model correction factor from provider-reported usage?

## Cumulative-anchor sampling with confirmation gating
**Path/Symbol:** `src/density.ts` whole (127L): constants (:19-23), `Estimator` state (:25-32), `DensityEstimator.resetModel`/`densityFor`/`update`/`estimateWithDensity` (:34-123); injection point `src/runtime.ts`:242-247 (`countTokens: (text) => density.estimateWithDensity(countModelId, text)`); consumption `src/tokens.ts`:27 (`calibrateTokens`) at `src/index.ts`:201.
**Signature:** `update(modelId: string, realTotal: number | null, estTotal: number, postCompression = false): void`; `estimateWithDensity(modelId, text): number`.
**Data Shape:** per-model `Estimator { density, anchorReal, anchorEst, pendingDensity, confirmCount, postCompressionSkip }`, keyed in a Map; unknown model → density 1.
### Decisive source
```ts
// density.ts:92-114 — the sampling loop. Anchor advances EVERY accepted sample
// (instant = adjacent-round delta; a single anomaly pollutes one round, not
// the estimate), but adoption needs TWO consecutive rounds within ±20%:
const dReal = realTotal - est.anchorReal;
const dEst = estTotal - est.anchorEst;
if (dEst < MIN_DELTA_EST) return;        // 50-token floor: micro-message ratio jitter
est.anchorReal = realTotal; est.anchorEst = estTotal;
const instant = clamp(dReal / dEst, DENSITY_MIN, DENSITY_MAX);   // [0.5, 2.5]
if (est.pendingDensity === null) { est.pendingDensity = instant; est.confirmCount = 1; }
else if (Math.abs(instant - est.pendingDensity) / est.pendingDensity <= CONFIRM_RATIO) {
  est.confirmCount += 1;                 // ±20% band, CONFIRM_RATIO = 0.2
} else { est.pendingDensity = instant; est.confirmCount = 1; }
if (est.confirmCount >= 2) { est.density = est.pendingDensity; ... }
```
**Flow:** every context event calls `density.update(modelId, realUsage?.tokens ?? null, sentTokens, postCompression)` AFTER processTurn/save (`index.ts`:244). `realTotal === null` freezes anchors (no provider usage ⇒ no sample). First round with both sides establishes the anchor without producing a sample. Post-compression round sets `postCompressionSkip` and returns; the NEXT round re-anchors on the clean post-compression basis — the comment explains why the re-anchor happens one round LATE: the compression round's own usage may still reflect pre-compression size, and re-anchoring on that round would leave the pre-compression anchor blocking resampling until estimates regrow past it (long dead zone) plus a clamped first-crossing outlier. Injection is dual-path: kernel countTokens gets `estimateWithDensity` (skips rounding entirely when density===1 to avoid float error), while nudge/emergency arbitration gets `calibrateTokens(sentTokens, density)` over the RAW chars/4 sent view.
**Invariant:** THE FEEDBACK TRAP — the estimator must always be fed the RAW uncalibrated estimate (`sentTokens` from `estimateTokens`), never its own calibrated output; "its samples must stay on the raw basis or density would chase its own calibration" (`index.ts`:194-200). Related traps: per-model isolation (switching models must not cross-contaminate densities); clamp bounds are load-bearing ("no natural language density can exceed 2.5 tokens/char"); one-round lag between calibration and use is explicitly accepted ("可忽略").
**Probe:** `cd /mnt/hdd/utopia/inspo/billion-context-pi && npx tsx --test tests/density.test.ts tests/density-usage-fixes.test.ts` — 18/18 GREEN at pin 6a88c556 (executed pass 12; anchor freeze on null usage, ±20% two-round confirmation, clamp bounds, postCompression skip+late re-anchor).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "DensityEstimator update calibrateTokens densityFor", limit: 10 });
```

## Verdict
Adopt cumulative-anchor sampling (not EMA — no lag), advance-per-sample with two-round ±20% confirmation, the min-delta floor, clamp [0.5, 2.5], per-model maps, and especially the post-compression late-re-anchor. Adapt the estimator source (provider usage shape) to your host. Omit nothing in the update() branch order — each early-return encodes a documented failure mode (frozen anchors, dead zones, self-chasing calibration).
