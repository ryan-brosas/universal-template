<!-- capsule-v2 -->
# Inactivity retention ladder — how do polls get deleted without ever losing active ones?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** What exact predicate decides "inactive enough to delete", and why does the vote-update path explicitly bump `updatedAt`?

## deleteInactivePolls + removeDeletedPolls + the updatedAt bump
**Path/Symbol:** `apps/web/src/features/poll/mutations.ts:deleteInactivePolls` (lines 239–281) + `removeDeletedPolls` (lines 313–352); counterpart bump `apps/web/src/trpc/routers/polls/participants.ts:update` (lines 494–501).
**Signature:** `deleteInactivePolls(): Promise<number>`; `removeDeletedPolls(): Promise<number>`; participant update sets `{ updatedAt: new Date() }`.
**Data Shape:** single `updateMany` with relational filters: options.none.startTime.gt cutoff, updatedAt.lt, participants.none.updatedAt.gte, comments.none.createdAt.gte, OR[spaceId null | space.tier != pro].

### Decisive source
```ts
const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
const { count: markedDeleted } = await prisma.poll.updateMany({
  where: {
    deleted: false,
    // All poll dates passed at least 30 days ago
    options: { none: { startTime: { gt: thirtyDaysAgo } } },
    // We don't delete polls that belong to a space with an active subscription
    OR: [{ spaceId: null }, { space: { tier: { not: "pro" } } }],
    // Poll is inactive: not edited, and no participant activity (new or
    // updated responses) or new comments in the last 30 days
    updatedAt: { lt: thirtyDaysAgo },
    participants: { none: { updatedAt: { gte: thirtyDaysAgo } } },
    comments: { none: { createdAt: { gte: thirtyDaysAgo } } },
  },
  data: { deleted: true, deletedAt: new Date() },
});
```
```ts
// Bump `updatedAt` so it reflects this vote change; the poll cleanup
// job uses it to detect recent activity. An empty `data: {}` update is
// a no-op for `@updatedAt`, so set it explicitly.
return tx.participant.update({ where: { id: participantId }, data: { updatedAt: new Date() }, ... });
```

**Flow:** cron → mark-deleted (soft, with deletedAt) → 7 days later `removeDeletedPolls` hard-deletes in batches of 100 (loop re-querying until empty). Retention guarantee: polls survive ≥30 days past their final date, and ANY activity (edit, vote add/update, comment) extends life another 30.
**Invariant:** three independent activity signals (poll.updatedAt, max participant.updatedAt, max comment.createdAt); Prisma's `@updatedAt` auto-touch does NOT fire on empty data — the explicit bump in the vote transaction is load-bearing for the retention contract; pro-tier spaces are exempt entirely.
**Probe:** `apps/web/src/features/poll/mutations.test.ts` deleteInactivePolls suite (:81–151) — evaluates the captured where-clause against synthetic polls ("keeps a poll whose dates passed less than 30 days ago…", "keeps a poll with recent participant or comment activity…", "keeps polls on pro spaces").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "deleteInactivePolls removeDeletedPolls", limit: 5 });
```

## Verdict
Adopt the predicate shape and the explicit-updatedAt-bump rule verbatim; adapt the ORM calls to your query builder; omit the batch loop if your DB cascades hard deletes. Direct tests pin the retention rule semantically (they replay the where clause), a pattern worth copying.
