<!-- capsule-v2 -->
# API serializer boundary — what does transformLink guarantee that raw Prisma rows don't?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** Where do DB rows become API responses, and which legacy/derived fields are manufactured there?

## transformLink — one exit shape for every link response
**Path/Symbol:** `apps/web/lib/api/links/utils/transform-link.ts:ExpandedLink/transformLink` (13-69).
**Signature:** `transformLink(link: ExpandedLink, { skipDecodeKey = false } = {}): TransformedLink`.
**Data Shape:** input = Prisma `Link` + optional relations (`tags: {tag}[]`, `webhooks: {webhookId}[]`, `dashboard`, `partner`, `discount`, `programEnrollment`); output = flat row with relations folded to scalars/arrays.

### Decisive source
```ts
const tags = (link.tags || []).map(({ tag }) => tag);            // join-table rows -> tag rows
const webhookIds = link.webhooks?.map(({ webhookId }) => webhookId) ?? [];

if (!skipDecodeKey) link = decodeLinkIfCaseSensitive(link);      // storage key -> display key

const { webhooks, dashboard, partnerGroupDefaultLinkId,
        // hide undocumented fields from the API response for now
        lastLeadAt, lastConversionAt, programEnrollment, ...rest } = link;

return {
  ...rest,
  saleAmount: toCentsNumber(rest.saleAmount),   // integer cents -> decimal-major string
  identifier: null,                              // backwards-compat stub (removed field)
  tagId: tags?.[0]?.id ?? null,                  // backwards-compat first-tag mirror
  tags,
  webhookIds,
  qrCode: `https://api.dub.co/qr?url=${link.shortLink}?qr=1`,   // DERIVED, never stored
  workspaceId: link.projectId ? prefixWorkspaceId(link.projectId) : null, // renamed + prefixed
  ...(dashboard && { dashboardId: dashboard.id || null }),
};
```

**Flow:** decode (unless caller opts out — e.g. GET /links/[linkId] passes `skipDecodeKey: true` because it already fetched by display key) → destructure OUT internal/join shapes (`webhooks[]`, `dashboard` object, `programEnrollment`, undocumented telemetry fields) → fold in derived/back-compat fields → return.
**Invariant:** Every link-shaped API response exits through this ONE function; internal column names never leak (`projectId`→prefixed `workspaceId`), join tables collapse to plain arrays, and REMOVED public fields are re-synthesized as null/stubs rather than dropped so old SDKs keep parsing. Derived values (qrCode) are computed at serialization time — storing them would rot when the QR host changes. The `skipDecodeKey` escape exists because decoding must be idempotent-per-source: a row already fetched BY its decoded key would double-decode into garbage.
**Probe:** exercised by nearly every integration suite (`tests/links/retrieve-link.test.ts` asserts serialized fields incl. qrCode/tag mirrors). Deterministic probe: transform of a row with `tags: []` yields `tagId: null, tags: []`; with `dashboard: null` yields NO dashboardId key (spread guard).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "transformLink ExpandedLink", limit: 5 });
// → utils.transform-link.transformLink @ 35-69 · ExpandedLink Type @ 13-32
```

## Verdict
Adopt a single serializer at the API boundary: rename internal columns, fold joins to arrays, synthesize removed-field stubs for back-compat, derive volatile URLs on read, and gate reversible transforms with an explicit skip flag. Adapt field names/prefixes. Omit the cents conversion without money fields.
