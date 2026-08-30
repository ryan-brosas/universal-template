<!-- capsule-v2 -->
# Campaign enrichment bifurcation — how does one lead fan out to known-URL nodes instantly and unknown-email nodes only after enrichment lands?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** a lead enters with just an email; some workflow nodes need a profile URL, others can act on the email — what is the split-and-join choreography?

## Two partitions + singleton enrichment workflow + per-step signal await
**Path/Symbol:** `apps/orchestrator/src/workflows/workflow.campaign.ts:workflowCampaign` (whole file).
**Signature:** `async function workflowCampaign(args: { orgId: string; workflowId: string; body: EnrichmentDto }): Promise<void>`.
**Data Shape:** `getWorkflowAndNodes` returns `WorkflowNodes[]` ({identifier, botId, platform, nodeId, leadId?, url?}); partition key is presence of `leadId && url`.

### Decisive source
```ts
const nonFoundLead = workflowDetails.filter((f) => !f.leadId);          // email-only
const foundLead = workflowDetails.filter((f) => f.leadId && f.url);     // URL known
for (const node of foundLead) {
  await startChild(workflowBotJobs, { workflowId: 'workflow-bot-jobs-' + makeId(10), ...,
    parentClosePolicy: 'ABANDON', typedSearchAttributes: [...org/wf/node/bot] });
}
if (!nonFoundLead.length) return;
// ONE shared enrichment workflow for the whole app:
try { await startChild(workflowEnrichment, { workflowId: 'enrichment', args: [{}],
      parentClosePolicy: 'ABANDON' }); } catch (err) {}   // already-running ⇒ ignore
const handle = getExternalWorkflowHandle('enrichment');
setHandler(finishedEnrichment, (data) => foundIdentifiers.push(data));
await Promise.all(nonFoundLead.map(async (node) => {
  await handle.signal(addEnrichment, { ...args.body, platform: node.platform,
    internalWorkflowId, stepId: node.identifier, ... });
  await condition(() => foundIdentifiers.some((p) => p.stepId === node.identifier));
  const found = foundIdentifiers.find((f) => f.stepId === node.identifier)!;
  if (!found.value) return;                               // all providers failed
  const lead = await addAndReturnLead(..., found.value);  // persist → now has url+leadId
  await startChild(workflowBotJobs, {...});               // then run its bot jobs
}));
```

**Flow:** known leads start bot-job children immediately; email-only nodes signal the singleton `enrichment` workflow and durably wait for THEIR stepId result (`value` is either an EnrichmentReturn or `false` = exhausted providers), then persist the lead and start its jobs like the first partition.
**Invariant:** the enrichment workflow id is the LITERAL `'enrichment'` — a fixed singleton across all orgs; `startChild` throwing because it already exists is swallowed by design (try/catch around that one call). Each waiter matches results by the node's random `identifier` (makeId(10)) so concurrent campaigns sharing the singleton never steal each other's results.
**Probe:** no test runner upstream. Deterministic pins: `grep -n "workflowId: 'enrichment'" apps/orchestrator/src/workflows/workflow.campaign.ts` → :96-98; `grep -n "p.stepId === node.identifier" workflow.campaign.ts` → :113/:118.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "workflowCampaign addEnrichment finishedEnrichment", limit: 10 });
```

## Verdict
Adopt: partition-by-capability fan-out with a shared enrichment service keyed by per-request correlation ids. Adapt the singleton-id approach if you need per-tenant isolation (search attributes already carry orgId). Omit LinkedIn/X URL normalization details.
