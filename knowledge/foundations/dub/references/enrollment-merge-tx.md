<!-- capsule-v2 -->
# Enrollment merge transaction — how does an overlap-merge preserve approval status, applications, and tenant bindings?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** When both partners are enrolled in the same program, which enrollment survives and what fields must be reconciled inside the single tx?

## mergeSingleEnrollment: live re-checks → data move → overlap-tx or ownership-scoped transfer
**Path/Symbol:** `apps/web/app/(ee)/api/workflows/merge-partner-accounts/route.ts:mergeSingleEnrollment` (:488-663).
**Signature:** `mergeSingleEnrollment({ enrollmentId, sourcePartnerId, targetPartnerId, sourceEmail, targetEmail }): Promise<{ programId, action: "skip"|"overlap"|"transfer", outputLog }>`.
**Data Shape:** `programEnrollment` unique on `(partnerId, programId)` and on `(tenantId, programId)`; statuses: pending/invited/approved (+ others).

### Decisive source
```ts
if (sourceEnrollment.partnerId !== sourcePartnerId) {
  return { action: "skip", ... };   // reassigned away mid-run — never steal
}
// ...
// Scope the transfer to the source partner so a concurrent reassignment
// can't make us steal another partner's enrollment.
const { count } = await prisma.programEnrollment.updateMany({
  where: { id: sourceEnrollment.id, partnerId: sourcePartnerId },
  data: { partnerId: targetPartnerId },
});
if (count === 0) return { action: "skip", ... };
```
(:535-541 ownership re-check; :619-632 scoped transfer)

**Flow:** re-fetch the enrollment (step may run long after plan time) · skip if gone / already-on-target / no-longer-owned · fetch target enrollment · `transferPartnerProgramData` FIRST (rows move while the source row still exists) · OVERLAP branch inside ONE `$transaction`: upgrade target status approved only when `source=approved && target∈{pending,invited}`; null out `sourceEnrollment.applicationId` (application record stays with its own enrollment); delete source enrollment; copy `tenantId` ONLY when target lacks one AND no third enrollment already holds that tenant for the program · TRANSFER branch: ownership-scoped updateMany with count check · emit `partner.merged` webhook per enrollment with `targetAlreadyEnrolled` flag.
**Invariant:** (1) status can only be RAISED toward approved by a merging APPROVED source — pending sources never downgrade targets; (2) every mutation of the source enrollment is WHERE-scoped to `partnerId: sourcePartnerId` so a concurrent reassignment turns the write into a no-op instead of stealing someone else's row; (3) tenant uniqueness is checked before binding (the unique index would abort the whole tx otherwise); (4) data rows move BEFORE enrollment resolution because several (e.g. commissions) carry FKs to the surviving partner, not to the enrollment row.
**Probe:** `tests/workflows/merge-partner-accounts-workflow.test.ts` :63-113 pins the pending→approved promotion end-to-end (polls until `sourceRes 404 && targetStatus === "approved"`); deterministic probe: `grep -c 'partnerId: sourcePartnerId' apps/web/app/\(ee\)/api/workflows/merge-partner-accounts/route.ts` = 9 (:127, :311, :404, :581, :587, :622, :696, :894, :931 — every ownership-scoped WHERE plus payload roots).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "mergeSingleEnrollment", limit: 5 });
// → ...route.mergeSingleEnrollment @ route.ts 488-663
```

## Verdict
Adopt the live-recheck ladder, raise-only status reconciliation, application-id severance, and tenant-copy-with-existence-check inside one tx. Adapt status vocabularies. Omit dub's webhook schema details.
