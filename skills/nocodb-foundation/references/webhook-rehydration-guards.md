<!-- capsule-v2 -->
|# Webhook processor — quiet-skip rehydration guards and injected addJob recursion channel

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** What does the webhook JOB layer do when entities vanish between enqueue and execution — and how does hook recursion receive its enqueue function?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/webhook-handler/webhook-handler.processor.ts:WebhookHandlerProcessor.job` (15–54); enqueue sites `services/hook-handler.service.ts:182` + `services/hooks.service.ts:387`.

**Signature:** `job(job: Job<HandleWebhookJobData>)` with payload `{context, hookId, modelId, viewId?, prevData, newData, user, hookName, ncSiteUrl}`; constructor takes `@Inject('JobsService')` and binds `.add` into the invoke call.

**Data Shape:** id + data-snapshot only; entities re-fetched. `prevData/newData` travel in the payload because the row may change again before execution.

### Decisive source
```ts
const hook = await Hook.get(context, hookId);
if (!hook) { this.logger.error(`Hook not found for id: ${hookId}`); return; }   // QUIET skip
const model = await Model.get(context, modelId);
if (!model) { this.logger.error(`Model not found...`); return; }                // QUIET skip
const view = viewId ? await View.get(context, viewId) : null;
await invokeWebhook(context, {
  hook, model, view, prevData, newData, user, hookName, ncSiteUrl,
  addJob: this.jobsService.add.bind(this.jobsService),   // recursion channel
});
```

**Flow:** row event → hooks service enqueues HandleWebhook → processor rehydrates hook→model→(optional view) → missing hook/model ⇒ error LOG + SUCCESSFUL return (job completes; no retry storm against a deleted entity) → invokeWebhook delivers and may enqueue follow-up jobs through the injected add.

**Invariant:** (1) Missing-entity is log-and-return-success, NOT a throw: a hook deleted between enqueue and execution must not consume retry budgets or dead-letter. (2) View absence is normal for row-level hooks — only fetched when the id exists. (3) Recursion is enabled by INJECTING the enqueue fn into invokeWebhook rather than importing a singleton — keeps delivery testable and honors whichever backend the single DI token resolved. (4) Data snapshots ride the payload; ids alone would read post-mutation state.

**Probe:** no unit test upstream. Source-grounded probe: whole file cited above (54 L), pairing capsules webhook-decoupling.md (the pattern) + internal-event-job-enqueue.md (enqueue side).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "WebhookHandlerProcessor invokeWebhook addJob Hook.get Model.get", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt quiet-skip rehydration guards, snapshot payloads, and injected-recursion; adapt delivery internals; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
