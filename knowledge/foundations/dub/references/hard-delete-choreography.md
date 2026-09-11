<!-- capsule-v2 -->
# Hard-delete cleanup choreography — how do you delete a primary row plus its blob, cache entry, counter, and warehouse copy without orphaning any of them?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1` (re-pinned in drift pass 4 — upstream MOVED discount-code removal out of the link transaction onto the shared deletion funnel; prior pin `873edc5a` showed an inline dependents-first `$transaction`); Codebase Memory `dub`. **Question:** What is deleteLink's delete ordering, and which cleanups are allowed to be eventual?

## deleteLink — funnel-first dependent removal, then a bare link delete, then allSettled fan-out
**Path/Symbol:** `apps/web/lib/api/links/delete-link.ts:deleteLink` (:12-66, whole function).
**Signature:** `deleteLink(linkId: string): Promise<TransformedLink>` (route guard: root-domain links refuse deletion — `[linkId]/route.ts`).
**Data Shape:** pre-fetch with relations (`includeTags`, `includeProgramEnrollment`, `discountCode.discount`) so cleanups have everything they need BEFORE the row disappears.

### Decisive source
```ts
const link = await prisma.link.findUniqueOrThrow({ where: { id: linkId },
  include: { ...includeTags, ...includeProgramEnrollment, discountCode: { include: { discount: true } } } });

if (link.discountCode) {
  await deleteDiscountCodes([link.discountCode]);   // shared funnel: local delete/soft-disable
}                                                   // + webhook + provider-revoke jobs

await prisma.link.delete({ where: { id: linkId } }); // standalone; NOT bundled in a $transaction anymore

waitUntil(Promise.allSettled([
  link.image && link.image.startsWith(`${R2_URL}/images/${link.id}`) && storage.delete(...),
  linkCache.delete(link),
  recordLink(link, { deleted: true }),               // tombstone into Tinybird
  link.projectId && prisma.project.update({ where: { id: link.projectId },
    data: { totalLinks: { decrement: 1 } } }),       // usage counter OUTSIDE any tx
]));
return transformLink(link);
```

**Flow:** snapshot-with-relations → dependent removal through the `deleteDiscountCodes` funnel (which itself does the local DB write, fires the deleted webhook under waitUntil, and enqueues chunked provider revocation) → single bare link delete → async fan-out: ownership-checked blob GC (`startsWith(R2/images/<id>)`), cache eviction, warehouse tombstone, atomic counter decrement → return the pre-fetch transform.
**Invariant:** ordering is still dependents-BEFORE-primary, but cross-row atomicity was deliberately traded for funnel consistency — every caller of code removal gets identical webhook/job semantics via one entry point, even though the code and link deletes are no longer one transaction. EVERY cross-system artifact (blob store, Redis, OLAP, counters) remains eventual and individually non-fatal under allSettled; consistency is restored by replaying idempotent cleanups rather than compensating transactions. The blob GC predicate doubles as an ownership check so a poisoned `image` column can never delete another object. Counter decrement stays outside all transactions. Porting note: if YOUR store needs the two deletes atomic, wrap funnel-local-write + link-delete yourself — upstream accepted a window where the code is gone but the link survives.
**Probe:** direct integration tests `tests/links/delete-link.test.ts:9 "DELETE /links/{linkId}"` (200 `{id}` envelope) and `:38 "cannot delete root link"` (403 forbidden). Funnel branch (code present) uncovered upstream — coverage caveat; deterministic probe: after deleteLink on a link with a code, BOTH rows are gone and one `delete-discount-code` job batch was enqueued.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "deleteLink recordLink deleted", limit: 6 });
// → lib.api.links.delete-link.deleteLink @ delete-link.ts 12-66 (+ IntegrationHarness.deleteLink test twins)
```

## Verdict
Adopt snapshot-before-delete, dependents-first ordering THROUGH a shared deletion funnel, ownership-predicated blob GC, and idempotent eventual cleanups under allSettled. Adapt which artifacts exist in your stack; decide explicitly whether your store demands re-bundling the tx upstream gave up. Omit the discount/provider branch without commerce.
