<!-- capsule-v2 -->
# Workflow trigger entry — how does the QStash workflow client get triggered, and what flow-control + correlation contract do the three durable workflows share?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** Where is the single choke point for starting partner-approved / create-partner-commission / merge-partner-accounts workflows, and what retries/parallelism apply?

## qstash-workflow.ts: triggerQStashWorkflow + getWorkflowConfig
**Path/Symbol:** `apps/web/lib/cron/qstash-workflow.ts:triggerQStashWorkflow` (:30-84) + `getWorkflowConfig` (:86-118); commission entry `apps/web/lib/partners/queue-partner-commission-creation.ts` (:8-38); callers approve-partner, bulk-approve-partners, merge action.
**Signature:** `triggerQStashWorkflow(input | input[])` with 3 exponential retries then STRUCTURED failure (`logger.error("workflow.trigger_failed", {correlation})`) and a null return — never throws after retries.
**Data Shape:** per workflow `{url:/api/workflows/<type>, body, label, retries:5, flowControl:{key, parallelism:15}}`; commission creation overrides flowControl to `{key: partnerId, parallelism:1}` so one partner's commissions serialize.

### Decisive source
```ts
const response = await client.trigger(workflows.map((workflow) => ({
  url: `${APP_DOMAIN}/api/workflows/${workflow.workflowType}`,
  body: workflow.body, label: workflow.workflowLabel,
  retries: 5,
  flowControl: workflow.flowControl ?? { key: workflow.workflowType, parallelism: 15 } })));
...
for (const workflow of workflows) {
  const { correlation } = getWorkflowConfig(workflow);
  logger.error("workflow.trigger_failed", { service: "qstash", ..., correlation });
}
await logger.flush();
return null;
```
(:36-83)

**Flow:** callers build typed bodies (partnerApproved `{programId,partnerId,userId}`; createPartnerCommission adds customerId/bountySubmissionId; merge adds emails) → batched trigger with defaults → success logs count; exhaustion returns null so the CALLER decides whether the user-facing step can continue without the async work. The commission path pre-fetches enrollment data BEFORE triggering so the webhook payload is ready regardless of queue latency, and its parallelism-1 key guarantees per-partner ordering (no duplicate-commission races between concurrent sales).
**Invariant:** (1) flow-control keys are the real concurrency contract — workflowType-level keys (15-wide) for independent workflows, partner-level keys (serial) where ordering equals correctness; (2) trigger failure is OBSERVED (correlated log + flush) not thrown, because triggers usually fire inside request paths that already committed their DB writes; (3) `retries:5` at the queue level plus each route's own durable-step revalidation compose instead of duplicating retry logic.
**Probe:** deterministic probe: `grep -n 'parallelism: 15\|retries: 5' apps/web/lib/cron/qstash-workflow.ts` = :43,:46; `grep -c 'parallelism: 1' apps/web/lib/partners/queue-partner-commission-creation.ts` = 1. No upstream unit suite covers these helpers directly (recorded caveat; downstream workflows carry e2e tests recorded in prior capsules).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "triggerQStashWorkflow", limit: 5 });
```

## Verdict
Adopt the typed choke-point trigger with per-type default flow control and caller-overridable serial keys. Adapt correlation logging to your observability stack. Omit nothing else — this is the whole entry surface.
