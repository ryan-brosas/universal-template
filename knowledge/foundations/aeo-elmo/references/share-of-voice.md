<!-- capsule-v2 -->
# Share-of-Voice math — how do you turn mention booleans into comparable percentages?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** What are the exact SoV definitions and their zero/rounding rules?

## brand / (brand + competitors), rounded once
**Path/Symbol:** `packages/lib/src/report-metrics.ts:computePromptSoV` (L51–90), `computeOverallSoV` (L96–114), `computeCompetitorSoVs` (L119–148), `computeReportUnstableStats` (L444–510).
**Signature:** `computePromptSoV(promptId, runs, competitors): PromptSoV` (sov `number | null`); `computeOverallSoV(runs, competitors): number | null`.
**Data Shape:** competitor mentions only count when they appear in the tracked `competitors` list (name equality) — stray names never dilute the denominator. Prompt-level and overall SoV round to integer percent; `computeReportUnstableStats` deliberately does NOT pre-round (`sov: number|null` 0–1 float).

### Decisive source
```ts
const denominator = brandMentionCount + totalCompetitorMentions;
const sov = denominator === 0 ? null : Math.round((brandMentionCount / denominator) * 100);
// Avoid an intermediate integer percentage so small shares are not rounded away.
const sov = totalAllMentions === 0 ? null : brandMentionCount / totalAllMentions;   // unstable-stats variant
```

**Flow:** per-prompt rows filter by `promptId`; a run with zero mentions of anyone yields `sov: null` (not 0) — null means "no data", 0 means "competitors only". Visibility is the companion metric: `brandMentionCount / totalPromptRuns`.
**Invariant:** null ≠ 0. UI ladders (`getSoVLevel`: ≥40 Strong / ≥20 Moderate / else Low, null → "No Data") all branch on null first. Double-rounding is called out as a bug class: share ratios stay exact until the display layer rounds once so table/donut/trend cannot disagree by a point.
**Probe:** `packages/lib/src/report-metrics.test.ts` — 20+ cases pinning null-on-empty, 100%-brand-only, ignores-competitors-not-in-list, per-prompt isolation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "computePromptSoV computeOverallSoV computeCompetitorSoVs computeReportUnstableStats", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the formulas and null-semantics exactly; adapt the color/badge thresholds to your product; omit nothing in the rounding discipline — "round once at display" is stated in-source because someone already hit that bug.
