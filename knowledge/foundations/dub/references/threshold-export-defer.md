<!-- capsule-v2 -->
# Threshold-defer CSV export — when does an export route answer inline and when does it hand off to a QStash worker?

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** How does a CSV export endpoint stay under request-time limits for both 10-row and 1M-row workspaces without a streaming response?

## Count-probe → inline-or-202 branch
**Path/Symbol:** `apps/web/app/api/links/export/route.ts:GET` (:19-:97) and twin `apps/web/app/(ee)/api/events/export/route.ts:GET` (:25-:182).
**Signature:** `GET = withWorkspace(async ({ searchParams, workspace, session }) => Response)` / events variant identical shape.
**Data Shape:** query params parsed by `linksExportQuerySchema` / (`eventsQuerySchema` + local `exportQuerySchema` for `columns`); count is a number from `getLinksCount` or `getAnalytics({groupBy:"count"})`; output is either an inline `text/csv` Response or `{}` with status 202.

### Decisive source
```ts
const MAX_LINKS_TO_EXPORT = 1000;
...
if (linksCount > MAX_LINKS_TO_EXPORT) {
  await qstash.publishJSON({
    url: `${APP_DOMAIN_WITH_NGROK}/api/cron/export/links`,
    body: { ...searchParams, workspaceId: workspace.id, userId: session.user.id },
  });
  return NextResponse.json({}, { status: 202 });
}
```

**Flow:** parse → count probe (same filter set as the eventual data fetch) → if count ≤ threshold, fetch ≤1000 rows, format, `convertToCSV`, stream inline; else publish the RAW searchParams plus workspaceId/userId to QStash and return 202 (client polls/polls email). The events variant computes `dataAvailableFrom = min([workspace.createdAt, programStartedAt])` (:73) before probing so program-scoped exports can't read past either boundary, then projects columns through `eventsExportColumnNames[c] ?? capitalize(c)` + `eventsExportColumnAccessors[c]?.(row) ?? row?.[c]` (:163).
**Invariant:** the count probe and the deferred worker MUST evaluate the same filter set — the probe's number is only truthful for the job it spawns. Threshold is strict `>` : exactly 1000 still answers inline.
**Probe:** no direct unit test (coverage caveat). Deterministic anchors at pin: `MAX_LINKS_TO_EXPORT = 1000` links/export :19, `status: 202` :59, strict-inline `pageSize: MAX_LINKS_TO_EXPORT` :78; events twin `MAX_EVENTS_TO_EXPORT = 1000` :25, `groupBy: "count"` :122, `eventsExportColumnAccessors[c]?.(row) ?? row?.[c]` :163.

## Worker half: authorization re-derived, paged by full-page continuation
**Path/Symbol:** `apps/web/app/(ee)/api/cron/export/links/route.ts:POST` (:28-:156); `fetch-links-batch.ts:fetchLinksBatch` (:6-:28).
**Signature:** `function* fetchLinksBatch(filters: Omit<GetLinksForWorkspaceProps,"page"|"pageSize">, pageSize = 1000): AsyncGenerator<{links}>`.
**Data Shape:** body carries ids only (`columns`, `workspaceId`, `userId`, filters); worker re-fetches User (must have email) and Project (selecting `users.role/defaultFolderId`) then rebuilds RBAC itself.

### Decisive source
```ts
while (hasMore) {
  const links = await getLinksForWorkspace({ ...filters, page, pageSize });
  if (links.length > 0) {
    yield { links };
    page++;
    hasMore = links.length === pageSize;   // full page ⇒ maybe more
  } else { hasMore = false; }
}
```

**Flow:** verifyQstashSignature on rawBody → re-derive user/workspace by id → **re-run `validateLinksQueryFilters` inside the worker** (:83) to rebuild folderIds in execution context → generator loop accumulates `formatLinksForExport` rows → one `convertToCSV` → `createDownloadableExport` (R2) → `ExportReady` email → logAndRespond.
**Invariant:** RBAC is recomputed at execution time from ids, never inherited from the HTTP request — folder permissions may have changed between 202 and job run. Termination requires `getLinksForWorkspace` to be stable under keyset-free offset paging (rows created mid-export can shift pages; accepted here because export is eventually-consistent by design).
**Probe:** anchors observed live: `validateLinksQueryFilters` cron route :83, `hasMore = links.length === pageSize` fetch-links-batch :23, default `pageSize: number = 1000` :8.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "links export route", file_pattern: "*export*", limit: 10 });
await mcp.codebase_memory.trace_path({ project: "dub", function_name: "getFolderIdsToFilter", direction: "inbound", depth: 3 });
```

## Verdict
Adopt the count-probe→inline-or-202 split with raw-params handoff and worker-side authorization re-derivation; adopt the full-page-continuation generator for offset paging. Adapt thresholds (1000) and storage/email delivery to host capabilities; omit dub-specific column registries (`exportLinksColumns`, `eventsExportColumnAccessors`). Coverage caveat: routes are integration-tested only (CI-gated harness), no direct unit test at pin.
