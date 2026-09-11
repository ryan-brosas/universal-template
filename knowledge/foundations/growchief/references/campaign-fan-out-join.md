<!-- capsule-v2 -->
# Campaign fan-out join — how does one campaign workflow start per-lead bot jobs immediately for known URLs and block per-step on enrichment results for unknown emails?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** the bifurcation capsule covers the split — but what is the exact JOIN contract (search attributes, deterministic child ids, signal-await) that keeps hundreds of parallel leads coherent?

## Per-node TypedSearchAttributes + makeId-suffixed child ids + foundIdentifiers condition-join
**Path/Symbol:** `apps/orchestrator/src/workflows/workflow.campaign.ts:workflowCampaign` (:42-185); `extraFields` :48-68; known-lead loop :85-101; enrichment join :121-182.
**Signature:** `extraFields(node)` stamps `{organizationId, workflowId, nodeId, botId}` search attributes + `parentClosePolicy:'ABANDON'` on EVERY child; children get `workflowId: 'workflow-bot-jobs-' + makeId(10)`; unknown leads signal `addEnrichment` with a fresh `stepId: node.identifier`.
**Data Shape:** `foundIdentifiers: {stepId, value: EnrichmentReturn | false}[]` accumulates via setHandler; each lead's Promise.all arm waits `condition(() => foundIdentifiers.some((p) => p.stepId === node.identifier))`.

### Decisive source
```ts
setHandler(finishedEnrichment, (data) => { foundIdentifiers.push(data); });
await Promise.all(nonFoundLead.map(async (node) => {
  await handle.signal(addEnrichment, {...args.body, platform: node.platform,
    internalWorkflowId, stepId: node.identifier, ...});
  await condition(() => foundIdentifiers.some((p) => p.stepId === node.identifier));
  const found = foundIdentifiers.find((f) => f.stepId === node.identifier)!;
  if (!found.value) return;                       // enrichment failed ⇒ drop silently
  const lead = (await addAndReturnLead(...))!;
  await startChild(workflowBotJobs, { workflowId: 'workflow-bot-jobs-' + makeId(10),
    args: [{..., url: found.value.url, leadId: lead.id}], ...extraFields(node) });
}));
```

**Flow:** fetch node rows → partition by existing leadId/url → known leads: startChild bot-jobs immediately → if any unknown remain, get-or-create the singleton enrichment workflow → fan out addEnrichment signals and wait PER NODE on its own stepId → on success write the lead then chain the bot-job child; on `false` the arm returns without side effects.

**Invariant:** the join key is the ENRICHMENT WORKFLOW's random `identifier`, echoed back in finishedEnrichment as stepId — NOT the campaign's own nodeId, so multiple campaigns awaiting simultaneously never steal each other's results. Child bot-job ids are randomized (`makeId(10)`), never derived from business keys, because Temporal requires unique ids per run and the same node may legitimately re-run across campaigns. Search attributes ride every child so the admin control-plane can query/terminate by org/workflow/node/bot (see temporal-multitenant-control-plane). ABANDON parent-close means campaign completion never kills running bot jobs — cleanup belongs to cancelAll/throttler paths, not lifecycle.

**Probe:** deterministic pins from repo root: `grep -cF 'workflow-bot-jobs-' apps/orchestrator/src/workflows/workflow.campaign.ts` → 2; `grep -nF 'foundIdentifiers.some' apps/orchestrator/src/workflows/workflow.campaign.ts` → :145; `grep -cF "startChild(workflowEnrichment" apps/orchestrator/src/workflows/workflow.campaign.ts` → 1; `grep -cF 'addEnrichment' apps/orchestrator/src/workflows/workflow.campaign.ts` → 2 (import + signal).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "workflowCampaign startChild botJobs search attributes", limit: 10 });
```

## Verdict
Adopt identifier-echo joins, randomized child ids, per-child search attributes, ABANDON parenting; adapt attribute names to your engine's tag system; omit nothing behavioral. Coverage caveat: deterministic probes only.
