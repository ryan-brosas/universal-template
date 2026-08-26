<!-- capsule-v2 -->
# Hold-release ladder — partner-level groups veto everything, customer-level groups block only their customers, and releases fan out four side effects per batch

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** After a fraud group resolves, how does the system decide WHICH held commissions release — and why can a single remaining duplicate-account group freeze the whole partner?

## Two-tier blocking model + batched release with status-stamped side-effect rows
**Path/Symbol:** `apps/web/lib/api/fraud/release-hold-commissions.ts:releaseHoldCommissions` (:35-237) + `queueReleaseHoldCommissions` (:241-301).
**Signature:** `async function releaseHoldCommissions({ programId, partnerId, resolvedGroupIds }): Promise<number /* totalReleased */>`; queue fn takes group ids ALREADY resolved/expired.
**Data Shape:** blocking sets from `PARTNER_LEVEL_FRAUD_RULES` / `CUSTOMER_LEVEL_FRAUD_RULES` (constants.ts :294-304); release where = `{programId, partnerId, status: hold}` optionally `OR [customerId: null, customerId: {notIn: blocked}]`.

### Decisive source
```ts
const otherPendingGroups = await prisma.fraudEventGroup.findMany({
  where: { programId, partnerId, status: pending, id: { notIn: resolvedGroupIds } },
  select: { type: true, fraudEvents: { select: { customerId: true } } } });
if (otherPendingGroups.some((g) => PARTNER_LEVEL_FRAUD_RULES.includes(g.type))) return 0; // FULL VETO
const blockedCustomerIds = new Set(otherPendingGroups
  .filter((g) => CUSTOMER_LEVEL_FRAUD_RULES.includes(g.type))
  .flatMap((g) => g.fraudEvents.map((e) => e.customerId).filter(Boolean)));
if (blockedCustomerIds.size > 0)
  releaseWhere.OR = [{ customerId: null },   // custom commissions always release
                      { customerId: { notIn: [...blockedCustomerIds] } }];
// batch loop: take 250 → updateMany hold→pending → refetch released rows and RE-STAMP hold for the log
.then((commissions) => commissions.map((c) => ({ ...c, status: CommissionStatus.hold })))
await Promise.allSettled([ trackCommissionStatusUpdate(...newStatus: pending),
  syncTotalCommissions({ partnerId, programId }),
  triggerAggregateDueCommissionsCronJob(programId),
  releasedEarnings > 0 && executeWorkflows({ event: "commissionRecorded", metrics: { current: { commissions: releasedEarnings } } }) ]);
```
(release-hold-commissions.ts :49-218 condensed)

**Flow:** empty ids ⇒ 0 → survey OTHER pending groups → partner-level survivor ⇒ veto → else build customer blocklist → program fetch for workspaceId → while-loop batches of PRISMA_UPDATEMANY_LIMIT → conditional re-fetch when partial (re-stamping old `hold` status so the activity log reads hold→pending, comment :180) → four-fan-out per batch → return accumulated count. **Queue path:** resolve/expire callers hand group ids; queue fn filters to actually resolved/expired, folds into ONE QStash job per (program,partner) via `qstash.batchJSON` to `/api/cron/fraud/release-hold-commissions`.
**Invariant:** (1) hierarchy: partner-level beats customer-level — any live duplicate/ban group keeps EVERYTHING held regardless of resolved siblings; (2) `customerId: null` commissions (manual adjustments) bypass customer blocks BY DESIGN; (3) released rows feed workflows only when earnings sum > 0 and the workflow payload carries the BATCH's summed earnings as `commissionRecorded` metric; (4) every side effect is allSettled — a webhook/workflow failure never loses the status flip already committed; (5) queue dedupes to one job per pair so multi-group resolution triggers exactly one release pass.
**Probe:** anchored at dub repo root: `grep -c 'notIn: resolvedGroupIds' apps/web/lib/api/fraud/release-hold-commissions.ts` = **1**; `grep -c 'customerId: null' apps/web/lib/api/fraud/release-hold-commissions.ts` = **1**; `grep -o 'APP_DOMAIN_WITH_NGROK' apps/web/lib/api/fraud/release-hold-commissions.ts | wc -l` = **2** (import + URL); `grep -c 'releasedEarnings > 0' apps/web/lib/api/fraud/release-hold-commissions.ts` = **1**; `grep -c 'batchJSON' apps/web/lib/api/fraud/release-hold-commissions.ts` = **1**. Direct tests: none isolated (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "releaseHoldCommissions", limit: 5 });
```

## Verdict
Adopt the two-tier blocking model and the release fan-out quartet. Adapt which rule types are partner- vs customer-scoped. Omit the ngrok-domain escape hatch (dev-only); keep one-job-per-pair queue folding.
