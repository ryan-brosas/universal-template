<!-- capsule-v2 -->
# Referral attribution & loop safety — how do you bind a referring partner to an application after the fact without creating referral cycles or double attribution?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What guards precede the manual attribution upsert, and why does a malformed pre-existing cycle stop the walk instead of erroring?

## attributeReferringPartnerAction: no-self → approved-referrer → unclaimed → loop-walk → guarded upsert
**Path/Symbol:** `apps/web/lib/partner-referrals/attribute-referring-partner.ts:attributeReferringPartnerAction` (:16-166) + `throwIfReferralLoop` (:168-212); backfill cron `apps/web/app/(ee)/api/cron/commissions/referrals/backfill/route.ts:POST` (:17-140).
**Signature:** server action `{partnerId, referredByPartnerId, createCommissionsForPastEvents}`; permission owner|member.
**Data Shape:** `programApplicationEvent` unique by `(programId, partnerId)`; synthetic visit timestamps are RELATIVE to the application: visitedAt=base−30min, startedAt=base−5min, submittedAt=base−1min (:121-123).

### Decisive source
```ts
await prisma.programApplicationEvent.upsert({
  where: { programId_partnerId: { programId, partnerId }, referredByPartnerId: null },  // claim only if unclaimed
  update: { referredByPartnerId },
  create: { id: createId({ prefix: "pga_evt_" }), ..., referredByPartnerId,
            referralSource: "manual", country: referrer.partner.country,
            visitedAt: subMinutes(baseDate, 30), startedAt: subMinutes(baseDate, 5),
            submittedAt: subMinutes(baseDate, 1), approvedAt: programEnrollment.createdAt } });
} catch (error) { if (error.code === "P2002")
  throw new DubApiError({ code: "conflict", message: "This partner already has a referring partner." }); }
```
(:103-136)
```ts
// Malformed data: ancestor chain already cycles (e.g. A→B→A) without
// including partnerId — stop walking instead of looping forever.
if (visited.has(currentReferrerId)) break;
```
(:189-194)

**Flow:** self-attribution rejected → BOTH enrollments must exist and the REFERRER's must be `approved` → target must have NO existing applicationEvent.referredByPartnerId (loud bad_request) → `throwIfReferralLoop` walks the referrer's ancestor chain (`applicationEvent.referredByPartnerId` hop-by-hop): reaching the target partner ⇒ reject (would create a cycle); revisiting any node ⇒ break (pre-existing corrupt cycle is not this request's fault); → upsert claims the row only while `referredByPartnerId:null`, racing claims surface as P2002→409 conflict → opt-in backfill enqueues ONE job for flat triggers (partnerApproved/commissionThreshold) or 50-chunked per-sale jobs for percentage triggers, each dedup'd `create-referral-commissions-${...}`.
**Invariant:** (1) attribution is CLAIM-shaped — the partial unique index implied by `referredByPartnerId: null` in the where-clause makes "first writer wins" a database property, not an application check; (2) loop prevention walks ancestors BEFORE writing, but a corrupted stored cycle degrades to no-op rather than infinite loop or spurious failure; (3) fabricated funnel timestamps keep downstream analytics believing a normal visit→apply→approve sequence occurred.
**Probe:** deterministic probe: `grep -n 'visited.has(currentReferrerId)' apps/web/lib/partner-referrals/attribute-referring-partner.ts` = :192; `grep -c 'subMinutes(baseDate' apps/web/lib/partner-referrals/attribute-referring-partner.ts` = 3. No upstream unit suite covers this file (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "attributeReferringPartner", limit: 5 });
```

## Verdict
Adopt the claim-shaped conditional upsert and the bounded ancestor walk for any DAG-shaped referral/permission graph. Adapt the timestamp fabrication (drop it if your schema doesn't require funnel fields). Omit the backfill trigger split unless you port rewards too.
