<!-- capsule-v2 -->
# Draft-submission upsert cron — how do you machine-create "in progress" rows for lifetime performance goals, and re-open them after expiry?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** When a performance bounty awards a fixed prize once a lifetime threshold is crossed, how do you keep one draft row per partner in sync with live stats — auto-submitting at the threshold, surviving races with manual finalization, and re-arming after an expired bounty is reopened?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/lib/bounty/api/upsert-draft-bounty-submissions.ts:planDraftBountySubmissionUpserts` (:53-124) + `shouldUpsertDraftSubmissionsOnReopen` (:29-51) · `apps/web/app/(ee)/api/cron/bounties/upsert-draft-submissions/route.ts:POST` (:33-258) · `apps/web/lib/bounty/api/trigger-draft-bounty-submissions.ts:triggerDraftBountySubmissionCreation` (:15-127) · direct test `apps/web/tests/bounties/upsert-draft-bounty-submissions.test.ts` (pure-unit, 14 cases).
**Signature:** `planDraftBountySubmissionUpserts({partners: PartnerLifetimeStats[], existingDraftSubmissions: ExistingBountySubmission[], condition: AwardBountyCondition, programId, bountyId}) => {toCreate: BountySubmissionCreateManyInput[], toUpdate: DraftBountySubmissionUpdate[]}`; `shouldUpsertDraftSubmissionsOnReopen({type, performanceScope, previousEndsAt, startsAt, endsAt, archivedAt, now?}) => boolean`.
**Data Shape:** PartnerLifetimeStats = {id, totalLeads, totalConversions, totalSaleAmount, totalCommissions} (cents). condition = {attribute ∈ 4 stats, operator "gte" (ONLY operator), value}. toUpdate row = {id, performanceCount, promoteToSubmitted}. Cron body = {bountyId, partnerIds?, page?=0}; MAX_PAGE_SIZE=100.

