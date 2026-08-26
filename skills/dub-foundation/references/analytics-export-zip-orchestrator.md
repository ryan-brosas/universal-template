<!-- capsule-v2 -->
# Analytics zip export orchestrator — sequential endpoint walker with skip sets and composite folding

**Source:** dub AGPL-3.0-or-later main@29df217a29631ced4041882a28d2327cc4546f27; Codebase Memory dub. **Question:** How do you export N analytics breakdowns into one downloadable artifact without N parallel warehouse storms or empty-CSV litter?

## Endpoint-set algebra + sequential per-endpoint getAnalytics loop
**Path/Symbol:** apps/web/lib/analytics/export-analytics-to-zip.ts:getAnalyticsExportEndpoints (:36-50) and exportAnalyticsToZip (:52-93).
**Signature:** exportAnalyticsToZip({params, workspaceId, useComposite, skipTopLinksForSingleLink?, skipEndpoints? = ["count"], getAnalyticsParams?, getDataAvailableFrom?, formatRows?}) -> Promise<Buffer> (JSZip nodebuffer).
**Data Shape:** options carry three injection hooks — per-endpoint param override, per-endpoint dataAvailableFrom, final row projection before CSV. PARTNER_PROFILE_SKIP_ENDPOINTS = count + top_partners/top_groups/top_partner_tags/top_folders/top_link_tags (:12-19).

### Decisive source
```ts
for (const endpoint of endpoints) {
  const response = await getAnalytics({
    ...params,
    ...getAnalyticsParams?.(endpoint),   // per-endpoint overrides spread LAST
    workspaceId, groupBy: endpoint,
    event: useComposite ? "composite" : params.event,   // composite folding
    isDeprecatedClicksEndpoint: false,
    ...(getDataAvailableFrom?.(endpoint) && { dataAvailableFrom: getDataAvailableFrom(endpoint) }),
  });
  if (!response || (Array.isArray(response) && response.length === 0)) continue;  // NO file for empty
  const rows = formatRows ? formatRows(response as Record<string, unknown>[]) : response;
  zip.file(endpointMarker + ".csv", convertToCSV(rows));   // source: zip.file(`${endpoint}.csv`, ...)
}
return zip.generateAsync({ type: "nodebuffer" });
```
(export-analytics-to-zip.ts :68-92)

**Flow:** Set(skipEndpoints) minus VALID_ANALYTICS_ENDPOINTS (skipTopLinksForSingleLink additionally drops top_links when params scope a single link) -> strictly sequential await per endpoint (direct test asserts exact call order [timeseries, top_links]) -> empty/undefined responses SKIP silently -> optional formatRows projection -> one CSV per non-empty breakdown -> single nodebuffer.
**Invariant:** sequential, never parallel — each getAnalytics may hit Tinybird AND hydrate from Prisma; the walker must stay backpressure-friendly. Empty result means absent file (consumers see only meaningful breakdowns). Per-endpoint overrides always win over shared params because they spread last.
**Probe:** executed at pin: grep -n DEFAULT_SKIP_ENDPOINTS -> :10,:37,:57; grep -n "zip.file" -> :89; useComposite fold -> :74. Direct test tests/analytics/export-analytics-to-zip.test.ts is PURE-UNIT (vi.mock getAnalytics, no CI gate): skip sets (:21-47), composite true/false propagation (:49-74), sequential order [timeseries,top_links] (:76-118), zip content carries metric columns (:120-175). Runner offline-blocked here (no node_modules) but the test needs NO services once deps exist.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "exportAnalyticsToZip", limit: 15 });
// rank-1 observed: ...export-analytics-to-zip.exportAnalyticsToZip Function 52-93
```

## Verdict
Adopt skip-set endpoint algebra + sequential walking + composite folding + empty-skip. Adapt hook names and archive library. Omit the partner-profile skip list unless you also serve scoped-down profile surfaces.