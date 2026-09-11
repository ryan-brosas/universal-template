<!-- capsule-v2 -->
# Enrollment-window scheduled resolution — how do you evaluate a "enrolled ≥ N days" rule with a 12-hour cron without missing or double-firing partners?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1` (drift pass; comment + take:1000 in current source). **Question:** When a condition is time-window based and the executor runs on a coarse cron, where is the boundary between SQL-side and JS-side filtering?

## resolveProgramEnrollments: the window IS the query, not an evaluated condition
**Path/Symbol:** `apps/web/lib/api/workflows/send-campaign/execute.ts:resolveProgramEnrollments` (:423-515); context builder `buildWorkflowContext` (:295-320); audience filter `campaignAudienceWhere` (:321-341).
**Signature:** `resolveProgramEnrollments({ programId, groupIds, partnerTagIds, conditions }): Promise<ProgramEnrollmentWithRelations[]>`; per-partner twin `resolveProgramEnrollment({...same, partnerId})` returns `[enrollment] | []`.
**Data Shape:** conditions carry the raw `partnerEnrolledDays.value: number`; enrollment rows include links + partner users + rewards via `programEnrollmentInclude`.

### Decisive source
```ts
const startDate = subDays(new Date(), partnerEnrolledDays.value as number);
// add 12 hours to the start date since we run the scheduled enrollment workflow every 12 hours
const endDate = addHours(startDate, 12);
// partnerEnrolledDays is enforced by the enrollment window query below —
// re-evaluating it with differenceInDays can false-negative partners in the window.
const remainingConditions = conditions.filter(
  (condition) => condition.attribute !== "partnerEnrolledDays");
const programEnrollments = await prisma.programEnrollment.findMany({
  where: { programId, ...campaignAudienceWhere({ groupIds, partnerTagIds }),
           createdAt: { gte: startDate, lte: endDate } },
  include: programEnrollmentInclude,
  take: 1000, // rough estimate that a program cannot get more than 1000 enrollments every 12 hours
});
```

**Flow:** find the enrolledDays condition → convert it into a [now−N days, now−N days+12h] createdAt window queried in SQL → STRIP it from the JS-evaluated condition list (the window already decided it) → batch-fetch commissions per partner only if remaining conditions need them (`getWorkflowDataRequirements`) → evaluate leftover conditions per enrollment in JS. The transactional (event-driven) twin resolves ONE enrollment by id, builds the same context, evaluates ALL conditions including enrolledDays via `differenceInDays`, and returns [] when they fail.
**Invariant:** a time-window attribute must be evaluated EXACTLY ONCE at whichever layer owns resolution — evaluating day-diff in JS after the SQL window double-filters and false-negatives (a partner enrolled N+11h ago has differenceInDays = 0). The fixed +12h endDate equals the cron period; widening it drifts into re-sends (dedup guard: NotificationEmail lookup excludes already-sent partners before any email goes out). `take:1000` is a documented capacity assumption, not pagination — overflow silently truncates. Audience narrowing (`campaignAudienceWhere`: approved-only + optional groupId IN + partnerTags SOME) composes INTO the same where as the window.
**Probe:** `playwright/api/campaigns/send-campaign-workflow.spec.ts` drives the whole ladder through `POST /api/cron/workflows/{id}` (`runScheduledCampaignWorkflow` helper :54) asserting sends happen for in-window partners and drafts/paused never send.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "resolveProgramEnrollments buildWorkflowContext", limit: 8 });
// → lib.api.workflows.send-campaign.execute.resolveProgramEnrollments @ execute.ts 423-515
```

## Verdict
Adopt window-as-SQL-predicate with explicit stripping of the window condition from downstream evaluation, plus the sent-ledger dedup. Adapt window width to YOUR cron period (they must match). Omit the group/tag audience filters without programs.
