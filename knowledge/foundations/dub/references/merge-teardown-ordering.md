<!-- capsule-v2 -->
# Merge teardown ordering — why is the source partner deleted with raw SQL last, and when does a fraud group auto-resolve?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What order must account-teardown steps run in, and how do you decide which duplicate-account fraud groups to resolve after a merge?

## cleanup-source-account: rewinds → user → fraud events → raw-SQL partner delete
**Path/Symbol:** `apps/web/app/(ee)/api/workflows/merge-partner-accounts/route.ts` step :120-153, helpers `deleteSourceUser` (:846-885), `cleanupFraudEvents` (:887-954), `deleteSourcePartner` (:956-984).
**Signature:** `cleanupFraudEvents({ sourcePartnerId }): Promise<{ outputLog }>`; `deleteSourcePartner({ sourcePartnerId, sourceEmail, sourceImage })`.
**Data Shape:** fraud events group under `fraudEventGroup` with `type: FraudRuleType.partnerDuplicateAccount`; group resolution carries a frozen `resolutionReason` string.

### Decisive source
```ts
const fraudEventGroupsToResolve = fraudEventsToDelete.filter(
  // this is the count pre-deleting the fraud event, so if there are 2 fraud events
  // that means post-deletion will leave 1 fraud event in the group (no additional duplicates), hence can be resolved
  (e) => e.fraudEventGroup._count.fraudEvents === 2,
);
await resolveFraudGroups({
  where: { OR: [
    { partnerId: sourcePartnerId },
    ...(fraudEventGroupsToResolve.length > 0 ? [{ id: { in: ... } }] : []),
  ], type: FraudRuleType.partnerDuplicateAccount },
  resolutionReason: "Automatically resolved because partners with duplicate payout methods were merged...",
});
// ...
// Delete the source partner account (must be last)
await conn.execute(`DELETE FROM Partner WHERE id = ?`, [sourcePartnerId]);
```
(:921-949 count-2 rule; :964-965 raw delete)

**Flow:** delete source rewinds FIRST (plan carried `hasRewinds` so the step knows whether any existed) · delete source user ONLY when workspace count is zero (image blob GC'd best-effort; delete errors are logged-and-continue) · fraud plane: fetch THIS partner's duplicate-account events WITH group `_count.fraudEvents`, bulk-delete them, then resolve (a) all duplicate-account groups naming the source partner and (b) exactly those groups where the PRE-deletion count was 2 — i.e. this merge removed the only remaining duplicate · LAST: raw SQL `DELETE FROM Partner` via the Planetscale `conn` (bypassing Prisma's relation checks now that every child table is empty), then image cleanup.
**Invariant:** (1) teardown order is load-bearing: children → user → fraud metadata → partner row; Prisma would refuse (or cascade unexpectedly) if the partner died first; (2) the count===2 filter uses the PRE-delete group count — filtering on post-delete state (1) or ≥2 would both mis-resolve groups that still hold OTHER duplicates; (3) the raw-SQL delete is deliberate: it's the one statement guaranteed not to drag relation logic into a step that has already hand-cleared every table; (4) per-item failures inside teardown log-and-continue — a stuck image delete must not orphan an already-empty account.
**Probe:** deterministic probe: `grep -c 'DELETE FROM Partner WHERE id' apps/web/app/\(ee\)/api/workflows/merge-partner-accounts/route.ts` = 1; `grep -n '_count.fraudEvents === 2' ...route.ts` = :924.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "cleanupFraudEvents", limit: 5 });
// → ...route.cleanupFraudEvents @ route.ts 887-954
```

## Verdict
Adopt children-first teardown ending in a raw bypassed-ORM delete, plus the pre-delete-count===2 auto-resolution rule for duplicate-detection groups. Adapt your ORM escape hatch. Omit dub's rewind feature specifics.
