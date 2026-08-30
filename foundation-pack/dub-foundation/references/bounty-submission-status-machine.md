<!-- capsule-v2 -->
# Bounty submission status machine — how do you model a reviewable submission lifecycle where approval is the only money door?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** When partners submit work for human review and approval pays money, what state machine keeps drafts unreviewable, verdicts one-way, and commission linking idempotent?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/lib/bounty/api/approve-bounty-submission.ts:approveBountySubmission` (:25-185) · `apps/web/lib/bounty/api/reject-bounty-submission.ts:rejectBountySubmission` (:23-145) · `apps/web/lib/bounty/api/create-bounty-submission.ts:BountySubmissionHandler` (:48-613) · `apps/web/lib/partners/queue-partner-commission-creation.ts:queuePartnerCommissionCreation` (:6-38) · `apps/web/app/(ee)/api/workflows/create-partner-commission/route.ts` step "set-bounty-commission" · routes `app/(ee)/api/bounties/[bountyId]/submissions/[submissionId]/{approve,reject}/route.ts` · schema `apps/web/prisma/schema/bounty.prisma:model BountySubmission` (`@@unique([bountyId, partnerId, periodNumber])`, `commissionId String? @unique`).
**Signature:** `approveBountySubmission({programId, bountyId?, submissionId, rewardAmount?, user}) => BountySubmissionSchema`; `rejectBountySubmission({programId, bountyId?, submissionId, rejectionReason="other", rejectionNote?, user}) => BountySubmissionSchema`; `new BountySubmissionHandler({programId, bountyId, files, urls, description?, isDraft, periodNumber?, partner}).submit() => BountySubmission`.
**Data Shape:** status enum {draft, submitted, approved, rejected}; rejectionReason enum {invalidProof, duplicateSubmission, outOfTimeWindow, didNotMeetCriteria, other}. In: review body is OPTIONAL (route try/catches parseRequestBody → `{}`); approve body carries only `rewardAmount?` (used when the bounty has no fixed amount); reject body carries reason+note. Out: strict BountySubmissionSchema parse at every exit.

