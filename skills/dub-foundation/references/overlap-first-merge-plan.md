<!-- capsule-v2 -->
# Overlap-first merge plan — how do you merge two accounts with per-program data when some programs are enrolled in both?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1` (drift pass; new since `873edc5a`). **Question:** In an account merge, which source rows transfer and which fold into existing target rows — and in what order must processing happen?

## loadMergePlan + the overlap/transfer split
**Path/Symbol:** `apps/web/app/(ee)/api/workflows/merge-partner-accounts/route.ts:loadMergePlan` (:247-349) and `mergeSingleEnrollment` overlap branch (:588-640).
**Signature:** `loadMergePlan({ sourceEmail, targetEmail }): Promise<MergePlan>` where `MergePlan = { proceed: false; reason } | { proceed: true; sourcePartnerId, targetPartnerId, sourceImage, sourceUserId, hasRewinds, orderedSourceEnrollmentIds, programIdsToTransfer }`.
**Data Shape:** emails resolved case-insensitively onto Partner rows (`email?.toLowerCase() === sourceEmail.toLowerCase()`); enrollments partitioned by `targetProgramIds.has(programId)` into overlapping vs transfer sets.

### Decisive source
```ts
const overlappingEnrollments = sourceEnrollments.filter((enrollment) =>
  targetProgramIds.has(enrollment.programId));
const transferEnrollments = sourceEnrollments.filter(
  (enrollment) => !targetProgramIds.has(enrollment.programId));
// Overlaps first, then transfers (preserves the original processing order).
const orderedSourceEnrollmentIds = [
  ...overlappingEnrollments,
  ...transferEnrollments,
].map(({ id }) => id);
```

**Flow:** validate both accounts exist and differ → fetch both sides' enrollments → partition into overlap/transfer → durable steps process each enrollment: OVERLAP = move program data first (commissions/links/customers batched, payouts/discounts single-shot, unique-on-(programId,partnerId) rows via findTarget→deleteSource else transferSource) THEN delete the source enrollment in a tx that also promotes `pending|invited` targets to `approved` when source was approved, nulls the applicationId, and copies tenantId only if unclaimed; TRANSFER = re-point the enrollment row itself with `updateMany({ where: { id, partnerId: sourcePartnerId } })` and treat count===0 as "lost the race, skip".
**Invariant:** overlaps MUST be processed before transfers so high-volume row transfers can never collide against a not-yet-folded duplicate; every ownership-checked mutation scopes its WHERE to the source partner so a concurrent reassignment aborts the step instead of stealing another partner's enrollment; tenant uniqueness is respected by copying tenantId only after checking no other enrollment holds it. The merge is one-directional (source → target) and terminal — cleanup deletes the source partner LAST via raw SQL.
**Probe:** `tests/workflows/merge-partner-accounts-workflow.test.ts:100` pins the overlap status-promotion (`lastTargetStatus === "approved"`); :149 pins second-trigger 400/no-duplicate.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "mergeSingleEnrollment loadMergePlan", limit: 8 });
// → route.ts mergeSingleEnrollment 488-663, loadMergePlan 247-349
```

## Verdict
Adopt partition-overlap-first planning, ownership-scoped WHERE clauses on every transfer, and promote-pending-target semantics. Adapt table lists to your schema; keep unique-key rows on a find-target-else-delete ladder. Omit fraud-event cleanup without that subsystem.