### Decisive source
```ts
// PURE PLANNER (upsert-draft-bounty-submissions.ts :84-118) — clamp at threshold, auto-submit on create:
if (performanceCount <= 0) continue;                                   // no row for zero activity
const conditionMet = evaluateWorkflowConditions({ conditions: [condition], context: { [condition.attribute]: performanceCount } });
if (!existing) {
  toCreate.push({ id: createId({ prefix: "bnty_sub_" }), programId, partnerId, bountyId,
    performanceCount: conditionMet ? condition.value : performanceCount,   // CLAMPED at the award value once met
    ...(conditionMet && { status: "submitted", completedAt: new Date() }) });
} else if (existing.performanceCount !== performanceCount || conditionMet) {
  toUpdate.push({ id: existing.id, performanceCount: conditionMet ? condition.value : performanceCount, promoteToSubmitted: conditionMet });
}
// REOPEN PREDICATE (:45-50) — lifetime performance only, was expired, now-or-soon active:
const wasExpired = previousEndsAt != null && previousEndsAt < now;
const stillExpired = endsAt != null && endsAt < now && startsAt != null && startsAt <= now;
const nowOrSoonActive = !archivedAt && !stillExpired;                   // future startsAt still counts as reopen
return wasExpired && nowOrSoonActive;
// CRON WRITER — race guard lives in the UPDATE WHERE (route :213-224):
await prisma.bountySubmission.update({
  where: { id: update.id, status: "draft" },   // in case of race condition, we don't want to update an already submitted entry
  data: { performanceCount: update.performanceCount,
    ...(update.promoteToSubmitted && { status: "submitted", completedAt: new Date() }) },
});
// creates are skipDuplicates against @@unique([bountyId, partnerId, periodNumber]); full page ⇒ self-requeue page+1 via QStash
```
**Flow:** trigger sites (bounty POST when type=performance ∧ scope=lifetime ∧ startMode≠relative, notBefore startsAt; PATCH when shouldUpsertDraftSubmissionsOnReopen fires; partner-approved workflow step 5; move-partners-to-group; update-program-partner-tags; accept-program-invite) all funnel through triggerDraftBountySubmissionCreation, which re-filters bounties (archivedAt null, performance, lifetime, buildBountyEligibilityWhere + buildBountyActivePeriodWhere) AND partners (isPartnerEligibleForBounty) before publishing one QStash job per (bounty, eligiblePartnerIds). The cron route verifies the QStash signature, then runs the gate ladder: bounty missing ⇒ error log; startsAt ≥10 min away ⇒ skip; type≠performance ⇒ skip; scope=="new" ⇒ skip (new-scope counts post-start data, so lifetime-style drafts don't apply); no workflow ⇒ skip. It scans enrollments (status in COMMISSION_ELIGIBLE_ENROLLMENT_STATUSES, group/tag-filtered by the bounty's audience, createdAt asc, page*100/100), aggregates link stats per enrollment, reads existing drafts (periodNumber 1, status draft), runs the pure planner, writes createMany(skipDuplicates) + guarded updates, and self-requeues while pages stay full.
**Invariant:** (1) The planner is PURE and directly tested — all money-relevant decisions (skip-zero, clamp-at-threshold, auto-submit-on-create, refresh-only-on-change-or-promotion) live in planDraftBountySubmissionUpserts so they are unit-testable without a DB; the route only gates, scans, and writes. (2) The stored performanceCount CLAMPS at condition.value once met — the row stops growing past the award value, so the UI's "progress" bar cannot exceed the prize. (3) The writer's update WHERE carries status:"draft": a concurrent manual finalization (or a prior page's promotion) wins, and the stale upsert becomes a no-op instead of resurrecting a submitted row. (4) Reopen is asymmetric: it requires the bounty to have BEEN expired (previousEndsAt < now) — extending an active bounty's end date does NOT re-arm drafts, but rescheduling to a FUTURE startsAt does (nowOrSoonActive tolerates not-yet-started). (5) One draft per partner per bounty: periodNumber is pinned to 1 for performance bounties ("only one submission is allowed").
**Probe:** DIRECT TEST EXISTS — tests/bounties/upsert-draft-bounty-submissions.test.ts (pure-unit, offline-blocked here, line-pinned): shouldUpsertDraftSubmissionsOnReopen ×9 cases (:55 reopen-true, :69 endsAt-cleared-true, :83 future-reschedule-true, :97 no-previous-endsAt-false, :111 new-scope-false, :125 not-previously-expired-false, :139 still-expired-false, :153 archived-false, :167 submission-type-false); planDraftBountySubmissionUpserts ×5 cases (:183 create-without-status, :203 auto-submit-clamped-at-threshold, :220 refresh-only-on-change, :239 promote-on-meet, :257 zero-count-skip). Deterministic probes executed at pin: `status: "draft", // in case of race condition` at route :217; `skipDuplicates: true` at :207; `MAX_PAGE_SIZE = 100` at :26; `page: page + 1` self-requeue at :241; `periodNumber: 1, // only one submission is allowed` at :178; NEGATIVE probe: no `operator` other than gte exists in award-bounty/schema.ts (AWARD_BOUNTY_OPERATORS = {gte} only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "planDraftBountySubmissionUpserts draft bounty submission upsert condition", limit: 10 }); // rank-1 expected: upsert-draft-bounty-submissions.ts
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "triggerDraftBountySubmissionCreation", direction: "inbound", depth: 1 }); // callers_total=5: partner-approved workflow, accept-program-invite, move-partners-to-group, update-program-partner-tags, (self)
```

## Verdict
Adopt the pure-planner/race-guarded-writer split for any background job that must converge rows toward a live-computed target: decide everything in a testable function, then write with the current-state predicate IN the WHERE clause so concurrent transitions win. Adopt clamp-at-threshold storage when the stored number doubles as UI progress toward a fixed prize. Adopt the was-expired-and-now-active reopen predicate (with future-reschedule tolerance) for re-arming derived rows after a window closes. Adapt the QStash self-requeue paging (full-page ⇒ publish next page) to your queue's continuation primitive. Omit nothing silently: dropping the status:"draft" WHERE guard lets a stale cron page resurrect a manually finalized row; dropping the clamp lets progress display exceed the prize.
