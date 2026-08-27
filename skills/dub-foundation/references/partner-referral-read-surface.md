<!-- capsule-v2 -->
# Partner referrals read surface — how do you list the partners I recruited, with their earned referral rewards, without N+1 queries or leaking emails?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** What does "referrals" mean on a partner-profile program route — customers, or recruited partners — and how are their earnings folded in?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/app/(ee)/api/partner-profile/programs/[programId]/referrals/route.ts:GET` (:15-111).
**Signature:** `export const GET = withPartnerProfile(async ({ partner, params, searchParams }) => ...)`.
**Data Shape:** Query `{country?, status?, page=1, pageSize}`. Rows keyed by referred PARTNER enrollment; output `referredPartnerSchema` = `{id, email(obfuscated?), country, programEnrollment:{...enrollment, earnings:number}}`.

### Decisive source
```ts
if (!programEnrollment.referralRewardId) {                       // :31-36 feature gate
  throw new DubApiError({ code: "forbidden",
    message: "Referral rewards are not enabled for the partner's group." });
}
const enrollments = await prisma.programEnrollment.findMany({
  where: {
    programId: programEnrollment.programId,
    applicationEvent: { referredByPartnerId: partner.id },       // :41-43 — recruits via attribution event
    ...(status && { status }),
    ...(country && { partner: { country } }),                    // :45-47 country filters the RELATED partner
  },
  include: { partner: { select: { id,name,image,email,country } } },
});
// earnings folded from ONE groupBy, not per-row:
const commissions = await prisma.commission.groupBy({
  by: ["sourcePartnerId"],
  where: { programId, partnerId: partner.id, type: CommissionType.referral,
           sourcePartnerId: { in: enrollments.map((e) => e.partner.id) } },
  _sum: { earnings: true },
});
...
earnings: commissionsMap.get(enrollment.partner.id) ?? 0,        // :105 — Map fold with explicit zero-fill
```

**Flow:** parse → own-enrollment scope (getProgramEnrollmentOrThrow) → referralRewardId feature gate ⇒ forbidden with a message naming GROUPS as the enablement surface → find referred enrollments through `applicationEvent.referredByPartnerId` (NOT a partner column) → single commission.groupBy(_sum earnings by sourcePartnerId, type=referral) restricted to THIS recruiter's id + this page's recruit ids → Map fold `?? 0` → obfuscate each referred partner's email unless `customerDataSharingEnabledAt` → strict `z.array(referredPartnerSchema).parse` exit.
**Invariant:** Referral listing is gated on the REWARD existing (the group's referralRewardId), not on a flag column; recruits are discovered through the attribution event relation; earnings aggregation is one grouped query for the whole page (never per-row), and every recruit without commissions still renders with earnings 0. Partner emails get the SAME obfuscation ladder as customer emails.
**Probe:** No tests under tests/partner-profile (glob ∅ this run). Deterministic probes: `referralRewardId` :31, `referredByPartnerId` :42, `_sum` :80/:89, obfuscate-on-partner-email :97-100, `commissionsMap.get(...) ?? 0` :105.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "partner profile program customers referrals route list", limit: 10 });
```

## Verdict
Adopt "recruits = enrollments joined through the attribution event" and the one-groupBy-per-page earnings fold with explicit zero-fill. Adapt the reward-existence gate to whatever object enables referrals in your domain. Omit the email obfuscation only if your referred partners consent to exposure by design.
