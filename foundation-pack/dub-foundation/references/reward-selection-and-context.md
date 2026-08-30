<!-- capsule-v2 -->
# Reward selection & context enrichment — how is a partner's per-event reward chosen and what context do modifiers see?

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** Which reward row applies to an event, and exactly which fields are folded into the condition context before modifiers evaluate?

## Event-column mapping & partner context assembly
**Path/Symbol:** `apps/web/lib/partners/determine-partner-reward.ts:determinePartnerReward` (:36-106) + `apps/web/lib/partners/aggregate-partner-links-stats.ts:aggregatePartnerLinksStats` (:11-39).
**Signature:** `determinePartnerReward({ event: EventType, programEnrollment: ProgramEnrollmentWithReward, context?: RewardContext }): Promise<Reward | null>` (sync fn returning `Reward | null`).
**Data Shape:** `programEnrollment` carries `partner.country`, `links`, `totalCommissions` (number|bigint), and optional `clickReward`/`leadReward`/`saleReward` Reward rows; `REWARD_EVENT_COLUMN_MAPPING` (:13-17) maps click→clickReward, lead→leadReward, sale→saleReward (referral absent — referral rewards never flow through this function).

### Decisive source
```ts
let partnerReward: Reward =
  programEnrollment[REWARD_EVENT_COLUMN_MAPPING[event]];

if (!partnerReward) {
  return null;
}

// Add the links metrics to the context
const partnerLinksStats = aggregatePartnerLinksStats(programEnrollment.links);

context = {
  ...context,
  partner: {
    ...context?.partner,
    ...partnerLinksStats,
    totalCommissions: toCentsNumber(programEnrollment.totalCommissions),
    country: programEnrollment.partner?.country,
  },
};
```
(determine-partner-reward.ts :45-63)

**Flow:** map event→reward column → missing reward ⇒ early `null` → aggregate link stats (clicks/leads/conversions/sales summed; saleAmount through `toCentsNumber`) → MERGE into `context.partner` (caller context spread first, stats overwrite) → proceed to modifier evaluation → `getRewardAmount(serializeReward(...)) === 0` ⇒ `null` → else `RewardSchema.parse(partnerReward)` exit.
**Invariant:** the caller-supplied `context.partner` fields are spread BEFORE the computed stats so aggregated link metrics and cents-normalized commissions always win over any caller-provided values; `toCentsNumber` accepts number|bigint|null|undefined (null⇒0) because Prisma returns bigint after the cents migration — porting with plain `Number()` throws on bigint rows.
**Probe:** deterministic probes (repo root): `grep -n 'REWARD_EVENT_COLUMN_MAPPING' apps/web/lib/partners/determine-partner-reward.ts` → :13 and :46; `grep -c 'totalConversions' apps/web/lib/partners/aggregate-partner-links-stats.ts` → 3; `cat packages/utils/src/functions/to-cents-number.ts` contains `typeof value === "bigint" ? Number(value) : value`. Direct tests: `apps/web/tests/rewards/{click,lead,sale}-reward.test.ts` exercise this selection end-to-end (runner offline-blocked, standing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "aggregatePartnerLinksStats", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the event→column map, missing-reward early null, computed-stats-wins context merge, and bigint-safe cents normalization. Adapt RewardContext fields to host domain. Omit the trailing `console.log("Reward context", prettyPrint(context))` debug emission (:180) — strip it when porting.
