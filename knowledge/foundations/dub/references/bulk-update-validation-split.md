<!-- capsule-v2 -->
# Bulk update with per-link validation split — how do you apply ONE payload to many links while reporting per-link failures and never leaving relations half-updated?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** Where does the route's all-or-nothing error contract differ from the per-item result contract, and how are tags/webhooks/images handled inside the per-link update?

## bulk PATCH route + bulkUpdateLinks
**Path/Symbol:** route `apps/web/app/api/links/bulk/route.ts:PATCH` (280-509); executor `apps/web/lib/api/links/bulk-update-links.ts:bulkUpdateLinks` (14-134).
**Signature:** `bulkUpdateLinks({linkIds, data, workspaceId})` (externalIds resolved to ids by the route first); `data: bulkUpdateLinksBodySchema["data"]`.
**Data Shape:** two failure vocabularies: (a) THROW — workspace-level preconditions (`unprocessable_entity` for invalid tag/webhook refs) abort everything; (b) PER-ITEM rows `{error, code, link}` returned alongside successes. Image dedup nonce: `nanoid(7)` shared by all links in one call.

### Decisive source
```ts
// route: missing ids become PER-ITEM errors, invalid refs THROW
let errorLinks = linkIds
  .filter((id) => links.find((link) => link.id === id) === undefined)
  .map((id) => ({ error: "Link not found", code: "not_found", link: { id } }));

// executor: every link updated INDIVIDUALLY with nested relation writes
const updatedLinks = await Promise.all(linkIds.map((linkId) =>
  prisma.link.update({
    where: { id: linkId },
    data: {
      ...rest,
      image: proxy && image && isNotHostedImage(image)
        ? `${R2_URL}/images/${linkIds[0]}_${imageUrlNonce}`   // shared key = one upload
        : image,
      geo: geo === null ? Prisma.DbNull : geo,               // explicit null → DB null
      testVariants: testVariants === null ? Prisma.DbNull : testVariants,
      ...(url && getParamsFromURL(url)),                     // utm_* extracted on url change
      // tagNames vs combinedTagIds: IDs take priority, both replace-all via deleteMany+create
      ...(combinedTagIds && {
        tags: { deleteMany: {}, create: combinedTagIds.map((tagId, idx) => ({
          tagId, createdAt: new Date(new Date().getTime() + idx * 100) })) },
      }),
      ...(webhookIds && {
        webhooks: { deleteMany: {}, create: webhookIds.map((webhookId) => ({ webhookId })) } }),
    },
    include: { ...includeTags, ...includeProgramEnrollment,
               webhooks: webhookIds ? { select: { webhookId: true } } : false },
  })));

waitUntil(Promise.all([ propagateBulkLinkChanges({ links: updatedLinks }),
  proxy && image && isNotHostedImage(image) &&
    storage.upload({ key: `images/${linkIds[0]}_${imageUrlNonce}`, /* ... */ }) ]));
```

**Flow:** resolve id/externalId selectors → not-found becomes per-item rows → workspace-wide ref checks (tags/webhooks/folder permission) THROW before any write → per-link `processLink` re-validation (`skipKeyChecks`, `skipExternalIdChecks` since keys don't change) → surviving ids into `bulkUpdateLinks` → response `[...updatedRows, ...errorRows]`; old proxied images deleted waitUntil'd.
**Invariant:** relation updates use Prisma NESTED writes (`deleteMany` + `create` inside the same `link.update`) so a link's tags/webhooks can never be observed half-swapped; per-link update is atomic even though the BATCH is not. `null` for geo/testVariants means "clear" only via explicit DbNull conversion. The R2 image key derives from `linkIds[0]` + a per-call nonce — all links share ONE upload, so image must be identical across the batch by contract.
**Probe:** no direct upstream unit test (coverage caveat). Deterministic probe: mix of 2 valid + 1 missing id → 200 with 2 updated rows + 1 `{code:"not_found"}` row; invalid tagId in data → whole request 422 with zero writes.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "bulkUpdateLinks bulkUpdateLinksBodySchema processLink skipKeyChecks", limit: 10 });
```

## Verdict
Adopt the two-tier failure model (throw for batch-wide preconditions, per-item rows for item-scoped problems), nested-write relation replacement, explicit-null→DbNull clearing, single-shared-upload image handling. Adapt which checks throw vs degrade to your API's consistency needs. Omit R2/storage specifics if your host differs.
