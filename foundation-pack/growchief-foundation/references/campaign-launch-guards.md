<!-- capsule-v2 -->
# Campaign launch guards — what stands between "user clicked start" and a Temporal run, and who owns retries?

**Source:** growchief AGPL-3.0 `main@abb1e37a6f5595d8d105aef5871a2eeb0c22a1dc`; Codebase Memory `growchief`. **Question:** when starting, pausing, counting, or cancelling campaign runs, which checks gate the launch and why does the server refuse to retry?

## Connected graph-selected seam
**Path/Symbol:** `shared/server/database/workflows/workflows.service.ts` — `startWorkflow` (:474–496), `startBotWorkflow` (:409–431), `cancelJobs` (:67–69) → `deleteWorkflow(…, preventDelete=true)` (:303–316), `totalRunningWorkflows` (:71–84); pause plane: `changeWorkflowActivity` service (:397–407) → `WorkflowsRepository.changeWorkflowActivity` (:223–238). Sole caller of both start methods: `startWorkflow` (trace: callers_total 1).
**Signature:** `startWorkflow(organizationId, id, body): Promise<{status: 'error'|'success', message}>`; `startBotWorkflow(orgId, workflowId, body): Promise<void>`; `cancelJobs(workflowId, organizationId)`; `totalRunningWorkflows(workflowId, organizationId): Promise<{total}>`.
**Data Shape:** launch guard errors are plain `{status:'error', message}` objects (NOT thrown) — HTTP 200 with an error envelope; success is `{status:'success', message}`. Workflow start options: `{workflowId: 'campaign-${wid}-${makeId(20)}', taskQueue:'main', typedSearchAttributes:[organizationId], retry:{maximumAttempts:1}}`.

### Decisive source
```ts
// startWorkflow :474-496 — guard ladder before any Temporal call
const getWorkflow = await this.getWorkflow(id, organizationId);
if (!getWorkflow) {
  return { status: 'error', message: 'Workflow not found' };
}
if (!getWorkflow.active) {
  return { status: 'error', message: 'Workflow is not active' };
}
await this.startBotWorkflow(organizationId, id, body);

// startBotWorkflow :417-429 — multi-run id, org-only attributes, no server retries
.workflow.start('workflowCampaign', {
  args: [{ workflowId, body, orgId }],
  workflowId: `campaign-${workflowId}-${makeId(20)}`,
  taskQueue: 'main',
  typedSearchAttributes: new TypedSearchAttributes([
    { key: organizationId, value: orgId },
  ]),
  retry: { maximumAttempts: 1 },
});
```

**Flow:** controller → `startWorkflow` resolves the workflow tenant-scoped → exists guard → active guard (both return typed error envelopes instead of throwing) → `startBotWorkflow` starts a NEW `workflowCampaign` child per click with a random 20-char suffix — one campaign definition can have many concurrent runs. Pausing is the mirror image: `changeWorkflowActivity` is a pure tenant-scoped DB flag flip (`update where {id, organizationId, deletedAt:null} data:{active}`) — it does **not** signal any running throttler; it only closes the future-start gate. Cancelling runs without deleting the definition: `cancelJobs = deleteWorkflow(id, org, preventDelete=true)` — skips the DB row delete but still retracts queued jobs from the enrichment singleton and every bot throttler, then terminates every Running workflow whose id matches (:353–369). Counting live runs walks `listWorkflows('WorkflowType="workflowBotJobs" AND workflowId=… AND organizationId=… AND ExecutionStatus="Running"')` and increments a counter per handle.
**Invariant:** (1) guards return typed envelopes; only truly exceptional paths throw. (2) Run identity is `campaign-${wid}-${makeId(20)}` — deliberately NOT a deterministic singleton, so re-clicking stacks runs rather than replacing them (contrast the per-bot `user-throttler-${botId}` singleton); dedup is the caller's problem. (3) `retry.maximumAttempts:1` means the server owns NO retry policy — retries belong to the job-outcome vocabulary (`repeatJob`) inside the throttler, keeping retry semantics at the queue layer where restrictions/working-hours are visible. (4) Pause ≠ cancel: the active flag gates future starts only; stopping in-flight work requires the cancel/retraction path (see queue-retraction-signals). (5) `totalRunningWorkflows` counts `workflowBotJobs` children via quoted-value list query — the same TypedSearchAttributes control plane as temporal-multitenant-control-plane.
**Probe:** no upstream test runner exists (spec/test count = 0, re-verified `find -name '*.spec.ts' -o -name '*.test.ts' | wc -l` = 0). Deterministic source pin executed: `grep -n "maximumAttempts\|preventDelete\|workflowBotJobs\|campaign-\|makeId(20)" workflows.service.ts` → :76, :133, :142, :168, :185, :306, :314, :419, :428 exactly as cited.
**Retrieve (executed):** `search_graph({project:"growchief", query:"startWorkflow startBotWorkflow campaign launch guard active"})` → rank#2 `WorkflowsService.startWorkflow` :474–496, rank#3 `startBotWorkflow` :409–431 line-exact.

## Verdict
Adopt the separation: existence/activation as typed-envelope preconditions, multi-run ids with random suffixes, zero server-side retries (push retry ownership into the durable queue's outcome vocabulary), and pause-as-flag vs cancel-as-retraction-and-terminate. Adapt the Temporal list-query counting to your scheduler's run registry. Omit the NestJS controller shell. Coverage caveat: all four cited paths (`workflows.service.ts`, `workflows.repository.ts`, `bot.list.ts`, `workflows.controller.ts`) returned `no_recorded_issue` + `metadata_match`, `generation_matches: true`; static callers_total = 0 on several methods because calls arrive via NestJS DI controllers — liveness verified by direct grep at `workflows.controller.ts:28–127`. No behavioral runner upstream.
