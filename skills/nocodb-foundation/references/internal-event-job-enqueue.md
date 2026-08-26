<!-- capsule-v2 -->
|# Internal-event job enqueue — service-layer producers for webhook and url-upload job types

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** Which job types are NOT enqueued by REST controllers but by internal event handlers — and what contract do they share?

## Path/Symbol
`packages/nocodb/src/services/emit-handler/attachment-url-upload.handler.ts:25`; `services/hook-handler.service.ts:182` + `services/hooks.service.ts:387` (HandleWebhook sites); processors under `modules/jobs/jobs/webhook-handler/` and `attachment-url-upload/`.

**Signature:** `jobsService.add(JobTypes.HandleWebhook | JobTypes.AttachmentUrlUpload, arg)` — arg is the FULL hook/attachment context captured at emit time.

**Data Shape:** both ride the SAME IJobsService token as REST-triggered jobs — no separate internal queue, no bypass of admission/meta-row upserts.

### Decisive source
```ts
// services/emit-handler/attachment-url-upload.handler.ts:25
await this.jobsService.add(JobTypes.AttachmentUrlUpload, arg);
// services/hook-handler.service.ts:182
await this.jobsService.add(JobTypes.HandleWebhook, { ... });
```

**Flow:** async event (hook fired / URL attachment saved) → service-layer handler builds a self-sufficient payload → standard add() (meta row, version stamp) → processor rehydrates and executes; hook recursion re-injects via the injected add (webhook-rehydration-guards.md).

**Invariant:** (1) Internal events use the SAME queue surface as user actions: one admission gate, one relay protocol, no side channel around worker coordination. (2) Payloads are self-sufficient snapshots — emit-time state travels because triggering rows may change before execution. (3) Hook-driven jobs may enqueue further jobs (recursion allowed, depth governed upstream).

**Probe:** no unit test upstream. Source-grounded probe: three enqueue lines above verbatim; pairing capsules webhook-rehydration-guards.md + url-upload-passthrough.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "HandleWebhook AttachmentUrlUpload jobsService add emit handler", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt one-queue-for-everything with service-layer enqueue sites and self-sufficient payloads; adapt event names; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
