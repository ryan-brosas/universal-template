<!-- capsule-v2 -->
# getOrgUsageSummary & doc-limit status aggregation — how does an org's usage page get computed without a counter table?

**Source:** grist-core MIT `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Where do "docs approaching/exceeding limits" counts and attachment totals come from?

## Scan live docs, classify each via getDataLimitInfo against effective product features, bucket client-side; attachments summed in the same pass
**Path/Symbol:** `app/gen-server/lib/homedb/HomeDBManager.ts`: `getOrgUsageSummary` (:862–903), non-removed doc query (:875–883), merged-org owner filter (:881–883), `createEmptyOrgUsageSummary` bucketing (:888–901).
**Signature:** `getOrgUsageSummary(scope, orgKey) => Promise<OrgUsageSummary>` — requires OWNER (markPermissions: Permissions.OWNER).
**Data Shape:** summary = `{countsByDataLimitStatus: {[status]: number}, attachments: {totalBytes, limitExceeded?}}`; per-doc inputs `{usage: docUsage, gracePeriodStart}` + org-level `productFeatures`.

### Decisive source
```ts
// Return an aggregate count of documents, grouped by data limit status.
const summary = createEmptyOrgUsageSummary();
let totalAttachmentsSizeBytes = 0;
for (const { usage: docUsage, gracePeriodStart } of docs) {
  const dataLimitStatus = getDataLimitInfo({ docUsage, gracePeriodStart, productFeatures }).status;
  totalAttachmentsSizeBytes += docUsage?.attachmentsSizeBytes ?? 0;
  if (dataLimitStatus) { summary.countsByDataLimitStatus[dataLimitStatus] += 1; }
}
const maxAttachmentsBytesPerOrg = productFeatures.maxAttachmentsBytesPerOrg;
summary.attachments = { totalBytes: totalAttachmentsSizeBytes };
if (maxAttachmentsBytesPerOrg && totalAttachmentsSizeBytes > maxAttachmentsBytesPerOrg) {
  summary.attachments.limitExceeded = true;
}
```

**Flow:** owner-gated org verify (`needRealOrg`) → features pulled via `_addFeatures` → all org docs with `removed_at IS NULL` on BOTH workspace and doc → in-process classification loop. Merged personal orgs scope docs to the requesting user's OWN docs (`orgs.owner_id = :userId`) since the pseudo-org spans everyone.
**Invariant:** Usage is DERIVED at read time from per-doc usage snapshots (written by HostedMetadataManager via setDocsMetadata), never incremented transactionally — eventual consistency by design. The classification function lives in common/ so the CLIENT repeats it for per-doc badges; server and UI must share one copy or badges disagree with the summary.

### Probe (direct tests)
`bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "getOrgUsageSummary" app/gen-server/lib/homedb/HomeDBManager.ts | head -1'` → :862.
`bash -c 'grep -rn "getOrgUsageSummary\|countsByDataLimitStatus" test/ --include="*.ts" -l | head -3'` → coverage files.
Direct tests: ApiServer usage-summary its (grep countsByDataLimitStatus in test/gen-server/).

### Retrieve
`codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"getOrgUsageSummary getDataLimitInfo countsByDataLimitStatus attachmentsSizeBytes","limit":8,"detail":"ids"}'`

**Verdict:** ADAPT — derived-usage aggregation pattern; small but completes the limits story started in homedb-product-feature-limits.
