<!-- capsule-v2 -->
# Tombstone analytics ingestion — what exactly is written to Tinybird when a link is created, updated, or deleted?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** What is the wire shape of the link-metadata event stream, and how are deletes represented?

## recordLink — typed ingest endpoint with null-to-empty normalization
**Path/Symbol:** `apps/web/lib/tinybird/record-link.ts:dubLinksMetadataSchema/transformLinkTB/recordLink` (6-89).
**Signature:** `recordLink(payload: ExpandedLink | ExpandedLink[], { deleted?: boolean } = {})` → `tb.buildIngestEndpoint({ datasource: "dub_links_metadata", event: dubLinksMetadataSchema, wait: true })`.
**Data Shape:** flat denormalized row: `link_id, domain, key, url, tag_ids[], folder_id, tenant_id, program_id, partner_id, partner_group_id, partner_tag_ids[], workspace_id, created_at (space-separated datetime), deleted (0|1)`.

### Decisive source
```ts
const recordLinkTB = tb.buildIngestEndpoint({
  datasource: "dub_links_metadata", event: dubLinksMetadataSchema, wait: true,
});

const transformLinkTB = (link: ExpandedLink) => ({
  link_id: link.id,
  domain: link.domain,
  key: decodeKeyIfCaseSensitive({ domain: link.domain, key: link.key }), // ANALYTICS see the human key
  url: link.url,
  tag_ids: link.tags?.map(({ tag }) => tag.id) ?? [],
  folder_id: link.folderId ?? "",
  tenant_id: link.tenantId ?? "",       // zod .nullish().transform(v => v ? v : "")
  program_id: link.programId ?? "",
  workspace_id: link.projectId,
  created_at: link.createdAt,           // schema transforms Date -> "YYYY-MM-DD HH:mm:ss" (T/Z stripped)
  ...
});

if (Array.isArray(payload)) {
  return await recordLinkTB(payload.map(transformLinkTB).map((p) => ({ ...p, deleted })));
}
return await recordLinkTB({ ...transformLinkTB(payload), deleted });
```
Delete call site (delete-link.ts:62): `recordLink(link, { deleted: true })` — the FULL row is re-emitted with `deleted: 1`.

**Flow:** callers (create :157, update :186, bulk propagate, delete :62) hand full ExpandedLink rows; transform flattens relations to id arrays, decodes case-sensitive keys back to display form, coerces every nullable column to empty-string/array defaults; the zod schema enforces types AND materializes defaults (`deleted.default(false)` → 0/1) at ingest time; single vs batch is one branch over the same endpoint.
**Invariant:** Analytics is a MATERIALIZED COPY, not a foreign key: every mutation re-emits the whole row (last-write-wins in Tinybird replays), and deletion is a TOMBSTONE (`deleted=1`) because append-only warehouses can't UPDATE. Nullable relational ids become empty STRINGS not SQL NULLs (Tinybird columns are non-nullable), booleans are ints. The key is decoded BEFORE ingest so warehouse groupings match user-visible slugs. `wait: true` trades latency for delivery certainty inside the caller's waitUntil budget — the click-side twin (recordClick) uses `wait=true` too but treats Redis as the durability net.
**Probe:** no direct unit test (coverage caveat — asserted indirectly through create/delete integration tests' side-effect expectations). Deterministic probe: `transformLinkTB` of a link with `tags: []`, `folderId: null` yields `tag_ids: []`, `folder_id: ""`; array payload maps EVERY element then stamps one shared `deleted` flag.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "createLink updateLink linkCache recordLink", limit: 6 });
// → tinybird.record-link.recordLink @ record-link.ts 78-89
```

## Verdict
Adopt tombstone-style append-only metadata sync: full-row re-emit per mutation, explicit deleted flag, null→empty-string coercion at a schema-validated ingest boundary, relation flattening to id arrays. Adapt the transport (Tinybird → your OLAP ingester). Omit the case-decode step if keys need no reverse transform downstream.
