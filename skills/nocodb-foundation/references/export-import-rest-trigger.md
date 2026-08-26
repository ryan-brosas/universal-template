<!-- capsule-v2 -->
|# Export/Import REST trigger — anchor-derived ids, controller-owned transport defaults, handle-only acks

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** What belongs in the CONTROLLER before the queue ever sees an export/import payload?

## Path/Symbol
`packages/nocodb/src/controllers/internal/modules/UiPost.operations.ts:dataExport` (640–660); import producer `services/data-import.service.ts:103`.

**Signature:** `case 'dataExport': { const view = await View.get(context, req.query.viewId); if (!view) NcError.viewNotFound(...); ... add(JobTypes.DataExport, {context, options, modelId: view.fk_model_id, viewId, user, exportAs, ncSiteUrl}) }` → returns `{id: job.id, name: job.name}`.

**Data Shape:** payload = resolved entity ids (modelId DERIVED from `view.fk_model_id`, never client-supplied) + sanitized options + request context. Client sends only viewId/exportAs/options.

### Decisive source
```ts
const view = await View.get(context, req.query.viewId);
if (!view) NcError.viewNotFound(req.query.viewId);
const job = await this.nocoJobsService.add(JobTypes.DataExport, {
  context,
  options: { ...options, includeByteOrderMark: true },  // forced at the CONTROLLER
  modelId: view.fk_model_id,                            // derived, not trusted
  viewId: req.query.viewId,
  user: req.user,
  exportAs: payload.exportAs,
  ncSiteUrl: req.ncSiteUrl,
});
return { id: job.id, name: job.name };
```

**Flow:** POST → guard chain → resolve anchor entity → derive dependent ids server-side → merge caller options with controller-forced transport defaults → enqueue → ack with the job handle only; status flows through /jobs/listen.

**Invariant:** (1) Controllers DERIVE ids from one client anchor (viewId → fk_model_id); clients can't name cross-base models directly. (2) Transport concerns (BOM for browser downloads) are decided at the EDGE because only it knows the consumer; internal producers keep defaults clean so machine consumers get no BOM bytes. (3) Ack is a handle — never job output.

**Probe:** no unit test upstream. Source-grounded probe: UiPost.operations.ts lines above verbatim; data-import.service.ts:103 (import twin); pairing capsules export-data-processor-v2.md (consumer), jobs-relay-write-side.md + jobs-polling.md (status path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "dataExport UiPost nocoJobsService includeByteOrderMark", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt anchor-derive-enqueue controllers with edge-owned transport decisions and handle-only acks; adapt route shapes; omit the UiPost mega-switch structure itself. Coverage caveat: no in-repo unit tests; source-grounded.
