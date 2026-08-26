<!-- capsule-v2 -->
# Webhook job decoupling — what does the webhook processor guarantee before invoking the user's hook, and why is addJob re-injected into the payload?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does hook delivery stay decoupled from request handling, and how can a hook trigger follow-up jobs?

## resolve-then-invoke with addJob re-injection
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/webhook-handler/webhook-handler.processor.ts:WebhookHandlerProcessor.job` (15-53).
**Signature:** `job(job: Job<HandleWebhookJobData>): Promise<void>`; payload `{context, hookId, modelId, viewId?, prevData, newData, user, hookName, ncSiteUrl}`.
**Data Shape:** ids only on the wire (never full objects); Hook/Model/View rehydrated inside the worker; `addJob` callback bound to JobsService for async-hook recursion.

### Decisive source
```ts
const hook = await Hook.get(context, hookId);
if (!hook) { this.logger.error(`Hook not found for id: ${hookId}`); return; }   // silent skip
const model = await Model.get(context, modelId);
if (!model) { this.logger.error(`Model not found for id: ${modelId}`); return; }
const view = viewId ? await View.get(context, viewId) : null;
await invokeWebhook(context, {
  hook, model, view, prevData, newData, user, hookName, ncSiteUrl,
  addJob: this.jobsService.add.bind(this.jobsService),   // hooks can enqueue more jobs
});
```

**Flow:** event producers enqueue `{hookId,...}` instead of delivering inline — slow/failing HTTP endpoints never block API writes. The worker re-fetches current hook/model state (config may have changed between enqueue and run), then invokes the shared `invokeWebhook` helper which handles sync/async plugin delivery. Deleted hook or model ⇒ log + return: a stale queued event must not fail/requeue forever.
**Invariant:** pass IDs in job data and re-resolve at execution time — serializing full records would deliver stale payloads after edits between enqueue and processing. Missing entities are terminal-but-quiet (`return`, no throw) to avoid retry loops against deleted resources. The `addJob` re-injection exists because async hooks (e.g., long-running automations) are themselves dispatched as jobs.
**Probe:** no unit test upstream. Source-grounded probe: `webhook-handler.processor.ts:29-38` — both null-guards return without throwing; `:51` — bound addJob passed into invokeWebhook.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "WebhookHandlerProcessor invokeWebhook HandleWebhookJobData", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt id-only payloads with execution-time rehydration and quiet-skip on missing entities; adapt entity names, delivery helpers, and audit fields to host; omit async-plugin dispatch unless porting the whole hook system. Coverage caveat: no in-repo tests; source-grounded.
