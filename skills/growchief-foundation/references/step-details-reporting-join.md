<!-- capsule-v2 -->
# Step-details reporting join — where does the "current step" name come from when projecting bot status?

**Source:** growchief AGPL-3.0 `main@abb1e37a6f5595d8d105aef5871a2eeb0c22a1dc`; Codebase Memory `growchief`. **Question:** when a status UI shows which campaign step is running, do you derive a display name from the step type, or trust what the user named the node?

## Connected graph-selected seam
**Path/Symbol:** `shared/server/database/bots/bots.repository.ts:BotsRepository.getWorkflowStepDetails` (:597–630) + private `_getStepDisplayName` (:632–648). Sole caller: `shared/server/database/bots/bots.service.ts:476` (inside `getBotStatus`, gated on `query.workflowId && query.stepId`).
**Signature:** `getWorkflowStepDetails(workflowId: string, stepId: string, organizationId: string): Promise<{stepName, workflowName, stepType, data} | null>`.
**Data Shape:** Input = live queue query's `{workflowId, stepId}` + org id from the request plane. Output = `{stepName: data.label, workflowName, stepType, data}` where `data = JSON.parse(step.data || '{}')`; `null` when no node matches.

### Decisive source
```ts
const step = await this._workflowNodes.model.workflowNodes.findFirst({
  where: { id: stepId, workflowId, organizationId, deletedAt: null },
  include: { workflow: { select: { name: true } } },
});
if (!step) { return null; }
const data = JSON.parse(step.data || '{}');
return {
  stepName: data.label, // this._getStepDisplayName(step.type, data),
  workflowName: step.workflow.name,
  ...
```

**Flow:** live throttler query returns current `{workflowId, stepId}` → repository re-resolves that node with a **triple tenant filter** (`id` + `workflowId` + `organizationId` + soft-delete guard) → parses the JSON `data` column with `'{}'` fallback → prefers the user-authored `data.label` over any derived name → merges into the status projection.
**Invariant:** the derived display-name mapper must stay subordinate to the user's label — at this pin the call is literally commented out (`// this._getStepDisplayName(...)`), and `_getStepDisplayName` (:632–648, switch over `linkedin-connection-request` / `linkedin-send-message` / `x-send-message` / `delay` + title-case fallback) has **zero callers**: dead code kept as scaffolding. A port that wires the mapper back in changes what users see; treat label-over-derived as the contract.
**Probe:** no upstream test runner exists (spec/test count = 0). Deterministic source pin: read `bots.repository.ts:597–648` and confirm `stepName: data.label` with the mapper call commented out; grep `getWorkflowStepDetails` resolves exactly 2 hits (def :597 + call site bots.service :476).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "_getStepDisplayName getWorkflowExecution step details reporting", limit: 10, fields: ["signature", "lines"] });
// rank#1: BotsRepository._getStepDisplayName bots.repository.ts:632-648; rank#2 getWorkflowStepDetails :597-630
```

## Verdict
Adopt the triple-filter tenant-scoped single-row join with `null` miss ladder and `JSON.parse(data || '{}')` tolerance — it is what makes cross-plane status projection safe to expose. Adapt the JSON column name and soft-delete predicate to your store. Omit `_getStepDisplayName` (dead at this pin; if you want pretty names, generate them at write time into `data.label`). Coverage caveat: both paths `no_recorded_issue`/`metadata_match`; no behavioral test runner upstream — probe is source-pin only.
