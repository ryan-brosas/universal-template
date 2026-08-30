<!-- capsule-v2 -->
# Partner-approved onboarding choreography — why does the network program stop after step 1, and what must each durable step re-verify?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How do you sequence an approval pipeline (links → discount → email → webhook → bounty drafts → workflow trigger → referral commission) so each step is idempotent under QStash retries?

## serve() seven-step pipeline with per-step guards
**Path/Symbol:** `apps/web/app/(ee)/api/workflows/partner-approved/route.ts` (:55-373).
**Signature:** `serve<Input>(async (context) => {...}, { initialPayloadParser, failureFunction })` — steps: `create-default-links` / `create-discount-codes` / `send-email` / `send-webhook` / `trigger-draft-bounty-submission-creation` / `execute-workflows` / `create-referral-commission`.
**Data Shape:** input `{ programId, partnerId, userId }`; enrollment loaded ONCE before the steps (with program/partner/links) and threaded through; `allPartnerLinks` array MUTATED inside step 1 then consumed by step 4's webhook payload.

### Decisive source
```ts
// Skip existing default links (should never happen since it's a new partner, but just in case)
for (const link of existingPartnerLinks) {
  if (link.partnerGroupDefaultLinkId) {
    partnerGroupDefaultLinks = partnerGroupDefaultLinks.filter(
      (defaultLink) => defaultLink.id !== link.partnerGroupDefaultLinkId,
    );
  }
}
// ...
// for network program, only need to create default links
if (program.id === NETWORK_PROGRAM_ID) return;
// ...
idempotencyKey: `application-approved/${programEnrollment.id}`,
```
(:105-112 dedup filter; :172-174 network early-return; :267 email idempotency)

**Flow:** step 1 loads group default links + UTM template, FILTERS out already-created defaults by `partnerGroupDefaultLinkId`, creates the rest via `createPartnerDefaultLinks`, PUSHES results into `allPartnerLinks` · network-program short-circuit BEFORE any side-effect step · step 2 auto-provisions discount codes when group config enables it · step 3 emails opted-in partner users (`notificationPreferences.applicationApproved`) as a batch keyed `application-approved/<enrollmentId>` — Resend retries suppressed on retry · step 4 parses the ENROLLED-partner webhook shape from enrollment+partner+social platforms · step 5 triggers draft bounty submissions · step 6 fires `executeWorkflows({ event: "partnerEnrolled" })` · step 7 creates the referrer's commission. failureFunction logs `workflow.failed` with correlation and flushes.
**Invariant:** (1) each step re-checks its own precondition INSIDE the step (groupId presence, existing links, zero opted-in users) because a retry resumes mid-pipeline with stale outer state; (2) the in-memory `allPartnerLinks` hand-off is safe ONLY because QStash caches completed step outputs and replays them deterministically — a porter moving that mutation across a non-durable boundary loses links from the webhook payload; (3) side effects are sequenced so the workspace never receives a `partner.enrolled` webhook whose links/discounts don't exist yet.
**Probe:** deterministic probe: `grep -c 'await context.run(' apps/web/app/\(ee\)/api/workflows/partner-approved/route.ts` = 7; behavior covered by partner-application e2e suites (`tests/partner-applications/`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "createPartnerDefaultLinks", limit: 5 });
// → dub.apps.web.lib.api.partners.create-partner-default-links.createPartnerDefaultLinks @ create-partner-default-links.ts 35-97
```

## Verdict
Adopt the guarded-step pipeline ordering (provision → notify → announce → fan out) with in-step precondition re-checks and enrollment-keyed email idempotency. Adapt step inventory to your product. Omit dub's email templates and network-program special case unless porting dub itself.
