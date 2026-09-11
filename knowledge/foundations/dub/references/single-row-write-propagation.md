<!-- capsule-v2 -->
# Single-row write with post-commit side effects — how does one link create/update keep Redis, Tinybird, R2 and cron work OFF the response path without losing them?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** What exactly happens inside createLink/updateLink after the row is written, and what invariants keep the eventual-consistency fan-out safe?

## createLink / updateLink — write, then waitUntil(allSettled)
**Path/Symbol:** `apps/web/lib/api/links/create-link.ts:createLink` (26-231); `apps/web/lib/api/links/update-link.ts:updateLink` (23-234).
**Signature:** `createLink(link: ProcessedLinkProps): Promise<TransformedLink>`; `updateLink({ oldLink: { domain, key, image?, testCompletedAt? }, updatedLink: ProcessedLinkProps & Pick<LinkProps,"id"|"clicks"|"lastClicked"|"updatedAt"> }): Promise<TransformedLink>`.
**Data Shape:** Prisma create/update with nested writes (tags `create`/`createMany` with `createdAt = now + idx*100ms` to encode ORDER; webhooks `createMany`; dashboard created inline when `publicStats`). Response is `transformLink(response)` PLUS an optimistic `image` swap to the not-yet-uploaded `${R2_URL}/images/${id}`.

### Decisive source
```ts
// CREATE: uploaded images are stored NULL first, swapped by the async upload
image: proxy && image && isNotHostedImage(image) ? null : image,
...
waitUntil((async () => {
  const { partner, discount } = await getPartnerEnrollmentInfo({...});
  await Promise.allSettled([
    linkCache.set({ ...response, ...(partner && { partner }), ...(discount && { discount }) }),
    recordLink({ ...response, /* + programEnrollment projection when partner */ }),
    // proxy uploads: R2 PUT at images/<id> then a SECOND prisma update to fill the URL
    ...(proxy && image && isNotHostedImage(image) ? [
      storage.upload({ key: `images/${response.id}`, body: image, opts: { width: 1200, height: 630 } }),
      prisma.link.update({ where: { id: response.id }, data: { image: uploadedImageUrl } }),
    ] : []),
    !response.userId && qstash.publishJSON({            // anonymous links self-destruct
      url: `${APP_DOMAIN_WITH_NGROK}/api/cron/links/delete`, delay: 30 * 60,
      body: { linkId: response.id },
    }),
    link.projectId && publishWorkspaceLinksUsageEvent({ workspaceId: link.projectId, linksCount: 1, ... }),
    testVariants && testCompletedAt && scheduleABTestCompletion(response),
  ]);
})());
```
```ts
// UPDATE: identity-change detection drives cache invalidation
const changedKey = key.toLowerCase() !== oldLink.key.toLowerCase();
const changedDomain = domain !== oldLink.domain;
const imageUrlNonce = nanoid(7);   // cache-busting suffix for re-uploads
// stored image PRE-NAMED with the nonce (no null phase like create)
image: proxy && image && isNotHostedImage(image) ? `${R2_URL}/images/${id}_${imageUrlNonce}` : image,
...
(changedDomain || changedKey) && linkCache.delete(oldLink),          // stale address eviction
oldLink.image && oldLink.image.startsWith(`${R2_URL}/images/${id}`) &&
  oldLink.image !== image && storage.delete({ key: oldLink.image.replace(`${R2_URL}/`, "") }), // GC own old blob
changedTestCompletedAt && testVariants && testCompletedAt && scheduleABTestCompletion(response),
```

**Flow:** both functions: DB mutation (withPrismaRetry on create) → `getPartnerEnrollmentInfo` lookup → ONE `Promise.allSettled` inside `waitUntil` for [cache mset, Tinybird recordLink, (image upload/eviction), (cron scheduling), (usage stream)] → return transformed row immediately. Update additionally computes change flags BEFORE writing and threads `oldLink` for invalidation.
**Invariant:** Side effects ride `waitUntil`+`allSettled`: nothing after the DB commit can fail the request, and no single side-effect failure cancels its siblings. Cache and analytics rows are ALWAYS overwritten with the full new record (never patched), so a missed event heals on next write; the ONLY compensating delete is on key/domain change (`linkCache.delete(oldLink)`), otherwise the redirect edge would serve the old destination forever. Image handling differs by design: create stores null then fills (row exists before blob), update pre-computes a nonced URL so concurrent readers never see a half-written key; old blobs are deleted only when they start with `${R2_URL}/images/${id}` (never touch another link's asset). Tag order inside a link is carried by createdAt offsets (+100ms per index), NOT array position.
**Probe:** direct integration pins around these writers: `tests/links/create-link.test.ts:556 "ab testing"` (testVariants/testStartedAt/testCompletedAt round-trip), `:405 "tags"`, `:528 "webhooks"`, `:495 "custom link previews"` (proxy/image); `tests/links/update-link.test.ts:48 "update link using linkId"`, `:87/:119 archive/unarchive`. Async branches (cache delete, R2 GC, qstash delay) have no unit tests — coverage caveat; deterministic probe: PATCH changing only the key ⇒ old shortLink must 404 from cache tier after propagation.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "createLink updateLink linkCache recordLink", limit: 6 });
// → tinybird.record-link.recordLink @ 78-89 · update-link.updateLink @ 23-234 · create-link.createLink @ 26-231 · LinkCache.set @ cache.ts 50-69
```

## Verdict
Adopt commit-then-waitUntil(allSettled) fan-out with full-record cache overwrites, explicit compensating deletes keyed on identity change, nonced/pre-named asset URLs, and optimistic response fields for still-running uploads. Adapt transports (QStash/R2/Tinybird → your queue/blob/warehouse). Omit anonymous-link TTL if you have no public creator flow.
