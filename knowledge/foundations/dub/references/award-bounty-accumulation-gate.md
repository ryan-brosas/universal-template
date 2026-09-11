<!-- capsule-v2 -->
# Award-bounty accumulation — how does a workflow accumulate progress toward a one-shot reward without double-submitting?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How should an event-triggered bounty workflow track a counter across events and flip to terminal exactly once?

## executeAwardBountyWorkflow: upsert-increment draft submission → gate on accumulated count → guarded status flip
**Path/Symbol:** `apps/web/lib/api/workflows/award-bounty/execute.ts:executeAwardBountyWorkflow` (:32-283).
**Signature:** `executeAwardBountyWorkflow({ workflow, context }): Promise<void>`; requires exactly ONE condition (`conditions.length !== 1 → return`, :42-44) because the single condition IS the bounty's goal metric.
**Data Shape:** `bountySubmission` unique on `(bountyId, partnerId, periodNumber)` with `performanceCount` + `status` (draft → submitted/approved/rejected); `periodNumber = 1` hardcoded — performance bounties are single-period.

### Decisive source
```ts
const bountySubmission = await prisma.bountySubmission.upsert({
  where: { bountyId_partnerId_periodNumber: { bountyId, partnerId, periodNumber } },
  create: { ..., status: "draft", performanceCount },          // first event starts at its own count
  update: { performanceCount: { increment: performanceCount } },
});
// Gate on the ACCUMULATED value:
const shouldExecute = evaluateWorkflowConditions({
  conditions: [condition],
  context: { [condition.attribute]: Number(bountySubmission.performanceCount ?? 0) },
});
// ...
const { partner } = await prisma.bountySubmission.update({
  where: { id: bountySubmission.id, status: "draft" },   // lost-race guard
  data: { status: "submitted", completedAt: new Date() },
  include: { partner: true },
});
```
(:173-195 upsert; :198-210 gate on accumulated; :213-225 flip)

**Flow:** type guard · enrollment/groupId presence · bounty load with THIS partner's submissions · reward-amount/performance-type sanity skips · `isPartnerEligibleForBounty` · terminal-status skip via `terminalStatusReason` map (submitted="finished", approved="been awarded", rejected="been rejected", :23-30) · net-new scope check: `performanceScope === "new"` rejects when `customerFirstSaleAt < startsAt` (bounty start precedes the customer's first sale ⇒ not net-new) · upsert-increment · evaluate against accumulated `performanceCount` (not this event's delta!) · draft-guarded update flips to submitted and emails partner + opted-in owners.
**Invariant:** (1) progress accumulates across events in the DB row — the workflow is stateless between runs; (2) the condition evaluates the POST-INCREMENT total, so crossing the threshold mid-stream fires exactly once when the total first reaches it; (3) the status-flip WHERE includes `status: "draft"` — if two events cross the threshold simultaneously, only one update matches, the loser's update affects zero rows and must not re-send completion emails (the code reads the returned row; a porter who ignores row-matching here double-sends); (4) rejected submissions also block re-entry (terminal), preventing gaming by resubmission.
**Probe:** `tests/workflows/award-bounty-workflow.test.ts` (275L) exercises eligibility/submission flow end-to-end with `tests/workflows/utils/verify-bounty-submission.ts` assertions; deterministic probe: `grep -c 'status: "draft"' apps/web/lib/api/workflows/award-bounty/execute.ts` = 2.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "executeAwardBountyWorkflow", limit: 5 });
// → dub.apps.web.lib.api.workflows.award-bounty.execute.executeAwardBountyWorkflow @ award-bounty/execute.ts 32-283
```

## Verdict
Adopt the upsert-increment + post-increment gating + draft-guarded terminal flip trio for any threshold-crossover reward. Adapt the uniqueness triple and notification fan-out. Omit dub's email templates.
