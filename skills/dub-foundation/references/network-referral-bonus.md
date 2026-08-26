<!-- capsule-v2 -->
# Network referral bonus — how does dub reward a partner for RECRUITING another partner's earnings, computed from the platform fee rather than program revenue?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How is the referrer's bonus derived when there is no program-level referral reward, and what synthetic sale is recorded?

## createNetworkReferralCommission
**Path/Symbol:** `apps/web/lib/partner-referrals/create-network-referral-commission.ts:createNetworkReferralCommission` (:21-262); constants `apps/web/lib/partner-referrals/constants.ts:66-71` (NETWORK_REFERRAL_REWARD 50%, maxDuration 12).
**Signature:** `createNetworkReferralCommission({partner:{id,referredByPartnerId}, payout:{id,amount,programId}})`; skips NETWORK/ACME programs themselves.
**Data Shape:** bonus = `Math.floor(payout.amount * 0.03) * 50%` — "assumes 3% average payout fee for all payouts" (:50); synthetic customer row keyed by `projectId:NETWORK_WORKSPACE_ID, externalId:partner.id`; invoiceId `referral:network:${payout.id}`.

### Decisive source
```ts
const payoutFeeEarned = Math.floor(payout.amount * 0.03); // assumes 3% average payout fee for all payouts
...
const invoiceId = `referral:network:${payout.id}`;
if (customer?.link) {
  ... await Promise.allSettled([
    recordSale({ ...saleData, event_name: "Partner payout fee",
                 payment_processor: "dub", timestamp: undefined }), ...
```
(:50-120)

**Flow:** guards → estimate dub's fee share of THIS payout → find the REFERRER's enrollment in the network program (their saleReward drives percentage math downstream) → resolve the referee-partner-as-customer in the network workspace → record a synthetic Tinybird sale ("Partner payout fee") + commission so network dashboards show recruiting income; recurring window enforced via months-since-first-commission as in the program-level engine.
**Invariant:** (1) platform-fee bonuses are ESTIMATES by design (fixed 3% assumption) — never present them as exact ledger data; (2) the recruited partner becomes a CUSTOMER row in the network program — identity reuse across programs rides the externalId namespace, so porters must keep that namespace stable or bonuses orphan.
**Probe:** deterministic probe: `grep -n 'payout.amount \* 0.03' apps/web/lib/partner-referrals/create-network-referral-commission.ts` = :50; `grep -c 'referral:network:' apps/web/lib/partner-referrals/create-network-referral-commission.ts` = 1. No upstream unit suite covers this file directly (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "createNetworkReferralCommission", limit: 5 });
```

## Verdict
Adopt fee-share estimation with honest naming and customer-row recycling. Adapt rates. Omit entirely unless you operate a meta-program.
