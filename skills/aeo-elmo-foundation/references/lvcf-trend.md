<!-- capsule-v2 -->
# LVCF share trend — how do staggered prompt schedules stop creating fake dips?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How should a brand-level SoV time series aggregate prompts that run on different days?

## Per-prompt last-value-carried-forward, pre-seeded
**Path/Symbol:** `apps/web/src/lib/visibility-stats.ts:shareOfVoiceTimeSeriesLVCF` (L177–215), `shareOfVoiceLeaderboardLVCF` (L232–293).
**Signature:** `shareOfVoiceTimeSeriesLVCF(perPrompt: PerPromptDailyMentions[], dateRange: string[]): {date, share: number|null}[]`.
**Data Shape:** per prompt, sort observations chronologically; seed `carried` with the EARLIEST observation (pre-seed kills the ramp-up dip); walk the full dateRange carrying forward on days the prompt didn't run; sum brand/competitor across prompts per day; `share = round(brand/(brand+competitor) × 100)`, null denominator → null.

### Decisive source
```ts
let carried = sorted.length > 0 ? sorted[0][1] : null;
for (const date of dateRange) {
	const actual = dateMap.get(date);
	if (actual) carried = actual;
	if (!carried) continue;
	bucket.brand += carried.brand; bucket.competitor += carried.competitor;
}
```

**Flow:** the leaderboard twin carries each prompt's most recent observation to the LAST day only, then sums — deliberately the same LVCF semantics so the headline/donut/table agree with the trend line's final point ("rather than a whole-window aggregate that wouldn't match it").
**Invariant:** carry-forward is PER-PROMPT, never per-brand-aggregate: aggregating raw daily rows would weight a 4×/day prompt four times a slow prompt. Share stays null (not 0) when no data.
**Probe:** `apps/web/src/lib/visibility-stats.test.ts` (trend + leaderboard consistency cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "shareOfVoiceTimeSeriesLVCF shareOfVoiceLeaderboardLVCF carried", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-entity LVCF with pre-seeding for any metric aggregated over independently-sampled sources; adapt to your cadence mix; omit the leaderboard twin if you have no current-standings view (but then expect the mismatch it exists to prevent).
