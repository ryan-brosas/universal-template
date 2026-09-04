<!-- capsule-v2 -->
# Payout backfill on attribution — how do you retroactively reward a referrer for events that happened BEFORE they were attributed?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What does the referrals/backfill cron enqueue for each trigger type, and how is replay suppressed?

## cron/commissions/referrals/backfill route
**Path/Symbol:** `apps/web/app/(ee)/api/cron/commissions/referrals/backfill/route.ts:POST` (:17-140); triggered by attributeReferringPartnerAction when `createCommissionsForPastEvents` (:138-165).
**Signature:** input `{programId, partnerId}`; per-job dedup `create-referral-commissions-${programId}-${partnerId}` (flat) or `-${commission.id}` (percentage).
**Data Shape:** eligible source commissions = type sale ∧ status ∈ pending|processed|paid; percentage triggers chunk 50.

### Decisive source
```ts
if (["commissionThreshold", "partnerApproved"].includes(trigger)) {
  await enqueueBatchJobs([{ deduplicationId: `create-referral-commissions-${programId}-${partnerId}`,
    body: { programId, partnerId } }]);
  return logAndRespond(`Enqueued 1 referral commission job ...`);
}
if (["saleRecorded", "commissionEarned"].includes(trigger)) {
  const commissions = await prisma.commission.findMany({ where: { programId, partnerId,
    type: CommissionType.sale, status: { in: ["pending", "processed", "paid"] } }, select: { id: true } });
  for (const commissionChunk of chunk(commissions, 50))
    await enqueueBatchJobs(commissionChunk.map((commission) => ({ ... body: { sourceCommissionId: commission.id } })));
```
(:70-120)

**Flow:** re-verify the applicationEvent + referrer's reward (state may have changed since the action) → dispatch by trigger family exactly as the payout-driven queue does → the create worker's `(invoiceId,programId)` dedup makes double-backfills harmless even if the cron itself re-runs.
**Invariant:** (1) backfill RE-VALIDATES everything rather than trusting the action's snapshot; (2) idempotency rides the same synthetic-invoiceId unique constraint — no separate backfill ledger needed.
**Probe:** deterministic probe: `grep -n 'chunk(commissions, 50)' 'apps/web/app/(ee)/api/cron/commissions/referrals/backfill/route.ts'` = :114. No upstream unit suite covers this route directly (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "referrals/backfill", limit: 5 });
```

## Verdict
Adopt re-validating backfill through the same idempotent workers. Adapt trigger families. Omit if attribution is always pre-registration.
