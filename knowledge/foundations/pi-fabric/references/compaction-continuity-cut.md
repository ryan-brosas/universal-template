<!-- capsule-v2 -->
# Continuity-tail compaction budget — how do you pick a cut point that never orphans a tool_result, under a calibrated post-compaction token target?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** given raw message tokens and provider-reported usage, how is the "keep recent" tail sized and where exactly may the cut land?

## Four-constraint min + closure-safe boundary walk
**Path/Symbol:** `src/compaction/hook.ts:continuityCutPlan` (:337-395), `tokenCalibration` (:301-335), `computeContinuityCut` (:426+), `callResultSpans`/`spanCrosses`/`closureSafe` (:222-243), `closeCut` (:245-261); constants :103-110.
**Signature:** `continuityCutPlan(branchEntries, tokensBefore, budget: {contextWindow; targetContextRatio; reserveTokens; keepRecentTokens}): ContinuityCutPlan | undefined`; `CutResult = {ok: true; summarized; firstKeptEntryId; …} | {ok: false; reason: "empty"}`.
**Data Shape:** plan = `{strategy:"continuity", targetContextTokens, bindingConstraint: "continuity"|"occupancy"|"reserve"|"reduction", tokenScale, fixedOverheadTokens, rawTailTokenBudget, …}`.

### Decisive source
```ts
const SUMMARY_RAW_TOKEN_BUDGET = Math.ceil(MAX_SUMMARY_BYTES / 4);   // 32KB summary ≈ 8k tokens
// Fit an upper affine envelope: context ≈ fixed overhead + scale × raw messages.
const tokenScale = Math.max(1, ...slopes);
const fixedOverheadTokens = Math.max(0, tokensBefore - tokenScale * rawTokensBefore,
  ...checkpoints.map((c) => c.contextTokens - tokenScale * c.rawTokens));
const constraints = [
  { binding: "continuity", tokens: continuityTargetTokens },  // keepRecent + summary, scaled
  { binding: "occupancy",  tokens: occupancyCeilingTokens },  // window × ratio (clamped .25–.85)
  { binding: "reserve",    tokens: safeCeilingTokens },       // (window − reserve) × 0.9 safety
  { binding: "reduction", tokens: reductionCeilingTokens },  // ≤ 0.95 × pre-compaction size
];
const targetContextTokens = Math.min(...constraints.map(c => c.tokens));
const bindingConstraint = constraints.find(c => c.tokens === targetContextTokens)!.binding;
```
```ts
// Cut walks FORWARD from the oldest legal turn boundary; a candidate boundary
// is illegal while ANY tool call/result pair spans it:
if (!item.cutPoint || suffixTokens[index] > plan.rawTailTokenBudget) continue;
if (!closureSafe(spans, item.branchIndex)) continue;
```

**Flow:** estimate raw tokens of the live branch (post-last-compaction) → calibrate an affine context≈fixed+scale×raw envelope from assistant-message usage checkpoints (only comparable pre-marker checkpoints with ≥4k raw delta; fallback scale=1) → compute the four ceilings and take the minimum, recording WHICH constraint binds → choose the largest raw suffix whose first kept entry is a cut point (non-toolResult role start) within `rawTailTokenBudget` that no call/result span crosses → if none, `closeCut` walks back to earlier boundaries; overflow recovery clamps the window to 0.9 × the observed failing request size because a provider rejection proves the real window is smaller.
**Invariant:** a cut may NEVER split a tool_call/tool_result pair — span closure dominates the budget (the tail simply shrinks until safe); the projected result must be strictly smaller than the input (`reduction` ceiling ≤95%) so compaction can't loop without progress; all budgets are computed from calibrated estimates, never advertised windows alone.
**Probe:** `tests/compaction.test.ts:956` describe ("compaction cut never orphans a tool_result from its tool_call"), `:1010` ("pushes the cut back when the last turn is in flight"), `:1059` ("closes parallel delayed pairs in both call/result directions"), `:1086`/:1112`/:1232` (continuity-tail retention + largest-legal-suffix selection), `:1274` ("clamps an overflow recovery cut to the observed failing request size"), `:1314` ("cancels rather than expanding when even compact-all cannot fit").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "continuityCutPlan tokenCalibration closureSafe callResultSpans bindingConstraint rawTailTokenBudget", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the min-of-constraints target with named binding constraint, usage-calibrated affine scaling, and closure-safe cut walking; adapt ratios/constants to your tokenizer; omit pi session-entry plumbing.
