<!-- capsule-v2 -->
# Temporal multitenant control plane — how do search attributes, deterministic IDs, and listWorkflows queries form the admin control plane?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** how does the API server find, signal, terminate, and introspect the RIGHT long-lived workflows per bot/org without its own registry table?

## Four TEXT search attributes + id grammar + visibility-query fan-out
**Path/Symbol:** attributes `shared/server/temporal/temporal.search.attribute.ts` (whole); boot registration `shared/server/temporal/temporal.register.ts:TemporalRegister.onModuleInit`; fan-out consumers `bots.service.ts` (deleteBot :66-87, updateBotWorkingHours :99-141, updateBotStatus :143-176, loggedOut :214-251), `workflows.service.ts:updateWorkflow/deleteWorkflow` (:260-364).
**Signature:** `defineSearchAttributeKey('organizationId'|'workflowId'|'nodeId'|'botId', SearchAttributeType.TEXT)`; query strings like `` `botId="${id}" AND WorkflowType IN("workflowBotJobs","userWorkflowThrottler") AND ExecutionStatus="Running"` ``.
**Data Shape:** workflow-ID grammar: `user-throttler-${botId}` (deterministic singleton), `campaign-${workflowId}-${makeId(20)}`, `workflow-bot-jobs-${makeId(10)}`, literal `enrichment`.

### Decisive source
```ts
// boot: create any missing cluster search attributes exactly once
const { customAttributes } = await connection.operatorService.listSearchAttributes({ namespace });
const missing = ['workflowId','nodeId','botId','organizationId'].filter((a) => !customAttributes[a]);
if (missing.length) await connection.operatorService.addSearchAttributes({
  namespace, searchAttributes: missing.reduce((all, c) => { all[c] = 1; return all; }, {}) });

// admin action = list-then-signal/terminate loop:
for await (const wf of client.listWorkflows(
    `botId="${id}" AND WorkflowType="userWorkflowThrottler" AND ExecutionStatus="Running"`)) {
  try { await (await client.getWorkflowHandle(wf.workflowId)).signal('botStatus', status === 'ACTIVE'); }
  catch (e) { console.log(`Failed to signal ${wf.workflowId}:`, e.message); }
}
// tenant check on direct handle access:
if (workflow?.typedSearchAttributes?.get(orgId) !== organizationId) return { found: false };
```

**Flow:** every child start stamps TypedSearchAttributes (org always; campaign adds wf/node/bot) → admin mutations translate user intent (pause bot, save hours, delete workflow, cancel subscription) into a visibility query → each hit is signaled or terminated individually with per-item error tolerance. Subscription deactivation fans out org-wide (`cancelAllWorkflows` terminates EVERY running workflow for the org, then disables bots and deletes proxies in independent try/catches).
**Invariant:** the throttler's ID is DERIVED (`user-throttler-${botId}`), never stored — startChild on an existing ID is a no-op error swallowed by try/catch (:55-63 bot.jobs; :24-31 upload.leads), which IS the idempotent get-or-create mechanism; every signal sent to a possibly-dead workflow is individually try/caught so one dead handle cannot abort the fan-out.
**Probe:** no test runner upstream. Deterministic pins: `grep -n 'listWorkflows' shared/server/database/bots/bots.service.ts` → :69/:107/:151/:221/:286; `grep -n "user-throttler-" apps/orchestrator/src/workflows/workflow.bot.jobs.ts` → :38.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "listWorkflows typedSearchAttributes terminate", limit: 10 });
```

## Verdict
Adopt: search-attribute-indexed control plane with derived deterministic IDs for singletons and list-signal loops for fan-out. Adapt attribute names/query syntax to your engine. Omit Temporal operatorService specifics if your platform pre-registers attributes.
