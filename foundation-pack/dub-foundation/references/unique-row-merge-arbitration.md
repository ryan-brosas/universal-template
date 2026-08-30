<!-- capsule-v2 -->
# Unique-row merge arbitration — how do you merge two partners' program data without colliding on (programId, partnerId) unique rows?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the per-table strategy matrix for moving rows onto a target partner when the target may already have its own row?

## transferPartnerProgramData: batch-move high-volume, single-move low-volume, transfer-else-delete unique
**Path/Symbol:** `apps/web/app/(ee)/api/workflows/merge-partner-accounts/route.ts:transferPartnerProgramData` (:393-486) with helpers `transferRowsInBatches` (:351-366) and `transferIfNotExistElseDelete` (:370-391).
**Signature:** `transferRowsInBatches(updateBatch: () => Promise<number>, { resourceName }): Promise<void>`; `transferIfNotExistElseDelete({ findTarget, transferSource, deleteSource, resourceName })`.
**Data Shape:** `PRISMA_UPDATEMANY_LIMIT = 250` (`lib/cron/index.ts:25`); unique-on-(programId, partnerId) tables here: `programApplicationEvent`, `discoveredPartner`.

### Decisive source
```ts
while (true) {
  const count = await updateBatch();
  if (count < PRISMA_UPDATEMANY_LIMIT) break;   // ONLY exit condition
}
// ...
// Rows unique on (programId, partnerId): move the source row when the target
// has none, otherwise delete it so rewriting enrollment.partnerId cannot collide.
if (await findTarget()) {
  const count = await deleteSource();   // target exists ⇒ drop source row
  return;
}
const count = await transferSource();   // else move it
```
(:359-365 loop; :381-390 arbitration)

**Flow:** all moves share `{ where: { programId, partnerId: sourcePartnerId }, data: { partnerId: targetPartnerId } }` · HIGH-volume (commission/link/customer): `updateMany` with `limit` in count-driven batches run CONCURRENTLY via `Promise.all` · LOW-volume (payout, discountCode, notificationEmail, message, partnerComment): one unbounded updateMany each · UNIQUE tables: findTarget → delete-source vs transfer-source · then `combinePendingPayouts` folds duplicate pending payouts (below).
**Invariant:** (1) the batch loop's only legal exit is `count < limit` — "no error" or "count === 0" would strand rows when exactly N×limit remain; (2) for unique rows you CANNOT rewrite the source row onto an existing target — the pre-check + delete keeps the invariant "one row per (program, partner)" while preserving the target's history; (3) the check-then-move is deliberately not transactional: a race just produces the delete branch next retry (each step re-fetches live state — idempotent re-run); (4) payout folding runs AFTER all moves because duplicates only exist once both partners' payouts sit on the target.
**Probe:** `tests/workflows/merge-partner-accounts-workflow.test.ts` :34-61 links-transfer assertion (source link visible under target after merge); deterministic probe: `grep -c 'PRISMA_UPDATEMANY_LIMIT' apps/web/app/\(ee\)/api/workflows/merge-partner-accounts/route.ts` = 8 (import :7, batch-exit check :362, four `limit:` call-sites :420/:430/:440/:777, two comments).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "transferIfNotExistElseDelete", limit: 5 });
// → ...route.transferIfNotExistElseDelete @ route.ts 370-391
```

## Verdict
Adopt the three-tier table-strategy matrix and the strict `count < limit` batch-exit contract for any ownership migration. Adapt limits/table lists. Omit dub's specific schema.
