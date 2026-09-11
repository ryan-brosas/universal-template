<!-- capsule-v2 -->
# Duplicate-account detector pair — Veriff-identity and payout-method cross-partner sweeps emitting the full directed pair set

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** When two partners share an identity or a payout method, which partners get flagged — and why does a program with exactly one matching partner stay clean?

## Shared skeleton: shared-key enrollment fan → multiplicity gate → all-directed-pairs event matrix
**Path/Symbol:** `apps/web/lib/api/fraud/detect-duplicate-identity-fraud.ts:detectDuplicateIdentityFraud` (:17-144) + `detect-duplicate-payout-method-fraud.ts:detectDuplicatePayoutMethodFraud` (:160-263).
**Signature:** identity: `({ veriffSessionId, riskLabels })`; payout: `({ payoutMethodHash } XOR { cryptoWalletAddress })` (TS `never` mutual exclusion :154-156).
**Data Shape:** both emit `CreateFraudEventInput[]` of type `partnerDuplicateAccount` with `metadata.duplicatePartnerId` = the OTHER partner (+ riskLabels / payout hash / wallet as available), then call `createFraudEvents(affectedGroups)` and hold via `Promise.allSettled([holdPendingCommissions, holdProcessedCommissions])`.

### Decisive source
```ts
// payout variant: partners sharing EITHER key, in ANY program
const programEnrollments = await prisma.programEnrollment.findMany({
  where: { partner: { OR: [ ...(payoutMethodHash ? [{ payoutMethodHash }] : []),
                           ...(cryptoWalletAddress ? [{ cryptoWalletAddress }] : []) ] } } });
// rule-disabled programs filtered via isFraudRuleEnabled(partnerDuplicateAccount)
// group by program; keep ONLY programs with >1 partner
partnersByProgram = new Map([...].filter(([_, partners]) => partners.length > 1));
for (const sourcePartner of partners)          // skip inactive / riskMonitoringDisabledAt
  for (const enrolledPartner of partners)      // includes SELF → self-referential row too
    fraudEvents.push({ programId, partnerId: sourcePartner.partnerId,
      type: "partnerDuplicateAccount", metadata: { ..., duplicatePartnerId: enrolledPartner.partnerId } });
```
(detect-duplicate-payout-method-fraud.ts :168-252 condensed; identity variant swaps the where-clause for `partner.veriffSessionId in [riskLabel sessionIds..., veriffSessionId]` deduped via Set)

**Flow:** collect shared-key enrollments (identity: Veriff decision webhook riskLabels carry their OWN sessionIds that get unioned with the current one) → filter programs where the partnerDuplicateAccount rule is disabled → per-program multiplicity gate (`length > 1`) → skip inactive/disabled-monitoring sources → push directed pairs → createFraudEvents → best-effort holds.
**Invariant:** (1) the pair loop is FULL n×n INCLUDING self (`source === enrolled` still pushes), so every member of a duplicate cluster gets its own event naming each counterpart — hash dedupe then collapses identical identities; (2) the `>1` gate means a LONE partner sharing a key with nobody in that specific program is untouched even if flagged elsewhere; (3) per-program rule-disable filters BEFORE grouping — disabled programs never appear in affectedGroups and thus never trigger commission holds; (4) holds ride allSettled with rejected-result logging (hold failure never fails detection); (5) payout-method variant accepts hash XOR wallet (typed `never`) — passing both or neither is a type error.
**Probe:** anchored at dub repo root: `grep -c 'veriffRiskLabels.includes' apps/web/lib/api/fraud/detect-duplicate-identity-fraud.ts` = **1**; `grep -c 'partners.length > 1' apps/web/lib/api/fraud/detect-duplicate-identity-fraud.ts` = **1**; `grep -c 'payoutMethodHash?: never' apps/web/lib/api/fraud/detect-duplicate-payout-method-fraud.ts` = **1**; `grep -o 'cryptoWalletAddress' apps/web/lib/api/fraud/detect-duplicate-payout-method-fraud.ts | wc -l` = **8** (2 type-XOR arms :11-12 + destructure :18 + neither-guard :20 + 2 in the OR spread :29 + 2 in the metadata spread :103); `grep -c 'holdProcessedCommissions(affectedGroups)' apps/web/lib/api/fraud/detect-duplicate-identity-fraud.ts` = **1**. Direct tests: none isolated (recorded caveat) — detectors are webhook/cron-driven.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "detectDuplicateIdentityFraud", limit: 5 });
```

## Verdict
Adopt the shared-skeleton detector (key → enrollments → rule filter → multiplicity gate → directed-pair events → holds). Adapt identity providers and payout-method keys. Omit the Veriff schema details; keep the sessionIds-union idea if you verify identities.
