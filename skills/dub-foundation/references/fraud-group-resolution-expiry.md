<!-- capsule-v2 -->
# Fraud group resolution & expiry lifecycle — resolve action plumbing, the 30-day expiry sweeper, and why network-level bans never expire

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How do groups leave `pending` (human resolve vs cron expiry), which types are immortal, and what side effects ride each exit?

## Shared release trigger: BOTH exits call queueReleaseHoldCommissions
**Path/Symbol:** `apps/web/lib/api/fraud/resolve-fraud-groups.ts:resolveFraudGroups` (:6-55) + `apps/web/lib/actions/fraud/resolve-fraud-group.ts:resolveFraudGroupAction` (:11-81) + `apps/web/app/(ee)/api/cron/cleanup/expired-fraud-groups/route.ts` (:19-71).
**Signature:** `async function resolveFraudGroups({ where, userId?, resolutionReason?, releaseHoldCommissions? }): Promise<number>`; expiry route = `withCron(async () => …)` batch loop.
**Data Shape:** status enum `{pending, resolved, expired}` (prisma/schema/fraud.prisma :1-5); expiry predicate `status:"pending" AND type NOT IN NON_EXPIRING_FRAUD_RULE_TYPES AND lastEventAt < now−30d`, BATCH_SIZE=250; `NON_EXPIRING_FRAUD_RULE_TYPES = [partnerCrossProgramBan]` (constants.ts :282-284); `FRAUD_GROUP_EXPIRY_DAYS = 30`.

### Decisive source
```ts
// resolve: guarded transition + attribution
const { count } = await prisma.fraudEventGroup.updateMany({
  where: { id: { in: riskGroupIds }, status: pending },     // re-guard inside update
  data: { userId, resolutionReason, resolvedAt: new Date(), status: resolved } });
if (releaseHoldCommissions && count > 0) await queueReleaseHoldCommissions(riskGroupIds);

// expire: daily 02:30 UTC cron, page-by-page
while (true) {
  const groupsToExpire = await prisma.fraudEventGroup.findMany({
    where: { status: "pending", type: { notIn: NON_EXPIRING_FRAUD_RULE_TYPES },
             lastEventAt: { lt: subDays(new Date(), FRAUD_GROUP_EXPIRY_DAYS) } },
    take: BATCH_SIZE });
  if (groupsToExpire.length === 0) break;
  ... updateMany pending→expired ... if (count > 0) await queueReleaseHoldCommissions(groupIds);
  if (groupsToExpire.length < BATCH_SIZE) break; }
```
(resolve-fraud-groups.ts :33-52 / expired-fraud-groups/route.ts :21-66 condensed)

**Flow:** human path — server action enforces role owner/member + plan capability (`canManageFraudEvents`: enterprise/advanced only), verifies group belongs to the workspace's default program, resolves via shared fn, writes a partnerComment with the resolution reason, optionally stamps `riskMonitoringDisabledAt` on the enrollment (kill-switch for this partner's future detection). Cron path — pages stale pendings to `expired` and queues holds-release per batch. Both paths converge on the SAME queue fn (see fraud-hold-release-ladder).
**Invariant:** (1) `lastEventAt` is the freshness clock — any new event refreshes it, so active groups never expire mid-investigation; (2) cross-program bans are IMMORTAL by list membership: they represent another program's confirmed judgment and must not silently self-heal after 30 days; (3) both transitions RE-GUARD `status: pending` in the update where, so a concurrent human+expiry race resolves exactly one winner; (4) expiry releases holds too — money is never frozen behind a case nobody is investigating; (5) resolution without `releaseHoldCommissions` flag (used by some admin flows) leaves holds untouched.
**Probe:** anchored at dub repo root: `grep -c 'FRAUD_GROUP_EXPIRY_DAYS = 30' apps/web/lib/api/fraud/constants.ts` = **1**; `grep -o 'NON_EXPIRING_FRAUD_RULE_TYPES' 'apps/web/app/(ee)/api/cron/cleanup/expired-fraud-groups/route.ts' | wc -l` = **3**; `grep -c 'BATCH_SIZE = 250' 'apps/web/app/(ee)/api/cron/cleanup/expired-fraud-groups/route.ts'` = **1**; `grep -c 'partnerComment.create' apps/web/lib/actions/fraud/resolve-fraud-group.ts` = **1**; `grep -o 'canManageFraudEvents' apps/web/lib/actions/fraud/resolve-fraud-group.ts | wc -l` = **2**. Direct tests: none isolated (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "resolveFraudGroups", limit: 5 });
```

## Verdict
Adopt the dual-exit lifecycle converging on one release trigger, the lastEventAt-refreshed expiry clock, and the immortal-ban carve-out. Adapt expiry window and plan gating. Omit the specific cron schedule comment.
