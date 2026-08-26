<!-- capsule-v2 -->
# Usage-ranked credential selection & drain-urgency comparator — in what order does a multi-account pool get tried?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT; Codebase Memory `oh-my-pi`. **Question:** What is the exact sort order of usage-ranked candidates, and why is "drain rate" descending before used-fraction ascending?

## Usage-ranked credential selection & drain-urgency comparator
**Path/Symbol:** `packages/ai/src/auth-storage.ts:` `AuthStorage.#compareUsageRankedCandidatePriority` (4597–4639) + `#computeWindowRequiredDrain` (4582–4595) + `PRIMARY_WINDOW_HOT_FRACTION = 0.85` (:85).
**Signature:** `#compareUsageRankedCandidatePriority(left, right, planRequirement): number`; drain = `headroom / max(remainingMs, 60_000)/3_600_000`.
**Data Shape:** Each candidate carries `{blocked, blockedUntil?, hasPriorityBoost, planPriority, secondaryUsed/RequiredDrain, primaryUsed/RequiredDrain, orderPos}`; window fractions default to 0.5 when unparseable (`#normalizeUsageFraction`).

### Decisive source
```ts
if (left.blocked !== right.blocked) return left.blocked ? 1 : -1;
if (left.blocked && right.blocked) {
	const leftBlockedUntil = left.blockedUntil ?? Number.POSITIVE_INFINITY;
	const rightBlockedUntil = right.blockedUntil ?? Number.POSITIVE_INFINITY;
	if (leftBlockedUntil !== rightBlockedUntil) return leftBlockedUntil - rightBlockedUntil;
	return 0;
}
if (planRequirement !== "none" && left.planPriority !== right.planPriority) {
	return left.planPriority - right.planPriority;
}
if (left.hasPriorityBoost !== right.hasPriorityBoost) return left.hasPriorityBoost ? -1 : 1;
const leftHot = left.primaryUsed >= PRIMARY_WINDOW_HOT_FRACTION;   // 0.85
const rightHot = right.primaryUsed >= PRIMARY_WINDOW_HOT_FRACTION;
if (leftHot !== rightHot) return leftHot ? 1 : -1;                 // hot short-window demotes
const leftMeasured = left.usage !== null;
const rightMeasured = right.usage !== null;
if (leftMeasured !== rightMeasured) return leftMeasured ? -1 : 1;  // measured beats unmeasured
metric = compareUsageRankingMetric(right.secondaryRequiredDrain, left.secondaryRequiredDrain); // DESC
metric = compareUsageRankingMetric(left.secondaryUsed, right.secondaryUsed);                   // ASC
metric = compareUsageRankingMetric(right.primaryRequiredDrain, left.primaryRequiredDrain);     // DESC
metric = compareUsageRankingMetric(left.primaryUsed, right.primaryUsed);                       // ASC
```

**Flow:** selection prefetches usage reports in parallel with an unref'd timeout (`Math.max(5000, timeout*1.5)`); on timeout every candidate is treated as unmeasured-but-unblocked rather than failing the resolve. Comparator runs blocked → plan → boost → hot-guard → measured-guard → secondary-drain → secondary-used → primary-drain → primary-used, ties falling back to `orderPos`.
**Invariant:** Drain-DESC precedes used-ASC because the goal is ~100% utilization across staggered resets — quota that would expire unused ranks first ("use it or lose it", :4574–4580). The 0.85 hot-guard overrides drain urgency: a nearly-exhausted 5h window means imminent mid-session block (:80–84 comment). Measured-beats-unmeasured exists because clockless headroom fallback is NOT comparable with drain scores (:4619–4622). Float compares use epsilon+relative tolerance (:1091–1097).
**Probe:** `packages/ai/test/auth-storage-codex-selection.test.ts` — `prefers near-reset weekly account over lower-used far-reset account` (:285), `weights 3 accounts by weekly drain rate` (:2227), `times out slow usage ranking instead of blocking first account selection` (:2189); claude twin at :2796+, `assumes the full duration remains when ranking clockless windows` (:2868).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "compareUsageRankedCandidatePriority", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt comparator ORDER as a unit and the drain formula incl. the 60s floor; adapt provider strategies (window mapping) to host; omit Codex plan-priority tier unless porting plan-gated models. Reordering the comparator (used-before-drain, or dropping the hot-guard) silently strands headroom.
