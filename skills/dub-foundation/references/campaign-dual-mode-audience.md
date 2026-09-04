<!-- capsule-v2 -->
# Campaign send dual-mode resolution — how does one workflow executor serve both a single event-triggered partner and a scheduled cohort sweep?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How should a send-campaign workflow resolve its audience when the same code runs per-partner from an event and program-wide from a cron?

## executeSendCampaignWorkflow: context-identity branch → eligibility → sent-ledger dedup → chunked sends with ledger write-back
**Path/Symbol:** `apps/web/lib/api/workflows/send-campaign/execute.ts:executeSendCampaignWorkflow` (:43-257) + `resolveProgramEnrollment` (:349-421) / `resolveProgramEnrollments` (:424-515).
**Signature:** `executeSendCampaignWorkflow({ workflow, context?: WorkflowContext })` — context OPTIONAL: absent identity ⇒ scheduled whole-program mode.
**Data Shape:** action payload `{ campaignId }`; campaign audience = `campaign.groups` ∩ `campaign.partnerTags`; dedup ledger = `notificationEmail` rows `(campaignId, type: "Campaign", partnerId)`.

### Decisive source
```ts
const { programId, partnerId } = context?.identity || {
  programId: workflow.programId, partnerId: undefined,   // undefined ⇒ scheduled mode
};
let programEnrollments = partnerId
  ? await resolveProgramEnrollment({ ...single })
  : await resolveProgramEnrollments({ ...cohort });
// ...
const alreadySentPartnerIds = pluck(alreadySentEmails, "partnerId");
programEnrollments = programEnrollments.filter(
  ({ partnerId }) => !alreadySentPartnerIdSet.has(partnerId));   // dedup BEFORE send
// ...
headers: { "Idempotency-Key": `${campaign.id}-${partnerUser.id}` },   // transport-level too
```
(:60-109 mode branch; :136-149 ledger filter; :229-231 idempotency header)

**Flow:** campaign must exist AND be `active` · audience where-clause (`status: approved` + group/tag IN filters via `campaignAudienceWhere`) · SINGLE mode re-evaluates ALL conditions against that partner's aggregated metrics (with lazy commission aggregate keyed by data requirements) · COHORT mode REQUIRES a `partnerEnrolledDays` condition (else skip), converts it to the 12h-cron-sized `createdAt` window, STRIPS it from JS evaluation (in-source comment :443-444 — day-diff re-check false-negatives partners inside the window), fetches ≤1000 enrollments, groupBy-sums commissions once for all candidates, then filters on remaining conditions · sent-ledger exclusion · optional-from validation TODO preserved · chunks of 100; per-chunk user flattening (email-less users dropped), `sendBatchEmail` with per-user Idempotency-Key, then `notificationEmail.createMany` indexed to `data.data[idx].id`.
**Invariant:** (1) double protection against duplicate sends: DB ledger pre-filter + transport idempotency keys survive QStash retries of a half-completed run; (2) in cohort mode the enrolledDays condition is enforced EXACTLY once (SQL window) — re-checking it in JS is a documented bug class; (3) `take: 1000` is a documented capacity assumption ("a program cannot get more than 1000 enrollments every 12 hours") — silent truncation risk if violated; (4) ledger rows are written only after a successful batch response and map positionally onto provider ids.
**Probe:** deterministic probe: `grep -c 'Idempotency-Key' apps/web/lib/api/workflows/send-campaign/execute.ts` = 1 and `grep -n 'take: 1000' apps/web/lib/api/workflows/send-campaign/execute.ts` = :466; behavior pinned by `playwright/api/campaigns/send-campaign-workflow.spec.ts` (threshold sends end-to-end).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "resolveProgramEnrollments", limit: 5 });
// → dub.apps.web.lib.api.workflows.send-campaign.execute.resolveProgramEnrollments @ send-campaign/execute.ts 424-515
```

## Verdict
Adopt the optional-context dual-mode dispatch, SQL-window-enforced scheduling attribute stripped from JS evaluation, and the two-layer dedup (DB ledger + idempotency keys). Adapt audience filters/transport. Omit dub's Tiptap variable interpolation plane.
