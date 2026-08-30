<!-- capsule-v2 -->
# Job producer controllers — what does the enqueue-side contract look like for export/duplicate/migrate/sync, and which guards run BEFORE add()?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How do thin HTTP controllers turn requests into typed queue jobs, and what pre-flight checks belong in the controller rather than the processor?

## Fast-ack producers with controller-owned pre-flight
**Path/Symbol:** `data-export/data-export.controller.ts:exportModelData` (:36-82); `data-export/public-data-export.controller.ts` (:30-84) — untyped-body caveat comment (:62-67) + `restrictSharedViewQueryForView`; `export-import/duplicate.controller.ts:duplicateSharedBase` (:52-110) vs delegated `duplicateBase` (:112-133); parent-audit-id threading in duplicateModel (:135-176); `export-import/migrate.controller.ts:validateMigrationUrl` (:44-70); `at-import/at-import.controller.ts:triggerSync` (:29-55) + empty abort (:57-60).
**Signature:** all return `{id}` (or `{id, base_id}`) from `jobsService.add(JobTypes.X, payload)`; guards stack `MetaApiLimiterGuard, GlobalGuard` (public variant: only `PublicApiLimiterGuard`).
**Data Shape:** payloads are id-only envelopes (`modelId/viewId/user/exportAs/ncSiteUrl/locale/options`) — entities rehydrate inside processors (see webhook-decoupling).

### Decisive source
```ts
// public-data-export.controller.ts
// `options` is an @Body() TS interface, not a class DTO, so nothing upstream
// strips unknown keys — `filterArrJson` / `sortArrJson` arrive verbatim and
// reach `datasService.dataList` in the export processor. The shared-view UI
// legitimately sends the viewer's own filters/sorts here, so confine them to
// the view's columns rather than dropping them.
const exportOptions = { ...(options ?? {}) };
await restrictSharedViewQueryForView(context, { view, query: exportOptions });
const job = await this.jobsService.add(JobTypes.DataExport, { context,
  options: { ...exportOptions, includeByteOrderMark: true, isPublicExport: true }, … });
```
```ts
// duplicate.controller.ts — JOB-status placeholder pattern:
const dupProject = await this.basesService.baseCreate({ base: {
  title: uniqueTitle, status: ProjectStatus.JOB, … }});   // UI polls THIS base id
const job = await this.jobsService.add(JobTypes.DuplicateBase, { …,
  options: { ...body.options, excludeHooks: true }, req }); // hooks never survive duplication
// audit threading: req.ncParentAuditId = parentAuditId (minted nanoid + AppEvents emit)
```

**Flow:** resolve + authorize the anchor entity → run controller-tier guards (shared-view password + allowCSVDownload; migration URL protocol/origin/secret parse; sandbox refusal; sync already-in-progress scan of `jobList()`) → shape the options envelope (BOM + isPublicExport flags set HERE, not in processors) → enqueue → return the job id immediately. Duplicate-shared-base additionally creates a real placeholder base with `status: JOB` so the UI has something to poll before the async copy finishes.
**Invariant:** transport defaults and security confinement are CONTROLLER concerns: BOM-on, ICS column narrowing flag, filter confinement to the view's columns (the @Body interface strips nothing — unknown keys flow to the processor verbatim), and hook exclusion on duplicates. `abortImport` returning `{}` is an intentional no-op API surface, not a stub bug. Audit ids minted pre-enqueue let start-events correlate even if enqueue fails.
**Probe:** no unit test upstream. Source-grounded probe: DTO caveat comment :62-67; FORM-view 404 + password verify :37-46; `status: ProjectStatus.JOB` :77; protocol allowlist migrate.controller :51-53.
**Coverage caveat:** no in-repo tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "DataExportController restrictSharedViewQueryForView duplicateSharedBase ProjectStatus.JOB", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fast-ack id-only envelopes with controller-owned guard/flag shaping; adapt guard stacks to your auth tiers; omit the placeholder-base trick if your UI polls jobs directly.
