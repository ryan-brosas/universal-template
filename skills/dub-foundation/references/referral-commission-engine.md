<!-- capsule-v2 -->
# Referral commission engine — how do you reward a referrer for a referee's sale/commission/approval/threshold exactly once, keyed by what?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the idempotency key and the trigger taxonomy for partner-referral commissions, and which gates run BEFORE any money is computed?

## createReferralCommission: dual-entry context resolution → trigger ladder → invoiceId dedup
**Path/Symbol:** `apps/web/lib/partner-referrals/create-referral-commission.ts:createReferralCommission` (:18-312); network fallback `apps/web/lib/partner-referrals/create-network-referral-commission.ts` (:21-262); dispatch queue `apps/web/app/(ee)/api/cron/commissions/referrals/queue/route.ts:POST` (:17-160+).
**Signature:** `createReferralCommission({sourceCommissionId} | {partnerId, programId})` — discriminated union, never both; returns null for EVERY skip (callers log "skipped").
**Data Shape:** referralReward.config parsed by `referralRewardConfigSchema`; triggers = percentage(`saleRecorded`,`commissionEarned`) vs flat(`partnerApproved`,`commissionThreshold`) (`apps/web/lib/partner-referrals/constants.ts:1-30`); synthetic invoiceIds `` `referral:${trigger}:${sourceCommission.id|partnerId}` `` (:150,:159,:188).

### Decisive source
```ts
if (trigger === "commissionEarned")
  commissionData.earnings = Math.floor((sourceCommission.earnings * amountInPercentage) / 100);
else if (trigger === "saleRecorded")
  commissionData.earnings = Math.floor((sourceCommission.amount * amountInPercentage) / 100);
...
if (monthsSinceFirstCommission >= referralReward.maxDuration) return null;   // recurring window
...
const existingCommission = await prisma.commission.findUnique({
  where: { invoiceId_programId: { invoiceId: commissionData.invoiceId, programId } } });
if (existingCommission) return null;
...
if (error.code === "P2002") return null;   // race between dedup check and create
```
(:135-150,:126,:206-246)

**Flow:** resolve context (by source commission — must be type=sale, status ∈ pending/processed/paid, and carry `programEnrollment.applicationEvent.referredByPartnerId`; or by approved enrollment) → self-referral + NETWORK_PROGRAM_ID guards → referrer's per-enrollment referralReward must exist with a VALID config → compute earnings per trigger: percentages floor-divide off source earnings or sale amount; maxDuration recurrence window measured in months since the REFEREE'S FIRST commission ever; partnerApproved/commissionThreshold pay flat cents (threshold checks SUM of the referee's sale-type earnings ≥ threshold) → earnings===0 ⇒ skip → findUnique on `(invoiceId,programId)` then create with P2002-as-dedup catch → allSettled(webhook `commission.created`, partner postback, syncTotalCommissions, notify). The payout-driven QUEUE route only enqueues after payout status ∈ {sent,completed}, fans out one job PER SALE COMMISSION (dedup by commission id) but ONE job per payout for threshold triggers; partners without a program-level referrer fall through to the NETWORK bonus (50% of dub's 3% fee share, own `referral:network:${payout.id}` key).
**Invariant:** (1) idempotency rides the SAME unique `(invoiceId, programId)` constraint as ordinary sales, using synthetic `referral:`-prefixed ids so replayed jobs can never double-pay regardless of check-then-create races; (2) percentage math floors to whole cents and zero-earnings rows are skipped rather than recorded; (3) every refusal path returns null — throwing would fail an otherwise-idempotent QStash job forever.
**Probe:** deterministic probe: `grep -c "invoiceId: .referral:" apps/web/lib/partner-referrals/create-referral-commission.ts` = 3; `grep -n "error.code === \"P2002\"" apps/web/lib/partner-referrals/create-referral-commission.ts` = :241. No upstream unit suite covers this file (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "createReferralCommission", limit: 5 });
```

## Verdict
Adopt the synthetic-id idempotency scheme and the four-trigger taxonomy verbatim for referral-style rewards. Adapt trigger names, recurrence windows, and the network-level fee-share fallback (dub-specific). Omit swag-threshold constants unless you ship physical rewards.