### Decisive source
```ts
// approve kernel — three-tier oracle, then the review gate (approve-bounty-submission.ts :53-86):
if (!submission) throw new DubApiError({ code: "not_found", message: `Bounty submission ${submissionId} not found.` });
if (submission.programId !== programId) throw new DubApiError({ code: "not_found", ... });   // cross-program ⇒ SAME not_found
if (bountyId && submission.bountyId !== bountyId) throw new DubApiError({ code: "not_found", ... });
if (submission.status === "draft")    throw new DubApiError({ code: "bad_request", message: "This bounty submission is in progress and cannot be approved." });
if (submission.status === "approved") throw new DubApiError({ code: "bad_request", message: "This bounty submission has already been approved." });
// NOTE: rejected is NOT refused here — rejected → approved re-review is legal; approved CANNOT be rejected (one-way money)
// reward resolution (:91-105): bounty amount wins; social-metrics bounties OVERRIDE with tiered calc; then required:
let finalRewardAmount = bounty.rewardAmount ?? rewardAmount;
if (bountyInfo?.hasSocialMetrics) finalRewardAmount = calculateSocialMetricsRewardAmount({ bounty, submission });
if (!finalRewardAmount) throw new DubApiError({ code: "bad_request", message: "Reward amount is required to approve the bounty submission." });
// reject kernel mirrors the gate but ADDS commission severance (reject-bounty-submission.ts :95-103):
data: { status: "rejected", reviewedAt: new Date(), userId: user.id, rejectionReason, rejectionNote, commissionId: null },
// link-back in the create-partner-commission workflow — idempotent by guard, not by check-then-set:
const { count } = await prisma.bountySubmission.updateMany({
  where: { id: bountySubmissionId, status: "approved", commissionId: null },
  data: { commissionId: commission.id },
});
```
```ts
// creation pipeline order (create-bounty-submission.ts :100-112) — nine steps, eligibility BEFORE requirements:
await this.fetchBountyAndEnrollment(); this.resolvePeriodNumber(); this.validateEligibility();
this.validateRequirements(); this.validateFiles(); await this.validateSocialContent();
this.mergeSubmissionData(); const submission = await this.persist(); this.sendNotifications(submission);
// conflict rule (:267-277): existing non-draft row OR any social-metrics bounty with an existing row:
if (existingSubmission.status !== "draft" || bountyInfo?.hasSocialMetrics)
  throw new DubApiError({ code: "conflict", message: `You already have a ${existingSubmission.status} submission for this period.` });
// performance bounties are machine-created only (:279-284): forbidden "You are not allowed to submit a performance bounty."
// persist (:587-613): find-by-periodNumber ⇒ update, else create with bnty_sub_ id — backed by @@unique([bountyId, partnerId, periodNumber])
```
**Flow:** partner finalizes via server action (authPartnerActionClient) or embed-token route (withReferralsEmbedToken) → handler pipeline resolves the period (single / multi-no-frequency client-sent / multi-with-frequency time-gated: explicit period must have started via addFrequency(startsAt, freq, n-1) ≤ now and must not be below currentPeriod) → eligibility (canPartnerSubmitBounty from the pass-16 visibility capsule; submissionsOpenAt gates FINAL submissions only; social-metrics bounties forbid drafts) → requirement/domain/file checks (files pinned to `/programs/<programId>/bounties/<bountyId>/submissions/<partnerId>/` on R2 origin) → social-content verification (platform match, connected+verified account, handle match, publishedAt ≥ effective start; auto-submit when metric ≥ minCount) → upsert-by-period → owner-notification fan-out (drafts send nothing). Review: workspace route re-checks the bounty exists (getBountyOrThrow) then the kernel runs oracle→gate→stamp (reviewedAt+userId)→approve clears rejection fields / reject nulls commissionId → approve queues the commission (queuePartnerCommissionCreation re-fetches enrollment, triggers QStash workflow with flowControl {key: partnerId, parallelism: 1} — per-partner serialization of ALL commission creation) → workflow step 3 links commission back under the {status:"approved", commissionId:null} guard.
**Invariant:** (1) Drafts are IN PROGRESS, not pending review — both review kernels refuse them with bad_request, so a draft can never be paid or rejected out from under its author. (2) The money direction is one-way: approved is terminal for BOTH kernels (re-approve refused; reject-after-approve refused), while rejected→approved re-review stays open because no money moved yet. (3) Every existence failure reports not_found regardless of which scope mismatched (missing / cross-program / cross-bounty) — no existence oracle leaks across programs. (4) Commission linkage is idempotent BY GUARD: the updateMany WHERE carries status:"approved" AND commissionId:null, so workflow retries never double-link and a rejected submission can never receive a commission even if a stale job fires. (5) The per-period uniqueness lives in the DB unique key, not in JS — the handler's find-then-update-or-create is safe because the constraint is the last word.
**Probe:** No direct test for approve/reject/create kernels (glob tests/**/*bounty* = only the draft-upsert suite). Deterministic probes executed at pin: `status === "draft"` refusal at approve :74 AND reject :68 (identical "in progress" message pair); `commissionId: null` at reject :102; `status: "approved", commissionId: null` guard in create-partner-commission/route.ts set-bounty-commission step; `flowControl: { key: partnerId, parallelism: 1 }` in queue-partner-commission-creation.ts; `code: "conflict"` at create-bounty-submission.ts :273; NEGATIVE probe: no `status === "rejected"` refusal on the APPROVE path (only draft + approved refused — re-review legal).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "approveBountySubmission bounty submission status approved reward", limit: 10 }); // rank-1 expected: approve-bounty-submission.ts
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "queuePartnerCommissionCreation", direction: "inbound", depth: 1 }); // callers incl. approve kernel + referral/commission rails
```

## Verdict
Adopt the four-state ladder with the two asymmetric gates (drafts unreviewable; approved one-way terminal; rejected reopenable) whenever a human verdict precedes money movement. Adopt the guard-in-WHERE idempotent link-back (status+null-column predicate) instead of check-then-set for any queue-retried side effect that attaches a resource to a verdict. Adapt the optional-body tolerance (empty POST body legal when the object carries its own amount) to your API's review ergonomics. Omit nothing silently: dropping the draft-refusal lets reviewers pay in-progress work; dropping the commissionId:null guard double-pays on workflow retry.
