<!-- capsule-v2 -->
|# DataExport processor — job-wrapper orchestration over the export service (options → streams → artifact)

**Source:** nocodb (Sustainable License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** What does the DataExport JOB layer own — distinct from the streaming internals already mined — that a porter must reproduce to make exports runnable end-to-end?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/data-export/data-export.processor.ts:DataExportProcessor.job` (~45–300); timing brackets :50 + :248–253; producer `controllers/internal/modules/UiPost.operations.ts:640–660`.

**Signature:** `job(job: Job<DataExportJobData>)` with payload `{context, options, modelId, viewId, user, exportAs, ncSiteUrl}`; controller forces `includeByteOrderMark: true`.

**Data Shape:** encoding option reaches only non-Excel formats (`exportAs === 'excel' ? undefined : options?.encoding || 'utf-8'`) — xlsx is a zip container, charset is meaningless. Storage adapter resolved via NcPluginMgrv2; artifacts named deterministically with presigned URLs (see export-presign).

### Decisive source
```ts
const hrTime = initTime();
// ... build per-format stream calls into the export service ...
elapsedTime(hrTime,
  `exported data for model ${modelId} view ${viewId} as ${exportAs}`, 'exportData');
} catch (e) {
  throw { data: { extension_id: options?.extension_id, title: filename } };  // plain-object envelope
}
```

**Flow:** payload → resolve view/model + adapter → initTime → branch on exportAs (csv/json/xlsx) into export.service stream machinery (pump/upload race, projection, serialization all live THERE) → split-log → return artifact descriptor. Failure rethrows a bare `{data:{extension_id,title}}` object, not an Error.

**Invariant:** (1) Processor owns ORCHESTRATION ONLY — every streaming/backpressure invariant stays in export.service; duplicating them here is the porting failure. (2) Excel's encoding exclusion is format-driven, not a default quirk. (3) The non-Error throw envelope is deliberate Bull-facing shape: failure payloads carry file identity to status pollers without stack noise. (4) BOM forcing happens at the CONTROLLER because only it knows the consumer is a browser download; internal producers leave defaults off so machine consumers get clean bytes.

**Probe:** no unit test upstream. Source-grounded probe: UiPost.operations.ts:640-660 (BOM force + derived modelId), processor :246-249 (encoding ternary), :250-262 (envelope), pairing capsules export-stream-upload.md / export-presign.md / jobs-relay-write-side.md (where failure envelopes surface).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "DataExportProcessor exportAs includeByteOrderMark elapsedTime", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt orchestration-only processors, format-driven option gating, and identity-carrying non-Error failure envelopes; adapt format names; omit the REST trigger unless porting it too. Coverage caveat: no in-repo unit tests; source-grounded.
