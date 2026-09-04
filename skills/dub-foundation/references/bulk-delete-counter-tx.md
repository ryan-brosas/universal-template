<!-- capsule-v2 -->
# Bulk delete with counter transaction and batched side effects — how do you delete N links across related tables while keeping usage counters exact?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** What is the canonical ordering of dependency cleanup, row deletion, counter decrement, and cache/analytics invalidation for mass deletes?

## bulkDeleteLinks — batches of 100, tx per batch
**Path/Symbol:** `apps/web/lib/api/links/bulk-delete-links.ts:bulkDeleteLinks` (22-70) + `deleteLinksBatch` (72-120); route filter `apps/web/app/api/links/bulk/route.ts:DELETE` (512-604).
**Signature:** `bulkDeleteLinks(links: ExpandedLink[]): Promise<{deletedCount: number}>`.
**Data Shape:** constant `DELETE_LINKS_BATCH_SIZE = 100`; callers MUST pass links from a single workspace (counter decrements `links[0].projectId`). Side-effect fan-out: Redis `linkCache.deleteMany`, Tinybird `recordLink(links, {deleted:true})`, R2 image deletes.

### Decisive source
```ts
// doc comment IS the contract:
// 1. Delete related DiscountCodes (and enqueue provider cleanup)
// 2. Delete Link rows + decrement totalLinks (transaction)
// 3. Run side effects (Redis / Tinybird / R2)  — batched at 100
const { count: deletedCount } = await prisma.$transaction(async (tx) => {
  const result = await tx.link.deleteMany({ where: { id: { in: linkIds } } });
  if (result.count > 0 && workspaceId) {
    await tx.project.update({
      where: { id: workspaceId },
      data: { totalLinks: { decrement: result.count } },   // ACTUAL count, not requested
    });
  }
  return result;
});

if (deletedCount > 0) {          // side effects ONLY if something really died
  waitUntil(Promise.allSettled([
    linkCache.deleteMany(links),
    recordLink(links, { deleted: true }),
    ...links.filter((l) => l.image?.startsWith(`${R2_URL}/images/${l.id}`))
      .map((l) => storage.delete({ key: l.image!.replace(`${R2_URL}/`, "") })),
  ]));
}
```

**Flow:** route resolves `linkIds` + `ext_`-prefixed externalIds → fetch full rows → drop links whose folder the user can't write (silently excluded, no error rows) → always exclude root-domain keys (`isRootDomainLinkKey`) → chunk into 100s; per chunk: discount codes deleted first (with provider cleanup enqueue), then rows+counter in ONE interactive transaction → aggregate real count → post-response allSettled cleanup.
**Invariant:** counter decrement uses `result.count` from INSIDE the transaction — never the input array length (folder-filtered/root-excluded links were never deleted). Discount-code cleanup strictly precedes row deletion (dangling references otherwise). Cache/analytics/image effects are best-effort (`allSettled`) and fire only when `deletedCount > 0`. Root-domain links are undeletable via this path by policy, not by DB constraint.
**Probe:** no direct upstream unit test (coverage caveat). Deterministic probe: request 3 ids where 1 is a `_root` key and 1 is missing → `deletedCount === 1`; project.totalLinks decremented by exactly 1.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "bulkDeleteLinks deleteLinksBatch DELETE_LINKS_BATCH_SIZE totalLinks", limit: 10 });
```

## Verdict
Adopt: dependency-first cleanup, delete+decrement in one interactive tx using the REAL affected count, batching at ~100, gated best-effort side effects, silent policy exclusions before write. Adapt relation tables and storage layer to your schema; keep the single-workspace precondition or generalize the counter update. Omit discount/provider cleanup if you have no promo-code coupling.
