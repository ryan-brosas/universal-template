<!-- capsule-v2 -->
# Bulk create with index-preserving result assembly — how do you createMany N rows (skipping duplicates), then return FULL records in the caller's original order?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** Prisma `createMany` returns counts, not rows — how does dub recover full created rows (with relations), keep API response order stable, and stay idempotent on partial duplicates?

## bulkCreateLinks shortLink→index map + refetch
**Path/Symbol:** `apps/web/lib/api/links/bulk-create-links.ts:bulkCreateLinks` (17-247); propagation helper `propagate-bulk-link-changes.ts:propagateBulkLinkChanges` (5-18).
**Signature:** `bulkCreateLinks({links: ProcessedLinkProps[], skipRedisCache? = false}): Promise<ExpandedLink[]>`.
**Data Shape:** input links already validated by `processLink` per-link (errors filtered upstream); identity key is `shortLink` = `https://domain/key` with case-sensitive keys punycode-encoded via `encodeKeyIfCaseSensitive`. Relation tables filled: `linkTag` (createdAt staggered +100ms per tag for ordering), `linkWebhook`.

### Decisive source
```ts
// 1. map shortLink → ORIGINAL array position BEFORE writing
const shortLinkToIndexMap = new Map(links.map((link, index) => {
  const key = encodeKeyIfCaseSensitive({ domain: link.domain, key: link.key });
  return [linkConstructorSimple({ domain: link.domain, key }), index];
}));

// 2. count-only insert; duplicates silently skipped (idempotent re-submit)
await prisma.link.createMany({ data: /* ... */, skipDuplicates: true });

// 3. refetch REAL rows (ids are server-generated) by shortLink membership
let createdLinksData = await prisma.link.findMany({
  where: { shortLink: { in: Array.from(shortLinkToIndexMap.keys()) } },
  include: { ...includeProgramEnrollment },
});

// 4. relations built from the ORIGINAL payloads via the same map ...
// 5. restore caller's order — DB has no such guarantee
createdLinksData = createdLinksData.sort((a, b) => {
  const aIndex = shortLinkToIndexMap.get(a.shortLink) ?? -1;
  const bIndex = shortLinkToIndexMap.get(b.shortLink) ?? -1;
  return aIndex - bIndex;
});
```
```ts
// cache+analytics propagation is post-response, never blocking
waitUntil(Promise.all([
  propagateBulkLinkChanges({ links: createdLinksData, skipRedisCache }),
  publishWorkspaceLinksUsageEvent({ workspaceId: links[0].projectId!, /* ... */ }),
]));
```

**Flow:** validate upstream → index map → createMany(skipDuplicates) → refetch by shortLink IN → create linkTag/linkWebhook rows for surviving links (tagNames resolved to ids via one workspace-scoped query, lowercase-normalized map) → final refetch WITH relations when tags/webhooks exist → waitUntil'd Redis mset + Tinybird recordLink + usage stream event → sort to input order → transformLink each.
**Invariant:** response order MUST equal request order (clients zip results against their input) — guaranteed only by the explicit sort over the precomputed map. `skipDuplicates: true` means a duplicate shortLink neither throws nor appears in output; the map-based refetch naturally excludes it. Tag ordering inside a link is enforced by staggered createdAt (+100ms), NOT by array position alone. Heavy side effects (cache/analytics/usage) ride `waitUntil` so latency is write-only.
**Probe:** no direct upstream unit test (coverage caveat; route-level integration only). Deterministic probe: submit `[A,B]` where B duplicates an existing row → response contains exactly A at index 0; submit 100 shuffled links → response order matches request order.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "bulkCreateLinks shortLinkToIndexMap propagateBulkLinkChanges skipDuplicates", limit: 10 });
```

## Verdict
Adopt the whole pattern for any bulk-insert API: identity-map before insert, count-only createMany with skipDuplicates, refetch-by-identity, relation backfill keyed through the same map, deterministic order restoration, post-response propagation. Adapt identity field (shortLink → your natural key), relation tables, and propagation targets. Omit usage-stream publishing if you meter differently.
