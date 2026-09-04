<!-- capsule-v2 -->
# Discount-code deletion funnel — how do you delete a code locally, decide provider cleanup, and support soft-delete in one entry point?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1` (drift pass — deleteLink/bulkDeleteLinks were rewired onto this funnel). **Question:** What is the single correct sequence for removing discount codes across local DB, external providers, and webhooks?

## deleteDiscountCodes: soft/hard branch + provider-known filter
**Path/Symbol:** `apps/web/lib/discounts/delete-discount-code.ts:deleteDiscountCodes` (:33-93) and `enqueueDeleteDiscountCode` (:99-128).
**Signature:** `deleteDiscountCodes(input: (DeleteDiscountCodesParams | null | undefined)[], { isSoftDelete } = {})`; `enqueueDeleteDiscountCode(codes: { code, programId, discount: Pick<Discount,"provider"> | null }[])`.
**Data Shape:** input rows carry the joined `discount` relation (or null for orphans); soft-delete stamps `disabledAt`.

### Decisive source
```ts
if (isSoftDelete) {
  const disabledAt = new Date();
  await prisma.discountCode.updateMany({ where: { id: { in: ids } },
    data: { disabledAt } });                    // mark disabled, keep the row
  waitUntil(sendDiscountCodeDeletedWebhooks(codes.map(dc => ({ ...dc, disabledAt }))));
} else {
  const deleted = await prisma.discountCode.deleteMany({ where: { id: { in: ids } } });
  waitUntil(sendDiscountCodeDeletedWebhooks(discountCodes));
}
await enqueueDeleteDiscountCode(discountCodes);

// Only enqueue external-provider cleanup for codes whose provider is known.
// Orphaned codes ... still get deleted locally ... but we can't tell which external
// provider to clean up, so we skip them. Custom providers disable via webhook.
const codesWithProvider = discountCodes.filter(
  (dc) => dc.discount != null && dc.discount.provider !== DiscountProvider.custom);
```

**Flow:** null-filter → soft path (updateMany disabledAt + webhook with the stamp) OR hard path (deleteMany + webhook) → ALWAYS enqueue chunked batch jobs (`queueName: "delete-discount-code"`, chunks of 100) to revoke at the external provider. Callers: link deletion calls this BEFORE deleting the link row; partner ban/deactivation uses `isSoftDelete: true`; group moves hard-delete.
**Invariant:** provider cleanup is best-effort and provider-gated — orphaned codes (null discount relation) are still removed locally but silently skip external revocation, and the `custom` provider is NEVER queued because Dub itself is the source of truth ("external apps disable coupons via webhook" — see `discount-provider-custom.ts`, whose `disableDiscountCode` is an intentional no-op). Webhooks fire under `waitUntil` with the SAME visibility the DB write produced (soft-deleted rows announce their disabledAt). The old pattern of inlining `discountCode.delete` inside the link's transaction is gone: local removal happens through THIS funnel so every caller gets identical webhook/job semantics.
**Probe:** `playwright/api/discount-codes/discount-codes.spec.ts` covers CRUD end-to-end; no unit test pins the orphan-skip branch directly — coverage caveat; deterministic probe: delete a link holding an orphaned code ⇒ code row gone, zero jobs enqueued on the `delete-discount-code` queue.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "deleteDiscountCodes enqueueDeleteDiscountCode", limit: 6 });
// → lib.discounts.delete-discount-code.deleteDiscountCodes @ delete-discount-code.ts 27-110
```

## Verdict
Adopt one deletion funnel with explicit soft/hard branches, provider-known filtering, and custom-provider-as-webhook-noop. Adapt provider enum to your integrations. Omit soft-delete if your domain has no disabled-but-auditable state.
