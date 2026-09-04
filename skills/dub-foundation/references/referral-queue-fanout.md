<!-- capsule-v2 -->
# Referral queue fan-out — how does a completed payout turn into per-commission referral jobs, and when is it ONE job instead of N?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What statuses gate referral creation, and how do threshold triggers differ from percentage triggers at enqueue time?

## cron/commissions/referrals/queue route
**Path/Symbol:** `apps/web/app/(ee)/api/cron/commissions/referrals/queue/route.ts:POST` (:17-160+); executor `create/route.ts` (z.union input mirroring the two body shapes).
**Signature:** input `{payoutId}`; jobs carry either `{sourceCommissionId}` per SALE commission or `{programId, partnerId}` for threshold; dedup ids `create-referral-commissions-${commission.id|payout.id}`.
**Data Shape:** payout gate = status ∈ {sent, completed} ∧ programId ≠ NETWORK_PROGRAM_ID; sale-type commissions only.

### Decisive source
```ts
if (!["sent", "completed"].includes(payout.status))
  return logAndRespond(`Payout ${payoutId} is not in a valid status to create referrals.`);
...
if (trigger === "commissionThreshold") {
  await enqueueBatchJobs([{ ... deduplicationId: `create-referral-commissions-${payout.id}`,
    body: { programId, partnerId: partner.id } }]);
  return logAndRespond(`Enqueued referral-eligible payout ${payout.id}.`);
}
await enqueueBatchJobs(commissions.map((commission) => ({ ...
  deduplicationId: `create-referral-commissions-${commission.id}`,
  body: { sourceCommissionId: commission.id } })));
```
(:60-136)

**Flow:** load payout with commissions(sale-only), enrollment applicationEvent, invoice → gates → program-level referrer found ⇒ read their referralReward → threshold ⇒ ONE idempotent job (the aggregate check runs inside create); otherwise ONE job PER sale commission → no program-level referrer ⇒ fall through to network-level bonus (`createNetworkReferralCommission` inline, keyed `referral:network:${payout.id}`).
**Invariant:** (1) referrals fire only AFTER money actually moved (sent/completed) — a refunded processing payout never spawns rewards; (2) dedup keys mirror the trigger granularity so QStash suppresses replays regardless of which side re-sends; (3) threshold aggregation happens in the WORKER not the enqueuer, keeping enqueue cheap and replay-safe.
**Probe:** deterministic probe: `grep -c 'deduplicationId' 'apps/web/app/(ee)/api/cron/commissions/referrals/queue/route.ts'` = 2; `grep -n '"sent", "completed"' 'apps/web/app/(ee)/api/cron/commissions/referrals/queue/route.ts'` = :60. No upstream unit suite covers this route directly (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "create-referral-commissions", limit: 5 });
```

## Verdict
Adopt status-gated, granularity-matched job fan-out. Adapt status names. Omit network-bonus fallback unless you run a platform-wide program.
